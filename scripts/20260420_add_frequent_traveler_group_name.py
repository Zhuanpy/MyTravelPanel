# -*- coding: utf-8 -*-
"""
给 frequent_travelers 表加 group_name 列，并把已有旅客的 group_name 回填为
其关联 CustomerCompany.group_name（若有）。

使用：
    python scripts/20260420_add_frequent_traveler_group_name.py           # dry-run
    python scripts/20260420_add_frequent_traveler_group_name.py --apply   # 正式执行
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from App_new import create_app
from App_new.exts import db


def column_exists():
    row = db.session.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'frequent_travelers' "
        "AND COLUMN_NAME = 'group_name'"
    )).scalar()
    return bool(row and int(row) > 0)


def ensure_column(apply_changes):
    if column_exists():
        print('[schema] frequent_travelers.group_name 已存在，跳过。')
        return True
    print('[schema] frequent_travelers.group_name 不存在，准备新增 VARCHAR(100) NULL。')
    if not apply_changes:
        print('[schema] (dry-run) 未实际执行 ALTER TABLE。')
        return False
    db.session.execute(text(
        "ALTER TABLE frequent_travelers ADD COLUMN group_name VARCHAR(100) NULL "
        "COMMENT '集团/关联标签' AFTER company_id"
    ))
    db.session.commit()
    print('[schema] 已新增。')
    return True


def backfill(apply_changes, column_ready):
    """把 group_name 为空且关联公司有 group_name 的旅客，回填为公司的 group_name"""
    if not column_ready:
        # 列还没有，走纯只读预览 SQL：只看需要回填多少条
        count = db.session.execute(text(
            "SELECT COUNT(*) FROM frequent_travelers t "
            "JOIN customer_companies c ON t.company_id = c.id "
            "WHERE c.group_name IS NOT NULL AND c.group_name != ''"
        )).scalar()
        print(f'[data] (dry-run) 有 {count} 条旅客可以从关联公司回填 group_name。')
        return

    # 需要回填：group_name 为空且公司有 group_name
    rows = db.session.execute(text(
        "SELECT t.id, c.group_name FROM frequent_travelers t "
        "JOIN customer_companies c ON t.company_id = c.id "
        "WHERE (t.group_name IS NULL OR t.group_name = '') "
        "AND c.group_name IS NOT NULL AND c.group_name != ''"
    )).fetchall()

    print(f'[data] 待回填 group_name 的旅客数：{len(rows)}')
    if not apply_changes:
        for r in rows[:5]:
            print(f'  <- traveler id={r[0]} group_name <- {r[1]!r}')
        if len(rows) > 5:
            print(f'  ...（共 {len(rows)} 条）')
        print('[data] (dry-run) 未实际写入。')
        return

    for tid, group in rows:
        db.session.execute(
            text("UPDATE frequent_travelers SET group_name = :g WHERE id = :i"),
            {'g': group, 'i': tid}
        )
    db.session.commit()
    print(f'[data] 已回填 {len(rows)} 条。')


def main():
    parser = argparse.ArgumentParser(description='给 frequent_travelers 加 group_name 列并回填')
    parser.add_argument('--apply', '--execute', dest='apply', action='store_true',
                        help='实际执行（默认 dry-run）；--execute 为老部署脚本兼容别名')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print('=== frequent_travelers.group_name 迁移 ===')
        print(f'模式：{"APPLY" if args.apply else "DRY-RUN"}')
        print('-' * 50)
        try:
            column_ready = ensure_column(args.apply)
            backfill(args.apply, column_ready)
        except Exception as e:
            db.session.rollback()
            print(f'迁移失败：{e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
