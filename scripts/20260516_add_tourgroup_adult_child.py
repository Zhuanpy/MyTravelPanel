# -*- coding: utf-8 -*-
"""
tour_group 增加 adult_count / child_count 两列（大人 / 小孩人数）

设计：
    - 两列 NULL 允许：历史行不回填，留空由用户在编辑页逐个补
    - pax 保留为"总人数"，编辑保存时后端自动 = adult + child
      （历史行未编辑前 pax 维持原值，作为总数兜底）

用法:
    python scripts/20260516_add_tourgroup_adult_child.py            # 预览
    python scripts/20260516_add_tourgroup_adult_child.py --execute  # 执行
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_config():
    try:
        from App_new.config import Config
        uri = Config.SQLALCHEMY_DATABASE_URI
        m = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^\?]+)', uri)
        if m:
            return {'host': m.group(3), 'port': int(m.group(4)), 'user': m.group(1),
                    'password': m.group(2), 'database': m.group(5), 'charset': 'utf8mb4'}
    except Exception as e:
        print(f"警告: 无法从 Flask 配置读取: {e}")
    return {'host': 'localhost', 'port': 3306, 'user': 'root',
            'password': os.environ.get('DB_PASSWORD', ''), 'database': 'travelindustry', 'charset': 'utf8mb4'}


def get_connection():
    import pymysql
    return pymysql.connect(**get_db_config())


def column_exists(cursor, table, column):
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
    """, (table, column))
    return cursor.fetchone()[0] > 0


def run(execute=False):
    print("=" * 70)
    print("tour_group 增加 adult_count / child_count")
    print(f"模式: {'执行' if execute else '预览'}")
    print("=" * 70)

    conn = get_connection()
    cur = conn.cursor()
    try:
        plan = []
        if not column_exists(cur, 'tour_group', 'adult_count'):
            plan.append(("adult_count",
                         "ALTER TABLE tour_group ADD COLUMN adult_count INT NULL COMMENT '大人人数' AFTER pax"))
        if not column_exists(cur, 'tour_group', 'child_count'):
            plan.append(("child_count",
                         "ALTER TABLE tour_group ADD COLUMN child_count INT NULL COMMENT '小孩人数' AFTER adult_count"))

        if not plan:
            print("两列均已存在，无需变更。")
            return 0

        for name, sql in plan:
            print(f"  + 新增列 {name}")
            print(f"    {sql}")

        if not execute:
            print("\n预览完成。加 --execute 执行。")
            return len(plan)

        for _name, sql in plan:
            cur.execute(sql)
        conn.commit()
        print(f"\n已执行 {len(plan)} 条 ALTER，完成。历史行 adult_count/child_count 为 NULL，pax 不变。")
        return len(plan)
    except Exception as e:
        conn.rollback()
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return -1
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    execute = '--execute' in sys.argv or '-e' in sys.argv
    sys.exit(0 if run(execute=execute) >= 0 else 1)
