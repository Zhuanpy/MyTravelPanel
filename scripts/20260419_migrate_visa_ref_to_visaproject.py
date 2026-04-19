# -*- coding: utf-8 -*-
"""
签证 REF -> VisaProject 数据迁移脚本

背景：
- 以前创建"签证 REF"时不会同时创建 VisaProject，两张表各自存一份签证业务数据。
- ProjectRef.extra_info (JSON) 里的 country / visa_type / visa_name / pax_names_display
  与 VisaProject 的 country / visa_type / applicant_name 重复。

本脚本做三件事：
1. 给 visa_projects 表新增 country 列（若还没有）。
2. 扫描所有 ref_type=visa 的 ProjectRef，若没有对应 VisaProject 则补建一条，
   并把 extra_info 中的 country / visa_type / pax_names_display 写入 VisaProject。
3. 从 ProjectRef.extra_info 中剔除已由 VisaProject 托管的共享键
   (country / visa_type / visa_name / pax_names_display)。

使用：
    python scripts/20260419_migrate_visa_ref_to_visaproject.py           # 干跑（只打印、不改库）
    python scripts/20260419_migrate_visa_ref_to_visaproject.py --apply   # 正式执行
"""

import argparse
import json
import sys
from pathlib import Path

# 保证可以以脚本形式从项目根执行
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.visa.models.Visamodels import VisaProject
from App_new.business.projects.models.project_member import ProjectMember
from App_new.shared.models.business_types import BusinessType


SHARED_KEYS = ('country', 'visa_type', 'visa_name', 'pax_names_display')


def ensure_country_column(apply_changes):
    """确认 visa_projects 表有 country 列，若缺失则 ADD COLUMN。

    返回值：True 表示列已就绪（已有或本轮已添加），False 表示 dry-run 跳过了添加。
    """
    result = db.session.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'visa_projects' "
        "AND COLUMN_NAME = 'country'"
    )).scalar()

    if result and int(result) > 0:
        print('[schema] visa_projects.country 已存在，跳过。')
        return True

    print('[schema] visa_projects.country 不存在，准备新增 VARCHAR(50) NULL 列。')
    if apply_changes:
        db.session.execute(text(
            "ALTER TABLE visa_projects ADD COLUMN country VARCHAR(50) NULL COMMENT '国家（与 REF 共享）'"
        ))
        db.session.commit()
        print('[schema] 已新增。')
        return True
    else:
        print('[schema] (dry-run) 未实际执行 ALTER TABLE。')
        return False


def build_pax_display(pax_name_ids):
    if not pax_name_ids:
        return ''
    try:
        pax_ids = [int(pid) for pid in pax_name_ids if pid]
    except (TypeError, ValueError):
        return ''
    if not pax_ids:
        return ''
    members = ProjectMember.query.filter(ProjectMember.id.in_(pax_ids)).all()
    return ', '.join(
        f"{m.title} {m.member_name}" if m.title else m.member_name for m in members
    )


def parse_departure_date(value):
    if not value:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(value, '%Y-%m-%d').date()
    except Exception:
        return None


def _vp_for_ref_via_sql(ref_id):
    """用原生 SQL 查询 ref_id 对应的 VisaProject，避免 ORM 引用 country 新列失败（dry-run 场景）"""
    row = db.session.execute(text(
        "SELECT id, header_id, visa_type, applicant_name, estimated_date "
        "FROM visa_projects WHERE ref_id = :rid LIMIT 1"
    ), {'rid': ref_id}).mappings().first()
    return dict(row) if row else None


def migrate_refs(apply_changes, column_ready):
    """扫描签证 REF，补建 VisaProject + 剔除 extra_info 共享键。

    column_ready=False（dry-run 且列尚未添加）时，只打印 REF 数量与将要剔除的 extra_info 键，
    不查询 VisaProject，避免 ORM 引用不存在的列。
    """
    visa_bt = BusinessType.query.filter_by(code='visa').first()
    if not visa_bt:
        print('[data] 找不到 code=visa 的 BusinessType，脚本退出。')
        return

    refs = ProjectRef.query.filter_by(ref_type_id=visa_bt.id).all()
    print(f'[data] 共发现 {len(refs)} 条签证 REF。')

    if not column_ready:
        print('[data] (dry-run) country 列尚未添加，仅预览 extra_info 清理动作，'
              '不比对 VisaProject。')

    created_vp = 0
    updated_vp = 0
    trimmed_refs = 0

    for ref in refs:
        extra_info = {}
        if ref.extra_info:
            try:
                extra_info = json.loads(ref.extra_info)
            except json.JSONDecodeError:
                print(f'  - REF {ref.id} ({ref.ref_number}) extra_info 不是合法 JSON，跳过。')
                continue

        country = (extra_info.get('country') or '').strip() or None
        visa_type = (extra_info.get('visa_type') or '').strip() or None
        pax_display = (extra_info.get('pax_names_display') or '').strip()
        if not pax_display:
            pax_display = build_pax_display(extra_info.get('pax_names', []))
        pax_display = pax_display or None
        dep_date = parse_departure_date(extra_info.get('departure_date'))

        if column_ready:
            vp = VisaProject.query.filter_by(ref_id=ref.id).first()
        else:
            row = _vp_for_ref_via_sql(ref.id)
            vp = row  # 仅用于 None/existence 判断
        if vp is None:
            print(f'  + REF {ref.id} ({ref.ref_number}): 新建 VisaProject '
                  f'[country={country} visa_type={visa_type} applicant={pax_display}]')
            if apply_changes:
                folder_name = f'REF-{ref.ref_number}'
                vp = VisaProject(name=folder_name, visa_status='待递交')
                vp.project_folder_name = folder_name
                vp.ref_id = ref.id
                vp.header_id = ref.header_id
                vp.country = country
                vp.visa_type = visa_type
                vp.applicant_name = pax_display
                if dep_date:
                    vp.estimated_date = dep_date
                db.session.add(vp)
            created_vp += 1
        elif column_ready:
            changed_fields = []
            if vp.country != country:
                changed_fields.append(f'country: {vp.country!r} -> {country!r}')
                if apply_changes:
                    vp.country = country
            if vp.visa_type != visa_type:
                changed_fields.append(f'visa_type: {vp.visa_type!r} -> {visa_type!r}')
                if apply_changes:
                    vp.visa_type = visa_type
            if pax_display and vp.applicant_name != pax_display:
                changed_fields.append(f'applicant: {vp.applicant_name!r} -> {pax_display!r}')
                if apply_changes:
                    vp.applicant_name = pax_display
            if vp.header_id != ref.header_id:
                changed_fields.append(f'header_id: {vp.header_id!r} -> {ref.header_id!r}')
                if apply_changes:
                    vp.header_id = ref.header_id
            if dep_date and vp.estimated_date != dep_date:
                changed_fields.append(f'estimated_date: {vp.estimated_date!r} -> {dep_date!r}')
                if apply_changes:
                    vp.estimated_date = dep_date
            if changed_fields:
                print(f'  ~ REF {ref.id} ({ref.ref_number}): 更新 VisaProject {vp.id}'
                      f'  [{"; ".join(changed_fields)}]')
                updated_vp += 1

        # 剔除 extra_info 共享键
        keys_to_drop = [k for k in SHARED_KEYS if k in extra_info]
        if keys_to_drop:
            trimmed_refs += 1
            print(f'  - REF {ref.id} ({ref.ref_number}): 剔除 extra_info 键 {keys_to_drop}')
            if apply_changes:
                new_extra = {k: v for k, v in extra_info.items() if k not in SHARED_KEYS}
                ref.extra_info = json.dumps(new_extra, ensure_ascii=False)

    if apply_changes:
        db.session.commit()

    print(f'\n[summary] 新建 VisaProject: {created_vp}，更新: {updated_vp}，'
          f'剔除 extra_info 共享键的 REF: {trimmed_refs}')


def main():
    parser = argparse.ArgumentParser(description='迁移签证 REF 的共享字段到 VisaProject')
    parser.add_argument('--apply', action='store_true', help='实际执行（默认 dry-run）')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print('=== 签证 REF -> VisaProject 迁移 ===')
        print(f'模式：{"APPLY（正式写入）" if args.apply else "DRY-RUN（只打印）"}')
        print('-' * 60)
        try:
            column_ready = ensure_country_column(args.apply)
            migrate_refs(args.apply, column_ready)
        except Exception as e:
            db.session.rollback()
            print(f'\n迁移失败：{e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
