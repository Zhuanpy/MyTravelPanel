# -*- coding: utf-8 -*-
"""
同步发票付款状态脚本

问题：以前的收款记录是根据REF或EO来付款的，现在统一成通过Invoice付款，
但有些老的收款记录没有关联到Invoice，导致Invoice显示为未付款状态。

解决方案：
1. 遍历所有发票
2. 根据发票关联的REF，计算实际已收款金额
3. 更新发票的 paid_amount 和 payment_status

使用方法:
    python scripts/20260110_sync_invoice_payment_status.py           # 预览模式（不修改数据）
    python scripts/20260110_sync_invoice_payment_status.py --execute  # 执行模式
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def get_ref_total_received(ref_id, header_id):
    """获取REF的实际已收款总额（包括项目级别收款记录的分配）"""
    from App_new.business.projects.models.receipt import ProjectReceipt

    # 1. 直接关联的REF级别收款记录
    ref_receipts = ProjectReceipt.query.filter_by(ref_id=ref_id, status='confirmed').all()
    total_received = sum(float(r.amount) for r in ref_receipts)

    # 2. 项目级别收款记录中分配给该REF的金额
    project_receipts = ProjectReceipt.query.filter_by(header_id=header_id, ref_id=None, status='confirmed').all()
    for project_receipt in project_receipts:
        if project_receipt.extra_info:
            try:
                distribution_info = json.loads(project_receipt.extra_info)
                if 'distribution' in distribution_info:
                    for dist in distribution_info['distribution']:
                        if dist.get('ref_id') == ref_id:
                            total_received += dist.get('amount', 0)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    return total_received


def get_invoice_received_from_refs(invoice):
    """根据发票关联的REF计算已收款金额"""
    if not invoice.ref_ids:
        return 0

    try:
        ref_id_list = json.loads(invoice.ref_ids)
    except (json.JSONDecodeError, TypeError):
        return 0

    if not ref_id_list:
        return 0

    total_received = 0
    for ref_id in ref_id_list:
        ref_received = get_ref_total_received(ref_id, invoice.header_id)
        total_received += ref_received

    return total_received


def get_invoice_direct_receipts(invoice_id):
    """获取直接关联到发票的收款总额"""
    from App_new.business.projects.models.receipt import ProjectReceipt
    from sqlalchemy import func

    result = db.session.query(func.sum(ProjectReceipt.amount)).filter(
        ProjectReceipt.invoice_id == invoice_id,
        ProjectReceipt.status == 'confirmed'
    ).scalar()
    return float(result) if result else 0


def get_invoice_allocated_receipts(invoice_id):
    """获取通过分配表关联到发票的收款总额"""
    from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
    from sqlalchemy import func

    result = db.session.query(func.sum(ReceiptInvoiceAllocation.allocated_amount)).filter(
        ReceiptInvoiceAllocation.invoice_id == invoice_id
    ).join(
        ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
    ).filter(
        ProjectReceipt.status == 'confirmed'
    ).scalar()
    return float(result) if result else 0


def calculate_invoice_paid_amount(invoice):
    """
    计算发票的实际已付金额

    综合考虑以下来源：
    1. 直接关联到发票的收款记录 (receipt.invoice_id = invoice.id)
    2. 通过分配表关联的收款 (receipt_invoice_allocations)
    3. 通过REF关联的收款（旧数据兼容）
    """
    # 方式1: 直接关联的收款
    direct_amount = get_invoice_direct_receipts(invoice.id)

    # 方式2: 通过分配表关联的收款
    allocated_amount = get_invoice_allocated_receipts(invoice.id)

    # 方式3: 通过REF关联的收款（旧数据）
    ref_amount = get_invoice_received_from_refs(invoice)

    # 取最大值（避免重复计算，因为新旧方式可能有重叠）
    # 逻辑：如果已有直接关联或分配表记录，则以此为准
    # 如果都没有，则使用REF计算的金额
    if direct_amount > 0 or allocated_amount > 0:
        return max(direct_amount, allocated_amount)
    else:
        return ref_amount


def determine_payment_status(amount, paid_amount):
    """根据金额确定付款状态"""
    if amount <= 0:
        return 'paid'
    if paid_amount >= amount:
        return 'paid'
    elif paid_amount > 0:
        return 'partial_paid'
    else:
        return 'unpaid'


def sync_invoice_payment_status(execute=False):
    """
    同步所有发票的付款状态

    Args:
        execute: True=执行更新, False=仅预览
    """
    from App_new.business.projects.models.invoice import ProjectInvoice

    print("=" * 80)
    print("发票付款状态同步脚本")
    print("=" * 80)
    print(f"模式: {'执行模式' if execute else '预览模式（不修改数据）'}")
    print()

    # 获取所有未取消的发票
    invoices = ProjectInvoice.query.filter(
        ProjectInvoice.status != 'cancelled'
    ).order_by(ProjectInvoice.id).all()

    print(f"共找到 {len(invoices)} 张有效发票")
    print()

    updated_count = 0
    need_update = []

    for invoice in invoices:
        # 计算实际已付金额
        calculated_paid = calculate_invoice_paid_amount(invoice)
        calculated_status = determine_payment_status(
            float(invoice.amount or 0),
            calculated_paid
        )

        current_paid = float(invoice.paid_amount or 0)
        current_status = invoice.payment_status

        # 检查是否需要更新
        need_paid_update = abs(calculated_paid - current_paid) > 0.01
        need_status_update = calculated_status != current_status

        if need_paid_update or need_status_update:
            need_update.append({
                'invoice': invoice,
                'current_paid': current_paid,
                'calculated_paid': calculated_paid,
                'current_status': current_status,
                'calculated_status': calculated_status
            })

    # 显示需要更新的发票
    if need_update:
        print(f"需要更新的发票: {len(need_update)} 张")
        print("-" * 80)
        print(f"{'发票号':<20} {'项目ID':<10} {'发票金额':>12} {'当前已付':>12} {'计算已付':>12} {'当前状态':<15} {'计算状态':<15}")
        print("-" * 80)

        for item in need_update:
            inv = item['invoice']
            print(f"{inv.invoice_number:<20} {inv.header_id:<10} {float(inv.amount):>12.2f} "
                  f"{item['current_paid']:>12.2f} {item['calculated_paid']:>12.2f} "
                  f"{item['current_status']:<15} {item['calculated_status']:<15}")

        print("-" * 80)
        print()

        if execute:
            print("正在执行更新...")
            for item in need_update:
                inv = item['invoice']
                inv.paid_amount = item['calculated_paid']
                inv.payment_status = item['calculated_status']
                updated_count += 1

            db.session.commit()
            print(f"成功更新 {updated_count} 张发票")
        else:
            print("预览模式，未执行更新。")
            print("如需执行更新，请运行: python scripts/20260110_sync_invoice_payment_status.py --execute")
    else:
        print("所有发票的付款状态已是最新，无需更新。")

    print()
    print("=" * 80)

    # 统计信息
    print("\n统计信息:")
    print("-" * 40)

    # 重新查询统计
    from sqlalchemy import func

    status_stats = db.session.query(
        ProjectInvoice.payment_status,
        func.count(ProjectInvoice.id),
        func.sum(ProjectInvoice.amount),
        func.sum(ProjectInvoice.paid_amount)
    ).filter(
        ProjectInvoice.status != 'cancelled'
    ).group_by(ProjectInvoice.payment_status).all()

    total_invoices = 0
    total_amount = 0
    total_paid = 0

    for status, count, amount, paid in status_stats:
        print(f"  {status:<15}: {count:>5} 张, 金额: {float(amount or 0):>12.2f}, 已付: {float(paid or 0):>12.2f}")
        total_invoices += count
        total_amount += float(amount or 0)
        total_paid += float(paid or 0)

    print("-" * 40)
    print(f"  {'合计':<15}: {total_invoices:>5} 张, 金额: {total_amount:>12.2f}, 已付: {total_paid:>12.2f}")
    print(f"  未收款总额: {total_amount - total_paid:>12.2f}")
    print()

    return updated_count


def main():
    """主函数"""
    # 检查参数
    execute = '--execute' in sys.argv or '-e' in sys.argv

    # 创建应用上下文
    app = create_app()
    with app.app_context():
        try:
            sync_invoice_payment_status(execute=execute)
        except Exception as e:
            db.session.rollback()
            print(f"\n错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
