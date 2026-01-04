# -*- coding: utf-8 -*-
"""
同步发票已付金额脚本
从分配表 (receipt_invoice_allocations) 和直接关联的收款记录更新发票的 paid_amount

逻辑：
1. 获取每张发票的分配总额（从 receipt_invoice_allocations 表，只统计 confirmed 状态的收款）
2. 获取每张发票直接关联的收款总额（从 project_receipts 表，只统计 confirmed 状态）
3. 取两者较大值更新到发票的 paid_amount
4. 更新发票状态（paid/partial_paid/sent）
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from App_new.exts import db
from App_new.config import Config
from decimal import Decimal


def create_minimal_app():
    """创建最小化应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def check_specific_invoice(invoice_number):
    """检查特定发票的分配情况"""
    print(f"\n{'='*60}")
    print(f"检查发票: {invoice_number}")
    print("=" * 60)

    # 获取发票信息
    invoice_sql = """
        SELECT id, invoice_number, amount, paid_amount, status, currency
        FROM project_invoices
        WHERE invoice_number = :invoice_number
    """
    result = db.session.execute(db.text(invoice_sql), {'invoice_number': invoice_number})
    invoice = result.fetchone()

    if not invoice:
        print(f"  未找到发票: {invoice_number}")
        return

    inv_id = invoice[0]
    print(f"  发票ID: {inv_id}")
    print(f"  金额: {invoice[5]} {invoice[2]}")
    print(f"  已付: {invoice[3] or 0}")
    print(f"  状态: {invoice[4]}")

    # 检查分配记录
    alloc_sql = """
        SELECT a.id, a.receipt_id, a.allocated_amount, r.receipt_number, r.status
        FROM receipt_invoice_allocations a
        JOIN project_receipts r ON a.receipt_id = r.id
        WHERE a.invoice_id = :invoice_id
    """
    alloc_result = db.session.execute(db.text(alloc_sql), {'invoice_id': inv_id})
    allocations = alloc_result.fetchall()

    print(f"\n  分配记录 ({len(allocations)} 条):")
    alloc_total = Decimal('0')
    for alloc in allocations:
        print(f"    - 收款ID: {alloc[1]}, 单号: {alloc[3]}, 分配金额: {alloc[2]}, 收款状态: {alloc[4]}")
        if alloc[4] == 'confirmed':
            alloc_total += Decimal(str(alloc[2] or 0))
    print(f"  分配总额(confirmed): {alloc_total}")

    # 检查直接关联的收款
    direct_sql = """
        SELECT id, receipt_number, amount, status
        FROM project_receipts
        WHERE invoice_id = :invoice_id
    """
    direct_result = db.session.execute(db.text(direct_sql), {'invoice_id': inv_id})
    direct_receipts = direct_result.fetchall()

    print(f"\n  直接关联收款 ({len(direct_receipts)} 条):")
    direct_total = Decimal('0')
    for r in direct_receipts:
        print(f"    - 收款ID: {r[0]}, 单号: {r[1]}, 金额: {r[2]}, 状态: {r[3]}")
        if r[3] == 'confirmed':
            direct_total += Decimal(str(r[2] or 0))
    print(f"  直接关联总额(confirmed): {direct_total}")

    final_paid = max(alloc_total, direct_total)
    print(f"\n  应更新的 paid_amount: {final_paid}")


def sync_invoice_paid_amount():
    """同步发票已付金额"""
    app = create_minimal_app()

    with app.app_context():
        # 先检查特定发票
        check_specific_invoice('INV20251212001')

        print("\n" + "=" * 60)
        print("开始同步所有发票已付金额...")
        print("=" * 60)

        # 1. 获取所有发票的分配总额（从分配表，只统计 confirmed 状态的收款）
        alloc_sql = """
            SELECT a.invoice_id, SUM(a.allocated_amount) as total_allocated
            FROM receipt_invoice_allocations a
            JOIN project_receipts r ON a.receipt_id = r.id
            WHERE r.status = 'confirmed'
            GROUP BY a.invoice_id
        """
        alloc_result = db.session.execute(db.text(alloc_sql))
        invoice_allocations = {row[0]: Decimal(str(row[1] or 0)) for row in alloc_result.fetchall()}

        print(f"\n从分配表找到 {len(invoice_allocations)} 张发票有分配记录")

        # 2. 获取所有发票的直接关联收款总额
        direct_sql = """
            SELECT invoice_id, SUM(amount) as total_direct
            FROM project_receipts
            WHERE invoice_id IS NOT NULL AND status = 'confirmed'
            GROUP BY invoice_id
        """
        direct_result = db.session.execute(db.text(direct_sql))
        invoice_direct = {row[0]: Decimal(str(row[1] or 0)) for row in direct_result.fetchall()}

        print(f"从直接关联找到 {len(invoice_direct)} 张发票有收款记录")

        # 3. 合并所有需要处理的发票ID
        all_invoice_ids = set(invoice_allocations.keys()) | set(invoice_direct.keys())
        print(f"共需处理 {len(all_invoice_ids)} 张发票")
        print("-" * 60)

        updated_invoices = 0

        for inv_id in all_invoice_ids:
            # 获取发票信息
            invoice_sql = """
                SELECT id, invoice_number, amount, paid_amount, status
                FROM project_invoices
                WHERE id = :id AND status != 'cancelled'
            """
            invoice_result = db.session.execute(db.text(invoice_sql), {'id': inv_id})
            invoice = invoice_result.fetchone()

            if not invoice:
                continue

            inv_number = invoice[1]
            inv_amount = Decimal(str(invoice[2] or 0))
            old_paid = Decimal(str(invoice[3] or 0))
            old_status = invoice[4]

            # 计算新的已付金额（取分配和直接关联的较大值）
            alloc_total = invoice_allocations.get(inv_id, Decimal('0'))
            direct_total = invoice_direct.get(inv_id, Decimal('0'))
            new_paid = max(alloc_total, direct_total)

            # 确定新状态
            if inv_amount > 0 and new_paid >= inv_amount:
                new_status = 'paid'
            elif new_paid > 0:
                new_status = 'partial_paid'
            else:
                new_status = 'sent'

            # 检查是否需要更新
            if abs(old_paid - new_paid) > Decimal('0.01') or old_status != new_status:
                db.session.execute(
                    db.text("""
                        UPDATE project_invoices
                        SET paid_amount = :paid_amount, status = :status
                        WHERE id = :id
                    """),
                    {'paid_amount': float(new_paid), 'status': new_status, 'id': inv_id}
                )
                print(f"  发票 {inv_number}: 金额={inv_amount}")
                print(f"    分配: {alloc_total}, 直接: {direct_total}")
                print(f"    已付: {old_paid} -> {new_paid}")
                print(f"    状态: {old_status} -> {new_status}")
                updated_invoices += 1

        # 提交更改
        if updated_invoices > 0:
            try:
                db.session.commit()
                print("-" * 60)
                print(f"成功更新 {updated_invoices} 张发票")
            except Exception as e:
                db.session.rollback()
                print(f"更新失败: {e}")
                return
        else:
            print("\n没有需要更新的发票")

        # 4. 打印最终统计
        print("-" * 60)
        print("最终状态统计:")
        stats_sql = """
            SELECT status, COUNT(*) as cnt
            FROM project_invoices
            WHERE status != 'cancelled'
            GROUP BY status
        """
        stats_result = db.session.execute(db.text(stats_sql))
        for row in stats_result.fetchall():
            status_name = {
                'sent': 'Unpaid',
                'partial_paid': 'Partial Paid',
                'paid': 'Paid'
            }.get(row[0], row[0])
            print(f"  - {status_name}: {row[1]}")

        # 再次检查特定发票
        check_specific_invoice('INV20251212001')


if __name__ == '__main__':
    sync_invoice_paid_amount()
