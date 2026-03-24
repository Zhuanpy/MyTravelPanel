"""
修复金额为0的发票付款状态
金额为0的发票不需要付款，应标记为paid
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.invoice import ProjectInvoice

app = create_app()

with app.app_context():
    # 查找金额为0但状态不是paid的发票
    invoices = ProjectInvoice.query.filter(
        ProjectInvoice.amount == 0,
        ProjectInvoice.payment_status != 'paid',
        ProjectInvoice.status != 'cancelled'
    ).all()

    print(f"找到 {len(invoices)} 条金额为0但未标记paid的发票")

    for inv in invoices:
        print(f"  修复: #{inv.id} {inv.invoice_number} amount={inv.amount} {inv.payment_status} -> paid")
        inv.payment_status = 'paid'

    if invoices:
        db.session.commit()
        print(f"已修复 {len(invoices)} 条记录")
    else:
        print("无需修复")
