# -*- coding: utf-8 -*-
"""
给 project_refs 增加 idempotency_key 列（幂等键，防 agent 重试重复建单）

背景:
    /projects/ref/flight/quick-create/<pid> 原先没有幂等保护，agent 重试或
    超时重发会实打实建出重复 REF（各带一份 EO + 发票）。加唯一索引后，
    同一 idempotency_key 只会存在一个 REF，重复请求原样返回首次结果。

步骤:
1. 检查列是否已存在（幂等，可重复执行）
2. 添加 idempotency_key VARCHAR(64) NULL
3. 添加唯一索引（NULL 不参与唯一性约束，人工建单不受影响）

运行方式: python scripts/20260727_add_ref_idempotency_key.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


TABLE = 'project_refs'
COLUMN = 'idempotency_key'
INDEX = 'uq_project_refs_idempotency_key'


def _column_exists():
    row = db.session.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {'t': TABLE, 'c': COLUMN}).scalar()
    return bool(row)


def _index_exists():
    row = db.session.execute(text(
        "SELECT COUNT(*) FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND INDEX_NAME = :i"
    ), {'t': TABLE, 'i': INDEX}).scalar()
    return bool(row)


def migrate():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("project_refs 增加 idempotency_key（幂等键）")
        print("=" * 60)

        # 第1步：加列
        print("\n--- 第1步：检查并添加列 ---")
        if _column_exists():
            print(f"列 {COLUMN} 已存在，跳过")
        else:
            db.session.execute(text(
                f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} VARCHAR(64) NULL "
                f"COMMENT '幂等键(agent重试防重复建单)'"
            ))
            db.session.commit()
            print(f"已添加列 {COLUMN} VARCHAR(64) NULL")

        # 第2步：加唯一索引
        # 说明：MySQL 唯一索引允许多行 NULL，所以人工表单建单（key 为空）不受影响
        print("\n--- 第2步：检查并添加唯一索引 ---")
        if _index_exists():
            print(f"索引 {INDEX} 已存在，跳过")
        else:
            # 保险起见先看历史数据有无重复非空值（正常情况下全是 NULL）
            dup = db.session.execute(text(
                f"SELECT {COLUMN}, COUNT(*) AS c FROM {TABLE} "
                f"WHERE {COLUMN} IS NOT NULL GROUP BY {COLUMN} HAVING c > 1"
            )).fetchall()
            if dup:
                print(f"发现 {len(dup)} 个重复的 {COLUMN} 值，无法建唯一索引：")
                for row in dup:
                    print(f"  {row[0]} 出现 {row[1]} 次")
                print("请先人工处理重复值后重跑本脚本")
                return

            db.session.execute(text(
                f"CREATE UNIQUE INDEX {INDEX} ON {TABLE} ({COLUMN})"
            ))
            db.session.commit()
            print(f"已添加唯一索引 {INDEX}")

        print("\n" + "=" * 60)
        print("迁移完成")
        print("=" * 60)


if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
