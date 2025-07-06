#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试预算单详情路由问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def debug_detail_route():
    """调试详情路由"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查找现有的预算单
            budgets = BudgetHeader.query.all()
            print(f"📋 找到 {len(budgets)} 个预算单")
            
            for budget in budgets:
                print(f"\n🔍 检查预算单 ID: {budget.id}")
                print(f"  套餐名称: {budget.package_name}")
                print(f"  成人数量: {budget.adult_count}")
                print(f"  儿童数量: {budget.child_count}")
                print(f"  项目数量: {len(budget.items)}")
                
                # 检查每个项目
                for i, item in enumerate(budget.items, 1):
                    print(f"    项目 {i}: {item.item_name}")
                    print(f"      计价方式: {item.pricing_method}")
                    print(f"      物品单价: {item.item_unit_price}")
                    print(f"      物品件数: {item.item_quantity}")
                    print(f"      成人单价: {item.adult_price}")
                    print(f"      儿童单价: {item.child_price}")
                    print(f"      计成人: {item.count_adult_apply}")
                    print(f"      计儿童: {item.count_child_apply}")
                    
                    # 测试属性计算
                    try:
                        subtotal = item.subtotal
                        adult_unit = item.adult_unit_price
                        child_unit = item.child_unit_price
                        total_item_cost = item.total_item_cost
                        
                        print(f"      小计: {subtotal}")
                        print(f"      成人人均: {adult_unit}")
                        print(f"      儿童人均: {child_unit}")
                        print(f"      物品总价: {total_item_cost}")
                    except Exception as e:
                        print(f"      ❌ 计算错误: {e}")
                
                # 测试详情页面计算
                try:
                    category_totals = {}
                    adult_total = 0
                    child_total = 0
                    tax_total = 0
                    
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
                        
                        # 计算税费
                        if item.tax_rate:
                            tax_total += (item.subtotal or 0) * item.tax_rate
                        if item.tax_amount:
                            tax_total += float(item.tax_amount or 0)
                    
                    print(f"  ✅ 计算成功:")
                    print(f"    成人总费用: {adult_total}")
                    print(f"    儿童总费用: {child_total}")
                    print(f"    税费总额: {tax_total}")
                    print(f"    分类统计: {category_totals}")
                    
                except Exception as e:
                    print(f"  ❌ 详情页面计算错误: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 测试路由URL生成
            print(f"\n🌐 测试路由URL生成...")
            with app.test_request_context():
                from flask import url_for
                
                for budget in budgets[:3]:  # 只测试前3个
                    try:
                        detail_url = url_for('package_budget.detail', budget_id=budget.id)
                        print(f"  预算单 {budget.id} 详情URL: {detail_url}")
                    except Exception as e:
                        print(f"  ❌ URL生成错误: {e}")
            
        except Exception as e:
            print(f"❌ 调试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    print("🚀 开始调试详情路由...")
    success = debug_detail_route()
    if success:
        print("\n🎉 调试完成！")
    else:
        print("\n💥 调试失败！")
        sys.exit(1) 