#!/usr/bin/env python3
"""
清理项目H87下所有REF的收款记录
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app, db
from App.models.projects.BookingProject import ProjectHeader, ProjectReceipt, ProjectRef

def clear_h87_receipts():
    app = create_app()
    with app.app_context():
        header = ProjectHeader.query.filter_by(hid='H87').first()
        if not header:
            print('项目H87不存在')
            return
        print(f'找到项目: {header.hid}')
        count = 0
        for ref in header.refs:
            receipts = ProjectReceipt.query.filter_by(ref_id=ref.id).all()
            for receipt in receipts:
                db.session.delete(receipt)
                count += 1
        db.session.commit()
        print(f'已删除{count}条收款记录')
        # 重置REF的付款状态
        for ref in header.refs:
            ref.payment_status = 'unpaid'
        db.session.commit()
        print('已重置所有REF的付款状态为unpaid')

if __name__ == '__main__':
    print('开始清理H87收款记录...')
    clear_h87_receipts() 