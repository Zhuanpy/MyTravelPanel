# -*- coding: utf-8 -*-
"""
回滚 20260419_migrate_visa_ref_to_visaproject.py 造成的数据变更

背景：
- 上一个迁移脚本错误地把 `VisaProject.visa_type`（具体签证产品名，例如"韩国单次签证"）
  用 `ProjectRef.extra_info['visa_type']`（粗粒度 enum，例如 "TOURIST"）覆盖掉了。
- 同时也把 `ProjectRef.extra_info` 里的 country / visa_type / visa_name / pax_names_display 剔除了。

本脚本从 MySQL binlog 里精确读出 before/after 值，逐行回滚：
- visa_projects 的 visa_type (46 条真正被改的)
- visa_projects 的 applicant_name / estimated_date (如果被改过)
- project_refs 的 extra_info (94 条)

不回滚：
- visa_projects.country 新增的值（保留 - 本来是 NULL，加上了总比没有强）
- visa_projects 的 10 条新 INSERT（保留 - 本来就没有记录）
- visa_projects.country 列本身（保留 - schema 改动，不是数据问题）

运行方式：
    python scripts/20260419_rollback_visa_migration.py                     # dry-run
    python scripts/20260419_rollback_visa_migration.py --apply             # 正式回滚
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from App_new import create_app
from App_new.exts import db


# binlog 解析后的临时文件（由 mysqlbinlog 生成，脚本启动前需已就绪）
MIGRATION_EVENTS_PATH = r'C:\Users\User\AppData\Local\Temp\migration_events.txt'


# ======================== binlog 解析 ========================

def _parse_cols(block: str) -> dict:
    """把 ###   @N=value 的多行块解析成 {N: value_literal} 字典"""
    result = {}
    for line in block.splitlines():
        m = re.match(r'###\s+@(\d+)=(.*)', line)
        if m:
            result[int(m.group(1))] = m.group(2)
    return result


def _literal_to_value(literal: str):
    """把 binlog 里 '123' / 'xxx' / NULL 这类字面量转成 Python 值

    binlog verbose 输出中，字符串会有两层引号（外层 SQL 单引号），数字无引号，NULL 就是 NULL。
    字符串里的 \\x0d\\x0a 代表 \\r\\n，但我们这里只做透明回写，保留为原字节序列即可。
    """
    if literal == 'NULL':
        return None
    if literal.startswith("'") and literal.endswith("'"):
        # 去掉外层引号，解码 \xHH 十六进制转义（由 mysqlbinlog 对不可打印字节生成）
        inner = literal[1:-1]
        # 转义序列 \x0d -> \r, \x0a -> \n 等；其它 \' \\ 也要处理
        out = inner.replace("\\'", "'").replace("\\\\", "\\")
        # 把 \xHH 还原为对应字节
        out = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), out)
        return out
    # 数字
    try:
        return int(literal)
    except ValueError:
        try:
            return float(literal)
        except ValueError:
            return literal


def load_binlog_events(path: str):
    """读入 binlog 片段，拆成 visa_projects / project_refs 的 UPDATE 事件列表

    返回 (visa_updates, ref_updates) 两个 list，每个元素是 (where_dict, set_dict)
    """
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    pattern_vp = re.compile(
        r'### UPDATE `travelindustry`\.`visa_projects`\n'
        r'### WHERE\n((?:###   @\d+=.+\n)+)'
        r'### SET\n((?:###   @\d+=.+\n)+)',
    )
    pattern_ref = re.compile(
        r'### UPDATE `travelindustry`\.`project_refs`\n'
        r'### WHERE\n((?:###   @\d+=.+\n)+)'
        r'### SET\n((?:###   @\d+=.+\n)+)',
    )

    visa_updates = []
    for m in pattern_vp.finditer(content):
        w = _parse_cols(m.group(1))
        s = _parse_cols(m.group(2))
        visa_updates.append((w, s))

    ref_updates = []
    for m in pattern_ref.finditer(content):
        w = _parse_cols(m.group(1))
        s = _parse_cols(m.group(2))
        ref_updates.append((w, s))

    return visa_updates, ref_updates


# ======================== 回滚 visa_projects ========================

# 列位置（通过 DESCRIBE visa_projects 查得）
VP_ID = 1
VP_VISA_TYPE = 3
VP_APPLICANT_NAME = 4
VP_ESTIMATED_DATE = 8


def rollback_visa_projects(visa_updates, apply_changes):
    """对 visa_type / applicant_name / estimated_date 被改过的 VisaProject 恢复原值。

    回滚的字段：
    - visa_type (@3) : 改过就还原
    - applicant_name (@4) : 改过就还原
    - estimated_date (@8) : 改过就还原
    不回滚 country (@14) : 本来是 NULL，加上了总比空好
    """
    reverts = []
    for where, set_ in visa_updates:
        vid = _literal_to_value(where.get(VP_ID))
        changes = {}
        for col, name in [
            (VP_VISA_TYPE, 'visa_type'),
            (VP_APPLICANT_NAME, 'applicant_name'),
            (VP_ESTIMATED_DATE, 'estimated_date'),
        ]:
            old_raw = where.get(col)
            new_raw = set_.get(col)
            if old_raw != new_raw:
                changes[name] = _literal_to_value(old_raw)
        if changes:
            reverts.append((vid, changes))

    print(f'[visa_projects] 需回滚 {len(reverts)} 条（visa_type/applicant_name/estimated_date 有变更）')
    for vid, changes in reverts[:10]:
        print(f'  <- id={vid}  {changes}')
    if len(reverts) > 10:
        print(f'  ...（共 {len(reverts)} 条，此处仅打印前 10）')

    if not apply_changes:
        print('[visa_projects] dry-run，未实际回滚。')
        return

    for vid, changes in reverts:
        assignments = ', '.join(f'{col} = :{col}' for col in changes)
        params = dict(changes)
        params['id'] = vid
        db.session.execute(
            text(f'UPDATE visa_projects SET {assignments} WHERE id = :id'),
            params,
        )
    db.session.commit()
    print(f'[visa_projects] 已回滚 {len(reverts)} 条。')


# ======================== 回滚 project_refs.extra_info ========================

# 确认 project_refs 的列顺序
REF_ID = 1
# extra_info 的位置需要动态查，因为表结构可能跨版本变。不过对这次迁移影响的只有 extra_info 列。
# 在 load 时通过 DESCRIBE 查出位置即可。

def find_ref_extra_info_col_index():
    """查出 project_refs.extra_info 是第几列"""
    rows = db.session.execute(text('DESCRIBE project_refs')).fetchall()
    for i, row in enumerate(rows, start=1):
        if row[0] == 'extra_info':
            return i
    raise RuntimeError('project_refs 没有 extra_info 列')


def rollback_project_refs(ref_updates, apply_changes):
    """对每条 project_refs UPDATE 恢复 extra_info 到原值"""
    extra_col_idx = find_ref_extra_info_col_index()
    print(f'[project_refs] extra_info 在第 {extra_col_idx} 列')

    reverts = []
    for where, set_ in ref_updates:
        rid = _literal_to_value(where.get(REF_ID))
        old_raw = where.get(extra_col_idx)
        new_raw = set_.get(extra_col_idx)
        if old_raw != new_raw:
            reverts.append((rid, _literal_to_value(old_raw)))

    print(f'[project_refs] 需回滚 {len(reverts)} 条 extra_info')
    for rid, old_extra in reverts[:3]:
        preview = (old_extra or '')[:80]
        print(f'  <- REF id={rid}  extra_info 前 80 字符: {preview!r}')
    if len(reverts) > 3:
        print(f'  ...（共 {len(reverts)} 条，仅打印前 3）')

    if not apply_changes:
        print('[project_refs] dry-run，未实际回滚。')
        return

    for rid, old_extra in reverts:
        db.session.execute(
            text('UPDATE project_refs SET extra_info = :extra WHERE id = :id'),
            {'extra': old_extra, 'id': rid},
        )
    db.session.commit()
    print(f'[project_refs] 已回滚 {len(reverts)} 条。')


# ======================== 主流程 ========================

def main():
    parser = argparse.ArgumentParser(description='回滚 20260419 签证迁移造成的数据变更')
    parser.add_argument('--apply', action='store_true', help='实际执行（默认 dry-run）')
    parser.add_argument('--events', default=MIGRATION_EVENTS_PATH,
                        help='mysqlbinlog --verbose 产生的迁移事件文件路径')
    args = parser.parse_args()

    events_path = args.events
    if not Path(events_path).exists():
        print(f'[error] 找不到 binlog 事件文件：{events_path}')
        print('请先用 mysqlbinlog 解析 binlog 并导出到该路径。')
        sys.exit(1)

    print('=== 签证迁移回滚 ===')
    print(f'模式：{"APPLY（正式写入）" if args.apply else "DRY-RUN（只打印）"}')
    print(f'binlog 事件文件：{events_path}')
    print('-' * 60)

    visa_updates, ref_updates = load_binlog_events(events_path)
    print(f'解析出 visa_projects UPDATE 事件 {len(visa_updates)} 条；'
          f'project_refs UPDATE 事件 {len(ref_updates)} 条')

    app = create_app()
    with app.app_context():
        try:
            rollback_visa_projects(visa_updates, args.apply)
            rollback_project_refs(ref_updates, args.apply)
        except Exception as e:
            db.session.rollback()
            print(f'\n回滚失败：{e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print('\n=== 完成 ===')


if __name__ == '__main__':
    main()
