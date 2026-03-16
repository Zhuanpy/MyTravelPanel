"""
修复项目2551的收款分配数据

问题：手动指定发票收款时，按比例分配算法有bug，
使用remaining_amount（递减值）而非原始amount计算比例，
导致分配总额小于收款金额。

此脚本：
1. 检查项目2551的所有收款记录
2. 找出分配不匹配的记录（receipt.amount != sum(allocations)）
3. 根据extra_info重新分配
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

def fix_project_receipts(header_id, dry_run=True):
    """检查并修复指定项目的收款分配"""
    with app.app_context():
        from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
        from App_new.business.projects.models.invoice import ProjectInvoice
        from App_new.business.projects.models.project import ProjectHeader
        from sqlalchemy import func
        import json

        header = ProjectHeader.query.get(header_id)
        if not header:
            print(f"项目 {header_id} 不存在")
            return

        print(f"=" * 60)
        print(f"项目: {header.hid} - {header.desc}")
        print(f"=" * 60)

        # 获取所有收款记录
        receipts = ProjectReceipt.query.filter_by(
            header_id=header_id,
            status='confirmed'
        ).all()

        print(f"\n共有 {len(receipts)} 条已确认收款记录\n")

        issues_found = 0

        for receipt in receipts:
            # 计算分配总额
            alloc_total = db.session.query(
                func.sum(ReceiptInvoiceAllocation.allocated_amount)
            ).filter_by(receipt_id=receipt.id).scalar() or 0
            alloc_total = float(alloc_total)
            receipt_amount = float(receipt.amount or 0)

            # 获取分配记录
            allocations = ReceiptInvoiceAllocation.query.filter_by(
                receipt_id=receipt.id
            ).all()

            diff = abs(receipt_amount - alloc_total)

            # 显示每条收款的信息
            status_icon = "✓" if diff < 0.01 else "✗"
            print(f"{status_icon} 收款 {receipt.receipt_number}")
            print(f"  金额: {receipt.currency} {receipt_amount:.2f}")
            print(f"  分配总额: {alloc_total:.2f}")
            if diff >= 0.01:
                print(f"  *** 差额: {diff:.2f} (丢失 {diff/receipt_amount*100:.1f}%) ***")

            # 显示各分配
            for alloc in allocations:
                inv = ProjectInvoice.query.get(alloc.invoice_id)
                inv_num = inv.invoice_number if inv else f"ID:{alloc.invoice_id}"
                print(f"    → {inv_num}: {float(alloc.allocated_amount):.2f}")

            # 显示extra_info
            if receipt.extra_info:
                try:
                    extra = json.loads(receipt.extra_info)
                    method = extra.get('distribution_method', 'unknown')
                    remaining = extra.get('remaining_amount', 0)
                    print(f"  分配方式: {method}, 记录的remaining: {remaining:.2f}")
                except:
                    pass

            print()

            # 如果有差额，修复
            if diff >= 0.01:
                issues_found += 1
                if not dry_run:
                    fix_receipt_allocation(receipt, allocations, receipt_amount)

        # 显示发票状态
        print(f"\n{'=' * 60}")
        print("发票状态:")
        print(f"{'=' * 60}")
        invoices = ProjectInvoice.query.filter_by(header_id=header_id).filter(
            ProjectInvoice.status != 'cancelled'
        ).all()
        for inv in invoices:
            alloc_sum = db.session.query(
                func.sum(ReceiptInvoiceAllocation.allocated_amount)
            ).filter_by(invoice_id=inv.id).join(
                ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
            ).filter(
                ProjectReceipt.status == 'confirmed'
            ).scalar() or 0
            alloc_sum = float(alloc_sum)
            inv_amount = float(inv.amount or 0)
            inv_paid = float(inv.paid_amount or 0)
            print(f"  {inv.invoice_number}: 金额={inv_amount:.2f}, "
                  f"paid_amount={inv_paid:.2f}, "
                  f"分配表合计={alloc_sum:.2f}, "
                  f"状态={inv.payment_status}")
            if abs(inv_paid - alloc_sum) >= 0.01:
                print(f"    *** paid_amount 与分配表不一致！差额: {inv_paid - alloc_sum:.2f} ***")

        print(f"\n总计发现 {issues_found} 条分配异常的收款记录")

        if issues_found > 0 and dry_run:
            print("\n当前为检查模式(dry_run=True)，未修改数据。")
            print("确认无误后请使用 dry_run=False 执行修复。")


def fix_receipt_allocation(receipt, allocations, receipt_amount):
    """修复单条收款的分配"""
    import json
    from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
    from App_new.business.projects.models.invoice import ProjectInvoice

    if not allocations:
        print(f"  [跳过] 没有分配记录，无法自动修复")
        return

    # 计算正确的按比例分配
    total_unpaid_at_alloc = sum(float(a.allocated_amount) for a in allocations)
    if total_unpaid_at_alloc <= 0:
        print(f"  [跳过] 分配总额为0")
        return

    remaining = receipt_amount
    for i, alloc in enumerate(allocations):
        old_amount = float(alloc.allocated_amount)
        inv = ProjectInvoice.query.get(alloc.invoice_id)
        inv_amount = float(inv.amount or 0) if inv else 999999
        inv_paid_other = float(inv.paid_amount or 0) - old_amount  # 该发票其他收款的付款额

        if i == len(allocations) - 1:
            # 最后一条：分配所有剩余
            new_amount = min(remaining, inv_amount - max(0, inv_paid_other))
        else:
            # 按比例重新计算
            ratio = old_amount / total_unpaid_at_alloc
            new_amount = round(receipt_amount * ratio, 2)
            new_amount = min(new_amount, inv_amount - max(0, inv_paid_other))

        new_amount = max(0, new_amount)
        remaining -= new_amount

        if abs(new_amount - old_amount) >= 0.01:
            print(f"  [修复] {inv.invoice_number if inv else alloc.invoice_id}: "
                  f"{old_amount:.2f} → {new_amount:.2f}")
            alloc.allocated_amount = new_amount

    # 更新所有受影响发票的paid_amount
    for alloc in allocations:
        ProjectReceipt.update_invoice_paid_amount(alloc.invoice_id)

    db.session.commit()
    print(f"  [完成] 收款 {receipt.receipt_number} 分配已修复")


if __name__ == '__main__':
    # 先用检查模式查看数据
    # 通过hid查找header_id
    with app.app_context():
        from App_new.business.projects.models.project import ProjectHeader
        # 尝试用hid=2551查找
        header = ProjectHeader.query.filter_by(hid='2551').first()
        if not header:
            # 尝试用id查找
            header = ProjectHeader.query.get(2551)
        if header:
            print(f"找到项目: ID={header.id}, HID={header.hid}")
            fix_project_receipts(header.id, dry_run=True)
        else:
            print("未找到项目 2551，请确认项目ID或HID")
