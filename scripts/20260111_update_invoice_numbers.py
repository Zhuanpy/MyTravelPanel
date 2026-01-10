# -*- coding: utf-8 -*-
"""
更新现有发票编号，从10000开始递增
按创建时间排序，保持原有顺序
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.invoice import ProjectInvoice

app = create_app()

with app.app_context():
    # 获取所有发票，按ID排序（保持创建顺序）
    invoices = ProjectInvoice.query.order_by(ProjectInvoice.id.asc()).all()

    if not invoices:
        print('没有找到任何发票记录')
    else:
        print(f'找到 {len(invoices)} 条发票记录')
        print('-' * 50)

        # 从10000开始分配新编号
        new_number = 10000

        for invoice in invoices:
            old_number = invoice.invoice_number
            invoice.invoice_number = str(new_number)
            print(f'ID {invoice.id}: {old_number} -> {new_number}')
            new_number += 1

        # 提交更改
        db.session.commit()
        print('-' * 50)
        print(f'成功更新 {len(invoices)} 条发票编号')
        print(f'编号范围: 10000 - {new_number - 1}')
