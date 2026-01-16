# -*- coding: utf-8 -*-
"""
修复收款分配重复问题

问题：REF级别收款（ref_id不为空）同时在 receipt_invoice_allocations 表中有记录，
导致收款金额被重复计算。

修复：删除这些重复的分配记录。

运行方式: python scripts/fix_duplicate_receipt_allocation.py
确认执行: python scripts/fix_duplicate_receipt_allocation.py --confirm
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation


def main():
    parser = argparse.ArgumentParser(description='修复收款分配重复问题')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    args = parser.parse_args()

    dry_run = not args.confirm

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("  修复收款分配重复问题")
        print("=" * 70)

        if dry_run:
            print("\n  [预览模式 - 数据不会实际修改]")

        # 查找所有 REF 级别收款但在分配表中有记录的情况
        # 这些是重复的，需要删除分配表中的记录
        problem_receipts = db.session.query(
            ProjectReceipt.id,
            ProjectReceipt.receipt_number,
            ProjectReceipt.amount,
            ProjectReceipt.ref_id,
            ProjectReceipt.header_id
        ).join(
            ReceiptInvoiceAllocation,
            ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
        ).filter(
            ProjectReceipt.ref_id.isnot(None)
        ).distinct().all()

        if not problem_receipts:
            print("\n没有发现重复分配的问题记录。")
            return

        print(f"\n发现 {len(problem_receipts)} 条问题收款记录：")

        total_allocations_to_delete = 0

        for receipt in problem_receipts:
            # 查找该收款在分配表中的记录
            allocations = ReceiptInvoiceAllocation.query.filter_by(
                receipt_id=receipt.id
            ).all()

            print(f"\n  收款 {receipt.receipt_number} (ID:{receipt.id})")
            print(f"    金额: {receipt.amount}, ref_id: {receipt.ref_id}, header_id: {receipt.header_id}")
            print(f"    分配表中有 {len(allocations)} 条记录需要删除:")

            for alloc in allocations:
                print(f"      - allocation_id={alloc.id}, invoice_id={alloc.invoice_id}, amount={alloc.allocated_amount}")
                total_allocations_to_delete += 1

            if not dry_run:
                # 删除分配记录
                ReceiptInvoiceAllocation.query.filter_by(receipt_id=receipt.id).delete()

        print("\n" + "=" * 70)

        if not dry_run:
            try:
                db.session.commit()
                print(f"  修复完成！删除了 {total_allocations_to_delete} 条重复分配记录")
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(f"  预览完成！将删除 {total_allocations_to_delete} 条重复分配记录")
            print(f"\n确认修复请添加 --confirm 参数:")
            print(f"  python scripts/fix_duplicate_receipt_allocation.py --confirm")


if __name__ == '__main__':
    main()
