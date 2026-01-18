"""
收款分配数据迁移脚本
将旧的 project_receipts.invoice_id 关联转为 receipt_invoice_allocations 记录

运行方式: python scripts/20250118_migrate_receipt_allocations.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from App_new import create_app
from App_new.exts import db

app = create_app()


def migrate_invoice_allocations(dry_run=True):
    """将旧的 invoice_id 关联迁移到分配表"""

    with app.app_context():
        from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
        from App_new.business.projects.models.invoice import ProjectInvoice

        print(f"{'[DRY RUN] ' if dry_run else ''}开始迁移收款分配数据...")
        print("=" * 80)

        # 查找有 invoice_id 但没有对应分配记录的收款
        receipts_to_migrate = []

        receipts_with_invoice = ProjectReceipt.query.filter(
            ProjectReceipt.invoice_id.isnot(None)
        ).all()

        print(f"找到 {len(receipts_with_invoice)} 条有 invoice_id 的收款记录")

        for receipt in receipts_with_invoice:
            # 检查是否已有分配记录
            existing_allocation = ReceiptInvoiceAllocation.query.filter_by(
                receipt_id=receipt.id,
                invoice_id=receipt.invoice_id
            ).first()

            if not existing_allocation:
                receipts_to_migrate.append(receipt)

        print(f"其中 {len(receipts_to_migrate)} 条需要迁移（无对应分配记录）")
        print("-" * 80)

        migrated_count = 0
        error_count = 0

        for receipt in receipts_to_migrate:
            try:
                invoice = ProjectInvoice.query.get(receipt.invoice_id)
                if not invoice:
                    print(f"警告: 收款 {receipt.id} ({receipt.receipt_number}) 的发票 {receipt.invoice_id} 不存在")
                    error_count += 1
                    continue

                print(f"迁移: Receipt {receipt.id} ({receipt.receipt_number}) -> Invoice {invoice.id} ({invoice.invoice_number}), 金额: {receipt.amount}")

                if not dry_run:
                    # 创建分配记录
                    allocation = ReceiptInvoiceAllocation(
                        receipt_id=receipt.id,
                        invoice_id=receipt.invoice_id,
                        allocated_amount=receipt.amount  # 全额分配
                    )
                    db.session.add(allocation)

                migrated_count += 1

            except Exception as e:
                error_count += 1
                print(f"错误: Receipt {receipt.id} - {str(e)}")

        if not dry_run and migrated_count > 0:
            db.session.commit()
            print(f"\n已提交 {migrated_count} 条分配记录")

        print("=" * 80)
        print(f"总计: 需迁移 {len(receipts_to_migrate)} 条, 成功 {migrated_count} 条, 错误 {error_count} 条")

        return migrated_count, error_count


def update_invoice_paid_amounts(dry_run=True):
    """根据分配表重新计算所有发票的已付金额"""

    with app.app_context():
        from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
        from App_new.business.projects.models.invoice import ProjectInvoice

        print(f"\n{'[DRY RUN] ' if dry_run else ''}重新计算发票已付金额...")
        print("=" * 80)

        invoices = ProjectInvoice.query.filter(
            ProjectInvoice.status == 'confirmed'
        ).all()

        print(f"共 {len(invoices)} 张已确认发票")

        updated_count = 0
        for invoice in invoices:
            # 只通过分配表计算已付金额
            total_allocated = db.session.query(
                db.func.sum(ReceiptInvoiceAllocation.allocated_amount)
            ).join(
                ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
            ).filter(
                ReceiptInvoiceAllocation.invoice_id == invoice.id,
                ProjectReceipt.status == 'confirmed'
            ).scalar() or Decimal('0')

            total_allocated = float(total_allocated)
            current_paid = float(invoice.paid_amount or 0)

            if abs(total_allocated - current_paid) > 0.01:
                print(f"Invoice {invoice.id} ({invoice.invoice_number}): {current_paid:.2f} -> {total_allocated:.2f}")

                if not dry_run:
                    invoice.paid_amount = total_allocated
                    # 更新付款状态
                    amount = float(invoice.amount or 0)
                    if amount <= 0:
                        invoice.payment_status = 'paid'
                    elif total_allocated >= amount - 0.01:
                        invoice.payment_status = 'paid'
                    elif total_allocated > 0:
                        invoice.payment_status = 'partial_paid'
                    else:
                        invoice.payment_status = 'unpaid'

                updated_count += 1

        if not dry_run and updated_count > 0:
            db.session.commit()
            print(f"\n已更新 {updated_count} 张发票")

        print("=" * 80)
        print(f"总计: 检查 {len(invoices)} 张, 更新 {updated_count} 张")

        return updated_count


def update_ref_payment_status(dry_run=True):
    """根据分配表重新计算所有 REF 的付款状态"""

    with app.app_context():
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
        from App_new.business.projects.models.invoice import ProjectInvoice
        import json

        print(f"\n{'[DRY RUN] ' if dry_run else ''}重新计算 REF 付款状态...")
        print("=" * 80)

        refs = ProjectRef.query.all()
        print(f"共 {len(refs)} 个 REF")

        updated_count = 0
        for ref in refs:
            try:
                total_received = Decimal('0')

                # 1. 直接关联的收款 (ref_id)
                direct_receipts = ProjectReceipt.query.filter_by(
                    ref_id=ref.id,
                    status='confirmed'
                ).all()
                for receipt in direct_receipts:
                    total_received += Decimal(str(receipt.amount or 0))

                # 2. 通过发票分配的收款
                all_refs = ProjectRef.query.filter_by(header_id=ref.header_id).all()
                is_single_ref = len(all_refs) == 1

                invoices = ProjectInvoice.query.filter_by(
                    header_id=ref.header_id,
                    status='confirmed'
                ).all()

                for invoice in invoices:
                    # 解析 ref_ids (JSON 格式)
                    ref_id_int_list = []
                    if invoice.ref_ids:
                        try:
                            ref_id_int_list = json.loads(invoice.ref_ids)
                            if not isinstance(ref_id_int_list, list):
                                ref_id_int_list = [ref_id_int_list]
                            ref_id_int_list = [int(x) for x in ref_id_int_list]
                        except:
                            try:
                                ref_id_int_list = [int(x.strip()) for x in invoice.ref_ids.split(',') if x.strip()]
                            except:
                                pass

                    if not ref_id_int_list:
                        if is_single_ref:
                            ref_id_int_list = [ref.id]
                        else:
                            ref_id_int_list = [r.id for r in all_refs]

                    if ref.id not in ref_id_int_list:
                        continue

                    # 获取分配记录
                    allocations = ReceiptInvoiceAllocation.query.filter_by(invoice_id=invoice.id).all()
                    for alloc in allocations:
                        receipt = ProjectReceipt.query.get(alloc.receipt_id)
                        if not receipt or receipt.status != 'confirmed':
                            continue
                        # 跳过直接关联的收款（避免重复计算）
                        if receipt.ref_id == ref.id:
                            continue

                        if len(ref_id_int_list) == 1:
                            total_received += Decimal(str(alloc.allocated_amount or 0))
                        else:
                            # 按比例分配
                            total_selling = sum(
                                Decimal(str(r.selling_price or 0))
                                for r in all_refs
                                if r.id in ref_id_int_list
                            )
                            if total_selling > 0:
                                ratio = Decimal(str(ref.selling_price or 0)) / total_selling
                                total_received += Decimal(str(alloc.allocated_amount or 0)) * ratio

                # 计算新状态
                selling_price = float(ref.selling_price or 0)
                total_received_float = float(total_received)

                if selling_price <= 0:
                    new_status = 'paid'
                elif total_received_float >= selling_price - 0.01:
                    new_status = 'paid'
                elif total_received_float > 0:
                    new_status = 'partial'
                else:
                    new_status = 'unpaid'

                if ref.payment_status != new_status:
                    print(f"REF {ref.id} ({ref.ref_number}): {ref.payment_status} -> {new_status} (收款: {total_received_float:.2f}, 售价: {selling_price:.2f})")
                    if not dry_run:
                        ref.payment_status = new_status
                    updated_count += 1

            except Exception as e:
                print(f"错误: REF {ref.id} - {str(e)}")

        if not dry_run and updated_count > 0:
            db.session.commit()
            print(f"\n已更新 {updated_count} 个 REF")

        print("=" * 80)
        print(f"总计: 检查 {len(refs)} 个, 更新 {updated_count} 个")

        return updated_count


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='收款分配数据迁移')
    parser.add_argument('--execute', action='store_true', help='执行迁移（默认只预览）')
    args = parser.parse_args()

    dry_run = not args.execute

    if not dry_run:
        confirm = input("确定要执行迁移吗？输入 'yes' 确认: ")
        if confirm.lower() != 'yes':
            print("已取消")
            sys.exit(0)

    # 步骤1: 迁移 invoice_id 到分配表
    migrate_invoice_allocations(dry_run=dry_run)

    # 步骤2: 重新计算发票已付金额
    update_invoice_paid_amounts(dry_run=dry_run)

    # 步骤3: 重新计算 REF 付款状态
    update_ref_payment_status(dry_run=dry_run)

    if dry_run:
        print("\n" + "=" * 80)
        print("这是预览模式，未实际修改数据。")
        print("如需执行迁移，请运行: python scripts/20250118_migrate_receipt_allocations.py --execute")
