#!/usr/bin/env python3
"""
测试收款分配逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app, db
from App.models.projects.BookingProject import ProjectHeader, ProjectRef, ProjectReceipt

def test_receipt_distribution():
    """测试收款分配逻辑"""
    app = create_app()
    
    with app.app_context():
        # 查找项目H87
        header = ProjectHeader.query.filter_by(hid='H87').first()
        if not header:
            print("项目H87不存在")
            return
        
        print(f"项目: {header.hid}")
        print(f"总销售金额: {header.total_selling_amount}")
        print(f"总未收款金额: {header.total_unpaid_amount}")
        
        # 显示所有REF的详细信息
        print("\nREF详细信息:")
        for ref in header.refs:
            print(f"\n  REF: {ref.ref_number}")
            print(f"    售价: {ref.selling_price}")
            print(f"    付款状态: {ref.payment_status}")
            
            # 显示该REF的所有收款记录
            receipts = ProjectReceipt.query.filter_by(ref_id=ref.id, status='confirmed').all()
            if receipts:
                print(f"    收款记录:")
                total_received = 0
                for receipt in receipts:
                    print(f"      {receipt.receipt_number}: {receipt.amount}")
                    total_received += float(receipt.amount)
                print(f"    总收款: {total_received}")
                if ref.selling_price:
                    unpaid = float(ref.selling_price) - total_received
                    print(f"    未收款: {unpaid}")
            else:
                print(f"    无收款记录")
                if ref.selling_price:
                    print(f"    未收款: {ref.selling_price}")
        
        # 测试分配逻辑
        test_amount = 38.19  # 使用实际的未收款金额
        print(f"\n测试分配金额: {test_amount}")
        
        # 调用分配方法
        distribution_result = ProjectReceipt.distribute_project_receipt(header.id, test_amount, 'auto')
        
        if distribution_result['success']:
            print("分配结果:")
            for dist in distribution_result['distribution']:
                ref = ProjectRef.query.get(dist['ref_id'])
                print(f"  {ref.ref_number}: 分配金额={dist['amount']}")
            print(f"剩余金额: {distribution_result['remaining_amount']}")
        else:
            print(f"分配失败: {distribution_result['message']}")

if __name__ == '__main__':
    test_receipt_distribution() 