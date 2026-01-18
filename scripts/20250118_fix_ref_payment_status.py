"""
修复 REF 付款状态脚本
根据实际收款记录重新计算并更新所有 REF 的 payment_status

运行方式: python scripts/20250118_fix_ref_payment_status.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from App_new import create_app
from App_new.exts import db

app = create_app()


def get_ref_total_received(ref, ProjectRef, ProjectInvoice, ProjectReceipt, ReceiptInvoiceAllocation):
    """计算 REF 的总收款金额"""
    total_received = Decimal('0')

    # 1. 直接关联到此 REF 的收款
    direct_receipts = ProjectReceipt.query.filter_by(
        ref_id=ref.id,
        status='confirmed'
    ).all()

    for receipt in direct_receipts:
        total_received += Decimal(str(receipt.amount or 0))

    # 2. 通过发票分配关联的收款
    # 获取项目下所有 REF
    all_refs = ProjectRef.query.filter_by(project_id=ref.project_id).all()
    is_single_ref = len(all_refs) == 1

    # 获取关联此 REF 的发票
    invoices = ProjectInvoice.query.filter_by(
        project_id=ref.project_id,
        status='confirmed'
    ).all()

    for invoice in invoices:
        # 解析发票的 ref_ids
        ref_id_int_list = []
        if invoice.ref_ids:
            try:
                ref_id_int_list = [int(x.strip()) for x in invoice.ref_ids.split(',') if x.strip()]
            except:
                pass

        # 如果发票没有 ref_ids
        if not ref_id_int_list:
            if is_single_ref:
                # 单 REF 项目，分配给这个 REF
                ref_id_int_list = [ref.id]
            else:
                # 多 REF 项目，按比例分配给所有 REF
                ref_id_int_list = [r.id for r in all_refs]

        # 检查此 REF 是否在发票关联的 REF 列表中
        if ref.id not in ref_id_int_list:
            continue

        # 获取发票的所有分配记录
        allocations = ReceiptInvoiceAllocation.query.filter_by(invoice_id=invoice.id).all()

        for alloc in allocations:
            # 检查收款状态
            receipt = ProjectReceipt.query.get(alloc.receipt_id)
            if not receipt or receipt.status != 'confirmed':
                continue

            # 如果收款已经直接关联到 REF，跳过避免重复计算
            if receipt.ref_id == ref.id:
                continue

            # 计算分配给此 REF 的金额
            if len(ref_id_int_list) == 1:
                # 单 REF，全额分配
                total_received += Decimal(str(alloc.allocated_amount or 0))
            else:
                # 多 REF，按 selling_price 比例分配
                total_selling = sum(
                    Decimal(str(r.selling_price or 0))
                    for r in all_refs
                    if r.id in ref_id_int_list
                )
                if total_selling > 0:
                    ref_selling = Decimal(str(ref.selling_price or 0))
                    ratio = ref_selling / total_selling
                    total_received += Decimal(str(alloc.allocated_amount or 0)) * ratio

    return float(total_received)


def fix_ref_payment_status(dry_run=True):
    """修复所有 REF 的付款状态"""

    # 在 app context 内导入模型
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
    from App_new.business.projects.models.invoice import ProjectInvoice

    print(f"{'[DRY RUN] ' if dry_run else ''}开始修复 REF 付款状态...")
    print("-" * 80)

    # 获取所有 REF
    refs = ProjectRef.query.all()
    print(f"共有 {len(refs)} 个 REF 需要检查")

    updated_count = 0
    error_count = 0
    changes = []

    for ref in refs:
        try:
            selling_price = float(ref.selling_price or 0)
            total_received = get_ref_total_received(
                ref, ProjectRef, ProjectInvoice, ProjectReceipt, ReceiptInvoiceAllocation
            )

            # 计算新状态
            if selling_price <= 0:
                new_status = 'paid'  # 无需付款
            elif total_received >= selling_price - 0.01:  # 允许 0.01 误差
                new_status = 'paid'
            elif total_received > 0:
                new_status = 'partial_paid'
            else:
                new_status = 'unpaid'

            old_status = ref.payment_status

            # 检查是否需要更新
            if old_status != new_status:
                changes.append({
                    'ref_id': ref.id,
                    'ref_no': ref.ref_no,
                    'project_id': ref.project_id,
                    'selling_price': selling_price,
                    'total_received': total_received,
                    'old_status': old_status,
                    'new_status': new_status
                })

                if not dry_run:
                    ref.payment_status = new_status
                    db.session.add(ref)

                updated_count += 1

        except Exception as e:
            error_count += 1
            print(f"错误: REF {ref.id} ({ref.ref_no}) - {str(e)}")

    # 打印变更详情
    if changes:
        print(f"\n需要更新的 REF ({len(changes)} 个):")
        print("-" * 80)
        print(f"{'REF ID':<8} {'REF NO':<15} {'Project':<10} {'Selling':<12} {'Received':<12} {'Old':<15} {'New':<15}")
        print("-" * 80)

        for c in changes:
            print(f"{c['ref_id']:<8} {c['ref_no']:<15} {c['project_id']:<10} {c['selling_price']:<12.2f} {c['total_received']:<12.2f} {c['old_status']:<15} {c['new_status']:<15}")

    if not dry_run and updated_count > 0:
        db.session.commit()
        print(f"\n已提交 {updated_count} 个 REF 的状态更新")

    print("-" * 80)
    print(f"总计: 检查 {len(refs)} 个, 需更新 {updated_count} 个, 错误 {error_count} 个")

    return updated_count, error_count


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='修复 REF 付款状态')
    parser.add_argument('--execute', action='store_true', help='执行更新（默认只预览）')
    args = parser.parse_args()

    dry_run = not args.execute

    with app.app_context():
        if not dry_run:
            confirm = input("确定要执行更新吗？输入 'yes' 确认: ")
            if confirm.lower() != 'yes':
                print("已取消")
                sys.exit(0)

        fix_ref_payment_status(dry_run=dry_run)

        if dry_run:
            print("\n这是预览模式，未实际修改数据。")
            print("如需执行更新，请运行: python scripts/20250118_fix_ref_payment_status.py --execute")
