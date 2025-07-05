#!/usr/bin/env python3
"""
测试REF利润计算功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import ProjectHeader, ProjectRef
from App.exts import db

def test_profit_calculation():
    """测试利润计算功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试REF利润计算功能 ===\n")
        
        # 获取所有REF
        refs = ProjectRef.query.all()
        
        if not refs:
            print("❌ 没有找到任何REF")
            return
        
        print(f"找到 {len(refs)} 个REF\n")
        
        for ref in refs:
            print(f"REF: {ref.ref_number}")
            print(f"名称: {ref.name or ref.description}")
            print(f"类型: {ref.ref_type.name if ref.ref_type else '未分类'}")
            print(f"售价: {ref.currency} {ref.selling_price or 0:.2f}")
            print(f"成本: {ref.currency} {ref.cost_price or 0:.2f}")
            
            # 计算利润
            profit = ref.ref_profit
            profit_margin = ref.ref_profit_margin
            
            print(f"利润: {ref.currency} {profit:.2f}")
            print(f"利润率: {profit_margin:.1f}%")
            
            # 显示利润状态
            if profit > 0:
                print("✅ 盈利")
            elif profit < 0:
                print("❌ 亏损")
            else:
                print("➖ 持平")
            
            print("-" * 50)

def test_project_total_profit():
    """测试项目总利润计算"""
    app = create_app()
    
    with app.app_context():
        print("\n=== 测试项目总利润计算 ===\n")
        
        # 获取所有项目
        headers = ProjectHeader.query.all()
        
        if not headers:
            print("❌ 没有找到任何项目")
            return
        
        for header in headers:
            print(f"项目: {header.hid}")
            print(f"描述: {header.desc}")
            print(f"总销售金额: {header.currency or 'SGD'} {header.total_selling_amount:.2f}")
            print(f"总成本金额: {header.currency or 'SGD'} {header.total_cost_amount:.2f}")
            print(f"总利润: {header.currency or 'SGD'} {header.total_profit:.2f}")
            
            if header.total_profit > 0:
                print("✅ 项目盈利")
            elif header.total_profit < 0:
                print("❌ 项目亏损")
            else:
                print("➖ 项目持平")
            
            print("-" * 50)

if __name__ == "__main__":
    test_profit_calculation()
    test_project_total_profit()
    print("\n🎉 利润计算测试完成！") 