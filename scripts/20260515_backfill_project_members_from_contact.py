# -*- coding: utf-8 -*-
"""
为"完全没有 project_members"的历史项目从 ProjectHeader.contact 补一条人员记录

策略：
    - 每个项目补 1 条 ProjectMember，is_leader=True
    - 解析 contact 前缀的称谓（MR/MS/MISS/MASTER/MRS/DR），分离 title 与 member_name
    - 没识别到称谓的，整个 contact 当作 member_name，title 留空
    - remarks 标注 [历史回填]，方便事后审计 / 回滚

用法:
    python scripts/20260515_backfill_project_members_from_contact.py
    python scripts/20260515_backfill_project_members_from_contact.py --execute
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_config():
    try:
        from App_new.config import Config
        uri = Config.SQLALCHEMY_DATABASE_URI
        pattern = r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^\?]+)'
        match = re.match(pattern, uri)
        if match:
            return {
                'host': match.group(3),
                'port': int(match.group(4)),
                'user': match.group(1),
                'password': match.group(2),
                'database': match.group(5),
                'charset': 'utf8mb4'
            }
    except Exception as e:
        print(f"警告: 无法从 Flask 配置读取数据库信息: {e}")
    return {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': os.environ.get('DB_PASSWORD', ''), 'database': 'travelindustry',
        'charset': 'utf8mb4'
    }


def get_connection():
    db_config = get_db_config()
    try:
        import pymysql
        return pymysql.connect(**db_config)
    except ImportError:
        import mysql.connector
        config = db_config.copy()
        config['db'] = config.pop('database')
        return mysql.connector.connect(**config)


# 支持的称谓前缀（按长度降序，先匹配长的避免误判，如 MISS 不被 MS 截胡）
KNOWN_TITLES = ['MASTER', 'MISS', 'MRS', 'MR.', 'MS.', 'DR.', 'MR', 'MS', 'DR']


def parse_title(contact):
    """从 contact 字符串里抽出称谓和姓名"""
    if not contact:
        return None, None
    s = contact.strip()
    upper = s.upper()
    for t in KNOWN_TITLES:
        # 必须是独立的词：后面跟空格才算
        if upper.startswith(t + ' '):
            title = t.rstrip('.')
            name = s[len(t):].strip()
            return title, name
    return None, s


SQL_ORPHAN_HEADERS = """
SELECT h.id, h.hid, h.contact, h.`desc`
FROM project_headers h
LEFT JOIN project_members m ON m.header_id = h.id
WHERE m.id IS NULL
  AND h.contact IS NOT NULL
  AND TRIM(h.contact) <> ''
ORDER BY h.id
"""

INSERT_SQL = """
INSERT INTO project_members
    (header_id, title, member_name, is_leader, remarks, created_at, updated_at)
VALUES (%s, %s, %s, 1, '[历史回填] 从项目联系人补建', NOW(), NOW())
"""


def fetch_all(cursor, sql):
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def build_plan(cursor):
    headers = fetch_all(cursor, SQL_ORPHAN_HEADERS)
    plan = []
    for h in headers:
        title, name = parse_title(h['contact'])
        if not name:
            continue
        plan.append({
            'header_id': h['id'],
            'hid': h['hid'],
            'contact_raw': h['contact'],
            'desc': h['desc'],
            'title': title,
            'member_name': name,
        })
    return plan


def print_plan(plan):
    if not plan:
        print("没有需要补建的项目。")
        return
    print(f"将补建 {len(plan)} 条 project_member 记录")
    print("-" * 100)
    print(f"{'HID':<10}{'项目描述':<28}{'原 contact':<30}{'title':<10}{'解析姓名':<20}")
    print("-" * 100)
    for p in plan:
        desc = (p['desc'] or '')[:26]
        contact = (p['contact_raw'] or '')[:28]
        title = p['title'] or '-'
        name = (p['member_name'] or '')[:18]
        print(f"{p['hid']:<10}{desc:<28}{contact:<30}{title:<10}{name:<20}")
    print("-" * 100)


def run(execute=False):
    print("=" * 80)
    print("从项目联系人补建 project_members")
    print(f"模式: {'执行模式（写库）' if execute else '预览模式（不写库）'}")
    print("=" * 80)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        plan = build_plan(cursor)
        print_plan(plan)
        print()

        if not plan:
            return 0

        if not execute:
            print("预览完成。如需写库请加 --execute 重跑。")
            return len(plan)

        for p in plan:
            cursor.execute(INSERT_SQL, (p['header_id'], p['title'], p['member_name']))

        conn.commit()
        print(f"已成功补建 {len(plan)} 条 project_member 记录。")
        return len(plan)

    except Exception as e:
        conn.rollback()
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return -1
    finally:
        cursor.close()
        conn.close()


def main():
    execute = '--execute' in sys.argv or '-e' in sys.argv
    result = run(execute=execute)
    return 0 if result >= 0 else 1


if __name__ == '__main__':
    sys.exit(main())
