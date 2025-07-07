#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试详情页面错误
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def debug_detail_error():
    """调试详情页面错误"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== 调试详情页面错误 ===")
            
            # 1. 检查预算单是否存在
            print("1. 检查预算单...")
            budget = BudgetHeader.query.get(2)
            if budget:
                print(f"   ✓ 找到预算单: {budget.package_name}")
                print(f"   成人数量: {budget.adult_count}")
                print(f"   儿童数量: {budget.child_count}")
                print(f"   项目数量: {len(budget.items)}")
            else:
                print("   ✗ 预算单不存在")
                return
            
            # 2. 检查项目数据
            print("2. 检查项目数据...")
            for i, item in enumerate(budget.items, 1):
                print(f"   项目{i}: {item.item_name}")
                print(f"     类别: {item.category}")
                print(f"     计价方式: {item.pricing_method}")
                print(f"     成人单价: {item.adult_price}")
                print(f"     儿童单价: {item.child_price}")
                print(f"     物品单价: {item.item_unit_price}")
                print(f"     物品件数: {item.item_quantity}")
                print(f"     小计: {item.subtotal}")
                print(f"     成人人均: {item.adult_unit_price}")
                print(f"     儿童人均: {item.child_unit_price}")
                print()
            
            # 3. 测试计算逻辑
            print("3. 测试计算逻辑...")
            category_totals = {}
            adult_total = 0
            child_total = 0
            
            for item in budget.items:
                # 分类统计
                category = item.category or '未分类'
                if category not in category_totals:
                    category_totals[category] = 0
                category_totals[category] += item.subtotal or 0
                
                # 计算成人费用
                if item.count_adult_apply:
                    adult_count = item.adult_count_override or budget.adult_count
                    adult_unit_price = item.adult_unit_price or 0
                    adult_total += adult_unit_price * adult_count
                
                # 计算儿童费用
                if item.count_child_apply:
                    child_count = item.child_count_override or budget.child_count
                    child_unit_price = item.child_unit_price or 0
                    child_total += child_unit_price * child_count
            
            print(f"   分类统计: {category_totals}")
            print(f"   成人总费用: {adult_total}")
            print(f"   儿童总费用: {child_total}")
            print(f"   总费用: {adult_total + child_total}")
            
            print("\n✅ 调试完成！")
            
        except Exception as e:
            print(f"❌ 调试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_detail_error() 