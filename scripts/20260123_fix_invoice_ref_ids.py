"""修复发票缺失的ref_ids字段

问题：部分发票创建时未选择REF，导致ref_ids为NULL，
     收款分配时无法正确追溯到REF，造成项目balance不归零。

修复策略：
- 对ref_ids为NULL的发票，自动关联项目下所有有selling_price的REF
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.invoice import ProjectInvoice
from App_new.business.projects.models.project import ProjectHeader

app = create_app()

with app.app_context():
    # 查找所有ref_ids为空的已确认发票
    invoices = ProjectInvoice.query.filter(
        ProjectInvoice.ref_ids.is_(None),
        ProjectInvoice.status != 'cancelled'
    ).all()

    print(f"找到 {len(invoices)} 张缺失ref_ids的发票")

    fixed_count = 0
    skipped_count = 0

    for invoice in invoices:
        header = ProjectHeader.query.get(invoice.header_id)
        if not header:
            print(f"  [跳过] 发票 {invoice.invoice_number}: 找不到项目 header_id={invoice.header_id}")
            skipped_count += 1
            continue

        # 获取项目下所有有selling_price的REF
        refs_with_price = [ref for ref in header.refs if ref.selling_price]
        if not refs_with_price:
            print(f"  [跳过] 发票 {invoice.invoice_number}: 项目 {header.hid} 无有效REF")
            skipped_count += 1
            continue

        ref_ids = [ref.id for ref in refs_with_price]
        invoice.ref_ids = json.dumps(ref_ids)
        fixed_count += 1
        print(f"  [修复] 发票 {invoice.invoice_number} (项目 {header.hid}): ref_ids={ref_ids}")

    if fixed_count > 0:
        db.session.flush()

        # 重新计算受影响项目的REF付款状态
        from App_new.business.projects.models.receipt import ProjectReceipt
        affected_header_ids = set(inv.header_id for inv in invoices if inv.ref_ids)
        print(f"\n重新计算 {len(affected_header_ids)} 个项目的REF付款状态...")

        for header_id in affected_header_ids:
            header = ProjectHeader.query.get(header_id)
            if not header:
                continue
            for ref in header.refs:
                if ref.selling_price:
                    total_received = ProjectReceipt.get_ref_total_received(ref.id, header.id)
                    if total_received >= float(ref.selling_price):
                        ref.payment_status = 'paid'
                    elif total_received > 0:
                        ref.payment_status = 'partial'
                    else:
                        ref.payment_status = 'unpaid'

        db.session.commit()
        print(f"完成：修复 {fixed_count} 张发票，跳过 {skipped_count} 张")
    else:
        print("无需修复")
