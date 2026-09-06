# -*- coding: utf-8 -*-
"""收款-发票分配表体检与修补

receipt_invoice_allocations 是「一笔收款分别核销了哪几张发票」的分配表，
应收余额、对账、客户对账单都靠它。早期的收款是用 project_receipts.invoice_id
直接挂一张发票的（这个字段现在已废弃），改成分配表之后历史数据没有全部搬过来，
于是有些收款在分配表里查不到，应收看上去就没收过钱。

本脚本查五类问题，只自动修第一类：

  1. 有 invoice_id、分配表里没有        -> 自动补一条分配（金额取收款额与发票未收额的较小值）
  2. 没有 invoice_id、分配表里也没有    -> 只报不改：不知道该核销哪张发票，得人来定；
                                          如果这笔本来就是预收款，应该在收款页改成「预收款」
  3. 分配额合计 != 收款额               -> 只报不改（分多了是已知的超额分配问题，
                                          分少了是没分完），涉及钱的方向，人来判断
  4. 分配额合计 > 发票金额              -> 只报不改（同一张发票被多笔收款重复核销）
  5. 已取消的收款还留着分配记录        -> 只报不改（票面看上去收过钱，其实收款作废了）

已取消（status='cancelled'）的收款不参与 1~3 类检查 —— 作废的收款本来就不该有分配。

预收款（receipt_type='advance'）不参与检查 —— 它开票前就收了钱，
本来就没有发票可分配，抵扣时才会写分配记录。

运行方式:
    python scripts/tools/20260906_repair_receipt_allocations.py            # 只看不改
    python scripts/tools/20260906_repair_receipt_allocations.py --apply    # 补第 1 类

放在 scripts/tools/ 而不是 scripts/：部署脚本会自动跑 scripts/ 下所有日期开头的
文件，这个要人看过报告再决定。
"""

import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from App_new import create_app
from App_new.exts import db

app = create_app()

# 1. 老字段挂了发票、分配表里却没有
LEGACY_SQL = """
SELECT r.id, r.receipt_number, r.payment_date, r.amount, r.invoice_id,
       i.invoice_number, i.amount AS invoice_amount,
       COALESCE((SELECT SUM(a2.allocated_amount)
                   FROM receipt_invoice_allocations a2
                  WHERE a2.invoice_id = r.invoice_id), 0) AS invoice_allocated
FROM project_receipts r
JOIN project_invoices i ON i.id = r.invoice_id
LEFT JOIN receipt_invoice_allocations a ON a.receipt_id = r.id
WHERE r.invoice_id IS NOT NULL
  AND a.id IS NULL
  AND r.receipt_type = 'payment'
  AND r.status <> 'cancelled'
ORDER BY r.payment_date, r.id
"""

# 2. 完全没有归属的收款
ORPHAN_SQL = """
SELECT r.id, r.receipt_number, r.payment_date, r.amount, r.header_id, r.status
FROM project_receipts r
LEFT JOIN receipt_invoice_allocations a ON a.receipt_id = r.id
WHERE r.invoice_id IS NULL
  AND a.id IS NULL
  AND r.receipt_type = 'payment'
  AND r.status <> 'cancelled'
ORDER BY r.payment_date, r.id
"""

# 3. 分配额跟收款额对不上
MISMATCH_SQL = """
SELECT r.id, r.receipt_number, r.payment_date, r.amount,
       SUM(a.allocated_amount) AS allocated
FROM project_receipts r
JOIN receipt_invoice_allocations a ON a.receipt_id = r.id
WHERE r.status <> 'cancelled'
GROUP BY r.id, r.receipt_number, r.payment_date, r.amount
HAVING SUM(a.allocated_amount) <> r.amount
ORDER BY r.payment_date, r.id
"""

# 4. 一张发票被核销超过票面金额
OVER_SQL = """
SELECT i.id, i.invoice_number, i.amount,
       SUM(a.allocated_amount) AS allocated
FROM project_invoices i
JOIN receipt_invoice_allocations a ON a.invoice_id = i.id
GROUP BY i.id, i.invoice_number, i.amount
HAVING SUM(a.allocated_amount) > i.amount
ORDER BY SUM(a.allocated_amount) - i.amount DESC
"""

# 5. 收款已作废，分配记录还挂着
CANCELLED_SQL = """
SELECT r.receipt_number, r.payment_date, i.invoice_number, a.allocated_amount
FROM receipt_invoice_allocations a
JOIN project_receipts r ON r.id = a.receipt_id
JOIN project_invoices i ON i.id = a.invoice_id
WHERE r.status = 'cancelled'
ORDER BY r.payment_date
"""


def _print_rows(rows, header, fmt, limit=30):
    print(header)
    for row in rows[:limit]:
        print(fmt(row))
    if len(rows) > limit:
        print('  ... 共 %s 条' % len(rows))
    print()


def main(apply_changes):
    with app.app_context():
        legacy = db.session.execute(text(LEGACY_SQL)).fetchall()
        orphan = db.session.execute(text(ORPHAN_SQL)).fetchall()
        mismatch = db.session.execute(text(MISMATCH_SQL)).fetchall()
        over = db.session.execute(text(OVER_SQL)).fetchall()
        cancelled = db.session.execute(text(CANCELLED_SQL)).fetchall()

        print('=' * 60)
        print('1) 有 invoice_id 但分配表缺记录：%s 条（可自动补）' % len(legacy))
        print('2) 无 invoice_id 也无分配记录  ：%s 条（需人工）' % len(orphan))
        print('3) 分配额 != 收款额            ：%s 条（需人工）' % len(mismatch))
        print('4) 发票被核销超过票面金额      ：%s 张（需人工）' % len(over))
        print('5) 已取消的收款还留着分配记录  ：%s 条（需人工）' % len(cancelled))
        print('=' * 60)
        print()

        if legacy:
            _print_rows(
                legacy,
                '【1】可自动补的分配：',
                lambda r: '  收款 %-16s %s  %10s  ->  发票 %-16s 票面 %10s 已分配 %10s' % (
                    r.receipt_number, r.payment_date, r.amount,
                    r.invoice_number, r.invoice_amount, r.invoice_allocated))

        if orphan:
            _print_rows(
                orphan,
                '【2】收了钱但不知道核销哪张发票（要么手工分配，要么改成预收款）：',
                lambda r: '  收款 %-16s %s  %10s  项目 header_id=%s  状态 %s' % (
                    r.receipt_number, r.payment_date, r.amount, r.header_id, r.status))

        if mismatch:
            _print_rows(
                mismatch,
                '【3】分配额跟收款额对不上：',
                lambda r: '  收款 %-16s %s  收款额 %10s  已分配 %10s  差 %10s' % (
                    r.receipt_number, r.payment_date, r.amount, r.allocated,
                    Decimal(str(r.allocated)) - Decimal(str(r.amount))))

        if over:
            _print_rows(
                over,
                '【4】发票被核销超过票面金额（同一张票被重复核销）：',
                lambda r: '  发票 %-16s 票面 %10s  已核销 %10s  超 %10s' % (
                    r.invoice_number, r.amount, r.allocated,
                    Decimal(str(r.allocated)) - Decimal(str(r.amount))))

        if cancelled:
            _print_rows(
                cancelled,
                '【5】收款已作废但分配记录还在（发票会显示成已收款）：',
                lambda r: '  收款 %-16s %s  ->  发票 %-16s %10s' % (
                    r.receipt_number, r.payment_date, r.invoice_number, r.allocated_amount))

        if not legacy:
            print('[完成] 没有可自动补的分配记录')
            return

        if not apply_changes:
            print('[试运行] 上面第 1 类的 %s 条会补进分配表。加 --apply 才真的执行。' % len(legacy))
            return

        created = 0
        skipped = []
        for row in legacy:
            receipt_amount = Decimal(str(row.amount or 0))
            outstanding = Decimal(str(row.invoice_amount or 0)) - Decimal(str(row.invoice_allocated or 0))
            # 补的金额不能把发票核销穿：取收款额和发票未核销额的较小值
            take = min(receipt_amount, outstanding)
            if take <= 0:
                skipped.append('%s（发票 %s 已核销满）' % (row.receipt_number, row.invoice_number))
                continue

            db.session.execute(text(
                'INSERT INTO receipt_invoice_allocations '
                '(receipt_id, invoice_id, allocated_amount, created_at) '
                'VALUES (:rid, :iid, :amt, NOW())'
            ), {'rid': row.id, 'iid': row.invoice_id, 'amt': take})
            created += 1
            if take != receipt_amount:
                skipped.append('%s（只补了 %s，收款额 %s，发票余额不够）' % (
                    row.receipt_number, take, receipt_amount))

        db.session.commit()
        print('[完成] 补入 %s 条分配记录' % created)
        if skipped:
            print('[注意] 以下需要再看一眼：')
            for note in skipped:
                print('    ' + note)


if __name__ == '__main__':
    main('--apply' in sys.argv)
