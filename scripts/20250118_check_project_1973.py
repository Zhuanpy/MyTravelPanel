"""
检查项目 1973 的收款分配详情
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    from App_new.business.projects.models.header import ProjectHeader
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
    from App_new.business.projects.models.invoice import ProjectInvoice

    header_id = 1973

    print("=" * 80)
    print(f"项目 {header_id} 收款分配详情")
    print("=" * 80)

    # 1. 项目基本信息
    header = ProjectHeader.query.get(header_id)
    if header:
        print(f"\n1. 项目信息: {header.project_no}")

    # 2. REF 信息
    print(f"\n2. REF 列表:")
    refs = ProjectRef.query.filter_by(header_id=header_id).all()
    for ref in refs:
        print(f"   - REF {ref.id}: {ref.ref_number}, 售价: {ref.selling_price}, 状态: {ref.payment_status}")

    # 3. 发票信息
    print(f"\n3. 发票列表:")
    invoices = ProjectInvoice.query.filter_by(header_id=header_id).all()
    for inv in invoices:
        print(f"   - Invoice {inv.id}: {inv.invoice_number}")
        print(f"     金额: {inv.amount}, 已付: {inv.paid_amount}")
        print(f"     状态: {inv.status}, 付款状态: {inv.payment_status}")
        print(f"     ref_ids: {inv.ref_ids}")

    # 4. 直接关联到 REF 的收款
    print(f"\n4. 直接关联到 REF 的收款:")
    for ref in refs:
        receipts = ProjectReceipt.query.filter_by(ref_id=ref.id).all()
        if receipts:
            for r in receipts:
                print(f"   - Receipt {r.id}: {r.receipt_no}, 金额: {r.amount}, 状态: {r.status}, ref_id: {r.ref_id}")
        else:
            print(f"   - REF {ref.id} ({ref.ref_number}): 无直接关联收款")

    # 5. 项目下所有收款
    print(f"\n5. 项目下所有收款 (project_id={header_id}):")
    all_receipts = ProjectReceipt.query.filter_by(project_id=header_id).all()
    if all_receipts:
        for r in all_receipts:
            print(f"   - Receipt {r.id}: {r.receipt_no}, 金额: {r.amount}, 状态: {r.status}")
            print(f"     ref_id: {r.ref_id}, invoice_id: {r.invoice_id}")
    else:
        print("   无收款记录")

    # 6. 发票分配记录
    print(f"\n6. 发票分配记录 (ReceiptInvoiceAllocation):")
    for inv in invoices:
        allocations = ReceiptInvoiceAllocation.query.filter_by(invoice_id=inv.id).all()
        if allocations:
            for alloc in allocations:
                receipt = ProjectReceipt.query.get(alloc.receipt_id)
                receipt_info = f"{receipt.receipt_no}, 状态: {receipt.status}" if receipt else "收款不存在"
                print(f"   - Invoice {inv.id} -> Receipt {alloc.receipt_id} ({receipt_info}), 分配金额: {alloc.allocated_amount}")
        else:
            print(f"   - Invoice {inv.id} ({inv.invoice_number}): 无分配记录")

    print("\n" + "=" * 80)
