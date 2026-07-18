# -*- coding: utf-8 -*-
"""
为"有收款但完全没发票"的历史项目批量补开发票

策略：
    每个项目按其"已确认收款总额"补开一张发票，金额 = 收款总额，
    invoice_date = 该项目最晚一笔收款日期，并立即把所有收款挂上去
    （paid_amount = amount，payment_status = paid）。

    - ref_ids 关联项目下所有 REF（与正常流程一致）
    - customer_name / customer_company 按 create_invoice 的回退逻辑
    - invoice_type = 'full'
    - remarks 标注"历史回填，源于 receipts"，便于审计
    - 不写 invoice_items（避免与 ref 价格不一致造成误解）
    - 不生成日记账（人工另行处理，避免污染账面）

    多币种容错：同一项目里若 receipts 含多种币种，按币种分别开发票。

用法:
    python scripts/20260515_backfill_invoices_from_receipts.py            # 预览
    python scripts/20260515_backfill_invoices_from_receipts.py --execute  # 执行
"""

import sys
import os
import re
import json
from collections import defaultdict

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
        try:
            import mysql.connector
            config = db_config.copy()
            config['db'] = config.pop('database')
            return mysql.connector.connect(**config)
        except ImportError:
            print("错误: 需要安装 pymysql 或 mysql-connector-python")
            sys.exit(1)


# ---------------------------------------------------------------------------
# 候选项目：有已确认收款，但 project_invoices 完全为空
# ---------------------------------------------------------------------------
SQL_ORPHAN_HEADERS = """
SELECT
    h.id, h.hid, h.desc, h.contact, h.staff_name,
    c.company_name
FROM project_headers h
JOIN project_receipts r
    ON r.header_id = h.id AND r.status = 'confirmed'
LEFT JOIN project_invoices i
    ON i.header_id = h.id
LEFT JOIN customer_companies c
    ON c.id = h.company_id
WHERE i.id IS NULL
GROUP BY h.id, h.hid, h.desc, h.contact, h.staff_name, c.company_name
ORDER BY h.id
"""

# 项目下 receipts
SQL_RECEIPTS_OF_HEADER = """
SELECT id, receipt_number, ref_id, amount, currency, payment_date, status,
       (SELECT COALESCE(SUM(allocated_amount),0)
        FROM receipt_invoice_allocations
        WHERE receipt_id = pr.id) AS already_allocated
FROM project_receipts pr
WHERE header_id = %s AND status = 'confirmed'
ORDER BY payment_date, id
"""

# 项目下 refs
SQL_REFS_OF_HEADER = """
SELECT id, ref_number FROM project_refs
WHERE header_id = %s ORDER BY id
"""

# leader 项目成员（供 customer_name 回退）
SQL_LEADER_MEMBER = """
SELECT title, member_name
FROM project_members
WHERE header_id = %s AND is_leader = 1
LIMIT 1
"""
SQL_ANY_MEMBER = """
SELECT title, member_name
FROM project_members
WHERE header_id = %s
ORDER BY id LIMIT 1
"""

# 当前最大纯数字 invoice_number
SQL_MAX_INVOICE_NUMBER = """
SELECT MAX(CAST(invoice_number AS UNSIGNED)) AS max_num
FROM project_invoices
WHERE invoice_number REGEXP '^[0-9]+$'
"""


def fetch_all(cursor, sql, params=None):
    cursor.execute(sql, params or ())
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def fetch_one(cursor, sql, params=None):
    cursor.execute(sql, params or ())
    row = cursor.fetchone()
    if not row:
        return None
    cols = [c[0] for c in cursor.description]
    return dict(zip(cols, row))


def resolve_customer_name(cursor, header):
    """模仿 create_invoice 路由的客户名回退顺序"""
    leader = fetch_one(cursor, SQL_LEADER_MEMBER, (header['id'],))
    if not leader:
        leader = fetch_one(cursor, SQL_ANY_MEMBER, (header['id'],))
    if leader:
        if leader['title']:
            return f"{leader['title']} {leader['member_name']}"
        return leader['member_name']
    if header.get('contact'):
        return header['contact']
    return None


def build_plan(cursor):
    headers = fetch_all(cursor, SQL_ORPHAN_HEADERS)
    plans = []

    for h in headers:
        receipts = fetch_all(cursor, SQL_RECEIPTS_OF_HEADER, (h['id'],))
        refs = fetch_all(cursor, SQL_REFS_OF_HEADER, (h['id'],))
        ref_ids = [r['id'] for r in refs]

        # 按币种分桶
        buckets = defaultdict(list)
        for rcp in receipts:
            remaining = float(rcp['amount']) - float(rcp['already_allocated'])
            if remaining < 0.01:
                continue
            rcp['remaining'] = remaining
            buckets[rcp['currency']].append(rcp)

        for currency, rcps in buckets.items():
            total = round(sum(r['remaining'] for r in rcps), 2)
            if total < 0.01:
                continue
            latest_date = max(r['payment_date'] for r in rcps)
            customer_name = resolve_customer_name(cursor, h)
            plans.append({
                'header_id': h['id'],
                'hid': h['hid'],
                'project_desc': h['desc'],
                'currency': currency,
                'amount': total,
                'invoice_date': latest_date,
                'customer_name': customer_name,
                'customer_company': h.get('company_name'),
                'ref_ids': ref_ids,
                'receipts': rcps,
            })

    return plans


def print_summary(plans):
    if not plans:
        print("没有需要补开的项目。")
        return
    print(f"将补开 {len(plans)} 张发票")
    print("-" * 115)
    print(f"{'HID':<10}{'项目描述':<32}{'客户':<22}{'币种':<6}{'金额':>12}{'日期':<13}{'receipts':>10}")
    print("-" * 115)
    total_amt = 0
    for p in plans:
        desc = (p['project_desc'] or '')[:30]
        cust = (p['customer_name'] or '')[:20]
        print(f"{p['hid']:<10}{desc:<32}{cust:<22}{p['currency']:<6}"
              f"{p['amount']:>12.2f}{str(p['invoice_date']):<13}{len(p['receipts']):>10}")
        total_amt += p['amount']
    print("-" * 115)
    print(f"合计金额: {total_amt:.2f}（仅同币种相加示意）")


def get_next_invoice_number(cursor):
    row = fetch_one(cursor, SQL_MAX_INVOICE_NUMBER)
    if row and row['max_num']:
        return int(row['max_num']) + 1
    return 10000


def insert_plan(cursor, plan, invoice_number):
    """插入一张发票 + 对应 allocation 行"""
    inv_sql = """
        INSERT INTO project_invoices
            (invoice_number, header_id, invoice_date, amount, currency,
             invoice_type, customer_name, customer_company, status,
             payment_status, paid_amount, ref_ids, remarks,
             created_at, updated_at, created_by)
        VALUES
            (%s, %s, %s, %s, %s,
             'full', %s, %s, 'confirmed',
             'paid', %s, %s,
             '[历史回填] 由项目已确认收款汇总补开，详见 receipts',
             NOW(), NOW(), 'system_backfill')
    """
    cursor.execute(inv_sql, (
        str(invoice_number),
        plan['header_id'],
        plan['invoice_date'],
        plan['amount'],
        plan['currency'],
        plan['customer_name'],
        plan['customer_company'],
        plan['amount'],
        json.dumps(plan['ref_ids']) if plan['ref_ids'] else None,
    ))
    invoice_id = cursor.lastrowid

    alloc_sql = """
        INSERT INTO receipt_invoice_allocations
            (receipt_id, invoice_id, allocated_amount, created_at)
        VALUES (%s, %s, %s, NOW())
    """
    for rcp in plan['receipts']:
        cursor.execute(alloc_sql, (rcp['id'], invoice_id, rcp['remaining']))

    return invoice_id


def run(execute=False):
    print("=" * 80)
    print("为孤儿收款项目补开发票")
    print(f"模式: {'执行模式（写库）' if execute else '预览模式（不写库）'}")
    print("=" * 80)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        plans = build_plan(cursor)
        print_summary(plans)
        print()

        if not plans:
            return 0

        if not execute:
            print("预览完成。如需写库请加 --execute 重跑。")
            return len(plans)

        next_num = get_next_invoice_number(cursor)
        print(f"起始发票号: {next_num}")
        created = 0
        for plan in plans:
            insert_plan(cursor, plan, next_num)
            next_num += 1
            created += 1

        conn.commit()
        print(f"已成功补开 {created} 张发票（含对应 allocation 记录）。")
        return created

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
