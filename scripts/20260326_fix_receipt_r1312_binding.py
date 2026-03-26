"""
修复脚本：将收款 R1312 绑定到发票 11065

问题：项目 2189 的收款 R1312 没有绑定到发票 11065（已付款），
      发票 11083 已作废。需要创建 ReceiptInvoiceAllocation 记录。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.core.exts import db
from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
from App_new.business.projects.models.invoice import ProjectInvoice

app = create_app()

with app.app_context():
    # 1. 查找收款 R1312
    receipt = ProjectReceipt.query.filter_by(receipt_number='R1312').first()
    if not receipt:
        print("错误：找不到收款 R1312")
        sys.exit(1)

    print(f"收款 R1312: id={receipt.id}, amount={receipt.amount}, "
          f"header_id={receipt.header_id}, status={receipt.status}")

    # 2. 查找发票 11065
    invoice = ProjectInvoice.query.filter_by(id=11065).first()
    if not invoice:
        print("错误：找不到发票 11065")
        sys.exit(1)

    print(f"发票 11065: invoice_number={invoice.invoice_number}, amount={invoice.amount}, "
          f"paid_amount={invoice.paid_amount}, payment_status={invoice.payment_status}, "
          f"status={invoice.status}")

    # 3. 检查是否已存在分配记录
    existing = ReceiptInvoiceAllocation.query.filter_by(
        receipt_id=receipt.id, invoice_id=invoice.id
    ).first()

    if existing:
        print(f"分配记录已存在: id={existing.id}, allocated_amount={existing.allocated_amount}")
        print("无需修复。")
        sys.exit(0)

    # 4. 检查收款的现有分配
    existing_allocations = ReceiptInvoiceAllocation.query.filter_by(receipt_id=receipt.id).all()
    if existing_allocations:
        print(f"收款 R1312 已有 {len(existing_allocations)} 条分配记录:")
        for a in existing_allocations:
            print(f"  -> invoice_id={a.invoice_id}, allocated_amount={a.allocated_amount}")

    # 5. 创建分配记录
    allocated_amount = float(receipt.amount)
    print(f"\n将创建分配记录: receipt_id={receipt.id} -> invoice_id={invoice.id}, "
          f"allocated_amount={allocated_amount}")

    confirm = input("确认执行？(y/n): ")
    if confirm.lower() != 'y':
        print("已取消。")
        sys.exit(0)

    allocation = ReceiptInvoiceAllocation(
        receipt_id=receipt.id,
        invoice_id=invoice.id,
        allocated_amount=allocated_amount
    )
    db.session.add(allocation)
    db.session.flush()

    # 6. 更新发票已付金额和状态
    ProjectReceipt.update_invoice_paid_amount(invoice.id)

    db.session.commit()
    print("修复完成！")

    # 7. 验证结果
    invoice = ProjectInvoice.query.get(invoice.id)
    print(f"发票 11065 更新后: paid_amount={invoice.paid_amount}, "
          f"payment_status={invoice.payment_status}")
