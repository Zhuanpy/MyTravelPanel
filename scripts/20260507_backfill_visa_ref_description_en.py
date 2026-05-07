# -*- coding: utf-8 -*-
"""
回填所有签证类型 ProjectRef 的 description / detailed_description 为英文版本

逻辑：
- 找出所有 ref_type_id 对应 BusinessType.name == '签证' 的 ProjectRef
- 读取 ref.extra_info.country (EN code) 和 ref.extra_info.visa_type (CN)
- 通过 visa_types 表查 visa_type_en；没填英文就回退中文
- 重新拼 description = "<COUNTRY> <visa_type_en or visa_type_cn> VISA [| DDMON]"
- detailed_description 同理（多换行 + Departure: + Pax: 信息保留）

运行方式：
  python scripts/20260507_backfill_visa_ref_description_en.py          # 预览（dry-run）
  python scripts/20260507_backfill_visa_ref_description_en.py --apply  # 实际写入
"""

import sys
import os
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.ref import ProjectRef
from App_new.shared.models.business_types import BusinessType
from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries
from App_new.business.projects.routes.project_ref import _normalize_country_for_display

MONTH_ABBR = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
              'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']


def format_date(date_str):
    """复刻前端 formatDate：YYYY-MM-DD -> DDMON"""
    if not date_str:
        return ''
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        return f"{d.day:02d}{MONTH_ABBR[d.month - 1]}"
    except (ValueError, TypeError):
        return ''


def build_descriptions(extra, visa_type_en_map, countries):
    """根据 extra_info 拼新的 description / detailed_description"""
    # 国家：把历史中文/别名归一化成 EN upper（与下拉 value 一致）
    country = _normalize_country_for_display(extra.get('country'), countries)
    visa_type_cn = (extra.get('visa_type') or '').strip()
    departure_date = extra.get('departure_date', '')

    # 三档策略：
    # 1) visa_type 在 visa_types 表里且填了英文 → 直接用英文（Country + Visa 已含）
    # 2) visa_type 在表里但没填英文 → "<COUNTRY> <visa_type_cn> VISA"（与历史一致）
    # 3) visa_type 是历史自由文本（如 'TOURIST'）→ "<COUNTRY> <visa_type> VISA"
    visa_name = ''
    if visa_type_cn:
        en = visa_type_en_map.get(visa_type_cn)
        if en and en != visa_type_cn:
            visa_name = en
        elif country:
            visa_name = f"{country} {visa_type_cn} VISA"
        else:
            visa_name = f"{visa_type_cn} VISA"
    elif country:
        visa_name = f"{country} VISA"

    description = visa_name or 'VISA APPLICATION'
    if departure_date:
        formatted = format_date(departure_date)
        if formatted:
            description += ' | ' + formatted

    detailed = visa_name or 'VISA APPLICATION'
    if departure_date:
        formatted = format_date(departure_date)
        if formatted:
            detailed += '\nDeparture: ' + formatted

    # Pax 统计：ProjectMember 没有 member_type 字段（前端模板的判断恒为 false），
    # 与现有 JS 行为对齐——所有 pax 都按 Adult 计。
    pax_ids = extra.get('pax_names') or []
    if pax_ids:
        n = len(pax_ids)
        detailed += f"\n{n} Adult" + ('s' if n > 1 else '')

    return description.strip(), detailed.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='实际写入数据库（默认仅 dry-run 预览）')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # 1) visa_type 中英映射
        visa_type_en_map = {
            vt.visa_type: (vt.visa_type_en or vt.visa_type)
            for vt in VisaTypes.query.all()
        }
        print(f"载入 {len(visa_type_en_map)} 条 visa_type 映射")

        # 2) 国家列表（用于 country 归一化）
        countries = VisaCountries.query.all()

        # 3) 找签证类型的 BusinessType
        visa_bt = BusinessType.query.filter_by(name='签证').first()
        if not visa_bt:
            print("找不到 BusinessType '签证'，终止")
            return

        # 4) 拉所有签证 ref
        refs = ProjectRef.query.filter_by(ref_type_id=visa_bt.id).all()
        print(f"找到 {len(refs)} 条签证 ref")

        updated = 0
        skipped = 0
        for ref in refs:
            try:
                extra = json.loads(ref.extra_info) if ref.extra_info else {}
            except (json.JSONDecodeError, TypeError):
                extra = {}

            new_desc, new_detailed = build_descriptions(
                extra, visa_type_en_map, countries
            )

            old_desc = ref.description or ''
            old_detailed = ref.detailed_description or ''

            if old_desc == new_desc and old_detailed == new_detailed:
                skipped += 1
                continue

            print(f"\nref #{ref.id} (header={ref.header_id})")
            print(f"  desc:     {old_desc!r}")
            print(f"  →         {new_desc!r}")
            if old_detailed != new_detailed:
                print(f"  detailed: {old_detailed!r}")
                print(f"  →         {new_detailed!r}")

            if args.apply:
                ref.description = new_desc
                ref.detailed_description = new_detailed
                updated += 1

        if args.apply:
            db.session.commit()
            print(f"\n[APPLIED] 更新 {updated} 条，跳过 {skipped} 条")
        else:
            preview_count = len(refs) - skipped
            print(f"\n[DRY-RUN] 预计更新 {preview_count} 条，"
                  f"跳过 {skipped} 条（已是英文/无变化）")
            print(f"加 --apply 实际写入")


if __name__ == '__main__':
    main()
