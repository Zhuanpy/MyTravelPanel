# -*- coding: utf-8 -*-
"""
回填发票与收据的分配记录（历史数据修复）

背景：
    部分项目先创建了收据（REF 级或项目级），后才生成发票。
    receipt_invoice_allocations 表没有对应行，导致发票列表
    paid_amount = 0，状态显示 Unpaid。

策略：
    1. REF 级 receipt：receipt.ref_id 命中发票 ref_ids 的，按
       min(receipt 剩余, invoice 未付) 写入分配表。
    2. 项目级 receipt（ref_id 为空）：只处理"项目内仅 1 张未付发票
       且币种一致"的清晰场景，避免误绑。
    3. 全量重算 project_invoices.paid_amount 和 payment_status。

使用：
    python scripts/20260515_backfill_invoice_receipt_allocations.py            # 预览
    python scripts/20260515_backfill_invoice_receipt_allocations.py --execute  # 执行
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_config():
    """从 Flask 配置中获取数据库配置"""
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
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '***REMOVED***',
        'database': 'travelindustry',
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
# 1. REF 级孤儿 receipt 候选
# ---------------------------------------------------------------------------
SQL_REF_LEVEL_CANDIDATES = """
SELECT
    r.id              AS receipt_id,
    r.receipt_number,
    r.payment_date,
    r.ref_id,
    r.amount          AS receipt_amount,
    r.currency,
    i.id              AS invoice_id,
    i.invoice_number,
    i.invoice_date,
    i.amount          AS invoice_amount,
    i.paid_amount     AS invoice_paid_now,
    i.payment_status,
    COALESCE((SELECT SUM(allocated_amount) FROM receipt_invoice_allocations
              WHERE receipt_id = r.id), 0) AS receipt_already_allocated,
    COALESCE((SELECT SUM(allocated_amount) FROM receipt_invoice_allocations
              WHERE invoice_id = i.id), 0) AS invoice_already_allocated
FROM project_receipts r
JOIN project_invoices i
    ON  i.header_id = r.header_id
    AND i.currency  = r.currency COLLATE utf8mb4_unicode_ci
    AND i.status    = 'confirmed'
    AND JSON_CONTAINS(i.ref_ids, CAST(r.ref_id AS JSON))
LEFT JOIN receipt_invoice_allocations ria
    ON ria.receipt_id = r.id AND ria.invoice_id = i.id
WHERE r.status  = 'confirmed'
  AND r.ref_id IS NOT NULL
  AND ria.id   IS NULL
ORDER BY r.header_id, i.invoice_date, r.payment_date
"""


# ---------------------------------------------------------------------------
# 2. 项目级 receipt 候选（只处理项目内只有一张未付发票的情况）
# ---------------------------------------------------------------------------
SQL_PROJECT_LEVEL_CANDIDATES = """
SELECT
    r.id              AS receipt_id,
    r.receipt_number,
    r.amount          AS receipt_amount,
    r.currency,
    r.header_id,
    i.id              AS invoice_id,
    i.invoice_number,
    i.amount          AS invoice_amount,
    i.paid_amount     AS invoice_paid_now,
    COALESCE((SELECT SUM(allocated_amount) FROM receipt_invoice_allocations
              WHERE receipt_id = r.id), 0) AS receipt_already_allocated,
    COALESCE((SELECT SUM(allocated_amount) FROM receipt_invoice_allocations
              WHERE invoice_id = i.id), 0) AS invoice_already_allocated
FROM project_receipts r
JOIN project_invoices i
    ON  i.header_id = r.header_id
    AND i.currency  = r.currency COLLATE utf8mb4_unicode_ci
    AND i.status    = 'confirmed'
    AND i.payment_status <> 'paid'
LEFT JOIN receipt_invoice_allocations ria
    ON ria.receipt_id = r.id AND ria.invoice_id = i.id
WHERE r.status   = 'confirmed'
  AND r.ref_id   IS NULL
  AND ria.id     IS NULL
  AND (
    SELECT COUNT(*) FROM project_invoices i2
    WHERE i2.header_id = r.header_id
      AND i2.status = 'confirmed'
      AND i2.payment_status <> 'paid'
      AND i2.currency = r.currency COLLATE utf8mb4_unicode_ci
  ) = 1
ORDER BY r.header_id, r.payment_date
"""


def fetch_candidates(cursor, sql):
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def plan_allocations(candidates):
    """计算每条候选的实际分配额：min(receipt 剩余, invoice 未付)

    同一个 receipt / invoice 在批内可能被多次匹配，需要在 Python 里
    维护"剩余/未付"的运行值，避免重复分配。
    """
    receipt_remaining = {}
    invoice_unpaid = {}
    plan = []

    for c in candidates:
        rid = c['receipt_id']
        iid = c['invoice_id']

        if rid not in receipt_remaining:
            receipt_remaining[rid] = float(c['receipt_amount']) - float(c['receipt_already_allocated'])
        if iid not in invoice_unpaid:
            invoice_unpaid[iid] = float(c['invoice_amount']) - float(c['invoice_already_allocated'])

        allocated = min(receipt_remaining[rid], invoice_unpaid[iid])
        # 浮点容差，避免分出 0.001 这种垃圾值
        if allocated < 0.01:
            continue

        allocated = round(allocated, 2)
        plan.append({
            'receipt_id': rid,
            'receipt_number': c['receipt_number'],
            'receipt_amount': float(c['receipt_amount']),
            'invoice_id': iid,
            'invoice_number': c['invoice_number'],
            'invoice_amount': float(c['invoice_amount']),
            'currency': c['currency'],
            'allocated_amount': allocated
        })
        receipt_remaining[rid] -= allocated
        invoice_unpaid[iid] -= allocated

    return plan


def print_plan(title, plan):
    if not plan:
        print(f"{title}: 没有候选")
        return
    print(f"{title}: {len(plan)} 条候选")
    print("-" * 110)
    print(f"{'收款单号':<22}{'金额':>12}  -> {'发票号':<14}{'发票金额':>12}{'本次分配':>12}  {'币种':<6}")
    print("-" * 110)
    for p in plan:
        print(f"{p['receipt_number']:<22}{p['receipt_amount']:>12.2f}  -> "
              f"{p['invoice_number']:<14}{p['invoice_amount']:>12.2f}"
              f"{p['allocated_amount']:>12.2f}  {p['currency']:<6}")
    print("-" * 110)


def insert_allocations(cursor, plan):
    if not plan:
        return 0
    sql = """
        INSERT INTO receipt_invoice_allocations
            (receipt_id, invoice_id, allocated_amount, created_at)
        VALUES (%s, %s, %s, NOW())
    """
    for p in plan:
        cursor.execute(sql, (p['receipt_id'], p['invoice_id'], p['allocated_amount']))
    return len(plan)


def refresh_invoice_paid_amount(cursor):
    """根据 allocation 表全量重算 paid_amount 和 payment_status"""
    cursor.execute("""
        UPDATE project_invoices i
        LEFT JOIN (
            SELECT ria.invoice_id, SUM(ria.allocated_amount) AS total_allocated
            FROM receipt_invoice_allocations ria
            JOIN project_receipts pr ON pr.id = ria.receipt_id
            WHERE pr.status = 'confirmed'
            GROUP BY ria.invoice_id
        ) a ON a.invoice_id = i.id
        SET
            i.paid_amount    = COALESCE(a.total_allocated, 0),
            i.payment_status = CASE
                WHEN i.amount <= 0                                       THEN 'paid'
                WHEN COALESCE(a.total_allocated, 0) >= i.amount - 0.01   THEN 'paid'
                WHEN COALESCE(a.total_allocated, 0) > 0                  THEN 'partial_paid'
                ELSE 'unpaid'
            END
        WHERE i.status <> 'cancelled'
    """)
    return cursor.rowcount


def run(execute=False):
    print("=" * 80)
    print("回填发票与收据分配记录")
    print(f"模式: {'执行模式（写库）' if execute else '预览模式（不写库）'}")
    print("=" * 80)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # ---- 1. REF 级 ----
        ref_candidates = fetch_candidates(cursor, SQL_REF_LEVEL_CANDIDATES)
        ref_plan = plan_allocations(ref_candidates)
        print_plan("【REF 级】", ref_plan)
        print()

        # ---- 2. 项目级 ----
        proj_candidates = fetch_candidates(cursor, SQL_PROJECT_LEVEL_CANDIDATES)
        proj_plan = plan_allocations(proj_candidates)
        print_plan("【项目级 - 单未付发票】", proj_plan)
        print()

        total = len(ref_plan) + len(proj_plan)
        if total == 0:
            print("没有需要回填的记录。")
            return 0

        if not execute:
            print(f"预览完成，共 {total} 条候选。如需写库请加 --execute 重跑。")
            return total

        # ---- 3. 写入 ----
        inserted = insert_allocations(cursor, ref_plan)
        inserted += insert_allocations(cursor, proj_plan)
        print(f"已插入 {inserted} 条分配记录。")

        # ---- 4. 重算 ----
        affected = refresh_invoice_paid_amount(cursor)
        print(f"已重算 {affected} 张发票的 paid_amount / payment_status。")

        conn.commit()
        print("提交成功。")
        return total

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
