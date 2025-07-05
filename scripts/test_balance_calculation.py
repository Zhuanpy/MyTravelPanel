#!/usr/bin/env python3
"""
测试项目余额计算功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import ProjectHeader, ProjectRef
from App.models.Accountsmodels import CustomerCompany
from App.exts import db

def test_balance_calculation():
    """测试余额计算功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试项目余额计算功能 ===\n")
        
        # 获取所有项目
        headers = ProjectHeader.query.all()
        
        if not headers:
            print("❌ 没有找到任何项目")
            return
        
        print(f"找到 {len(headers)} 个项目\n")
        
        for header in headers:
            print(f"项目: {header.hid}")
            print(f"描述: {header.desc}")
            print(f"公司: {header.company.name if header.company else '无'}")
            print(f"REF数量: {len(header.refs)}")
            
            # 计算各项金额
            total_selling = header.total_selling_amount
            total_cost = header.total_cost_amount
            total_profit = header.total_profit
            total_paid = header.total_paid_amount
            total_unpaid = header.total_unpaid_amount
            payment_summary = header.payment_status_summary
            
            print(f"总销售金额: {header.currency or 'SGD'} {total_selling:.2f}")
            print(f"总成本金额: {header.currency or 'SGD'} {total_cost:.2f}")
            print(f"总利润: {header.currency or 'SGD'} {total_profit:.2f}")
            print(f"已付款金额: {header.currency or 'SGD'} {total_paid:.2f}")
            print(f"未付款金额: {header.currency or 'SGD'} {total_unpaid:.2f}")
            
            if total_selling > 0:
                payment_percentage = (total_paid / total_selling) * 100
                print(f"付款进度: {payment_percentage:.1f}%")
            
            print(f"付款状态: 已付款({payment_summary['paid']}) 部分付款({payment_summary['partial']}) 未付款({payment_summary['unpaid']})")
            
            # 显示REF详情
            if header.refs:
                print("\nREF详情:")
                for ref in header.refs:
                    payment_status_text = {
                        'paid': '已付款',
                        'partial': '部分付款', 
                        'unpaid': '未付款'
                    }.get(ref.payment_status, '未知')
                    
                    print(f"  - {ref.ref_number}: {ref.name or ref.description}")
                    print(f"    售价: {ref.currency} {ref.selling_price or 0:.2f}")
                    print(f"    成本: {ref.currency} {ref.cost_price or 0:.2f}")
                    print(f"    付款状态: {payment_status_text}")
            
            print("\n" + "="*50 + "\n")

def test_specific_project(project_hid):
    """测试特定项目的余额计算"""
    app = create_app()
    
    with app.app_context():
        header = ProjectHeader.query.filter_by(hid=project_hid).first()
        
        if not header:
            print(f"❌ 未找到项目: {project_hid}")
            return
        
        print(f"=== 项目 {project_hid} 余额详情 ===\n")
        
        print(f"项目信息:")
        print(f"  HID: {header.hid}")
        print(f"  描述: {header.desc}")
        print(f"  公司: {header.company.name if header.company else '无'}")
        print(f"  创建时间: {header.created_at}")
        
        print(f"\n财务概览:")
        print(f"  总销售金额: {header.currency or 'SGD'} {header.total_selling_amount:.2f}")
        print(f"  总成本金额: {header.currency or 'SGD'} {header.total_cost_amount:.2f}")
        print(f"  总利润: {header.currency or 'SGD'} {header.total_profit:.2f}")
        print(f"  已付款金额: {header.currency or 'SGD'} {header.total_paid_amount:.2f}")
        print(f"  未付款金额: {header.currency or 'SGD'} {header.total_unpaid_amount:.2f}")
        
        if header.total_selling_amount > 0:
            payment_percentage = (header.total_paid_amount / header.total_selling_amount) * 100
            print(f"  付款进度: {payment_percentage:.1f}%")
        
        payment_summary = header.payment_status_summary
        print(f"\n付款状态统计:")
        print(f"  已付款: {payment_summary['paid']} 个REF")
        print(f"  部分付款: {payment_summary['partial']} 个REF")
        print(f"  未付款: {payment_summary['unpaid']} 个REF")
        print(f"  总计: {payment_summary['total']} 个REF")
        
        if header.refs:
            print(f"\nREF明细:")
            for ref in header.refs:
                print(f"\n  REF: {ref.ref_number}")
                print(f"    名称: {ref.name or ref.description}")
                print(f"    类型: {ref.ref_type.name if ref.ref_type else '未分类'}")
                print(f"    供应商: {ref.supplier.name if ref.supplier else '无'}")
                print(f"    售价: {ref.currency} {ref.selling_price or 0:.2f}")
                print(f"    成本: {ref.currency} {ref.cost_price or 0:.2f}")
                print(f"    付款状态: {ref.payment_status}")
                print(f"    状态: {ref.status}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 测试特定项目
        project_hid = sys.argv[1]
        test_specific_project(project_hid)
    else:
        # 测试所有项目
        test_balance_calculation() 