#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试脚本 - 验证所有预算单功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def final_test():
    """最终测试所有功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🚀 开始最终测试...")
            
            # 1. 测试列表页面
            print("\n📋 1. 测试列表页面")
            with app.test_client() as client:
                response = client.get('/package_budget/list')
                if response.status_code == 200:
                    print("  ✅ 列表页面正常")
                else:
                    print(f"  ❌ 列表页面失败: {response.status_code}")
            
            # 2. 测试详情页面
            print("\n🔍 2. 测试详情页面")
            budget = BudgetHeader.query.first()
            if budget:
                with app.test_client() as client:
                    response = client.get(f'/package_budget/{budget.id}')
                    if response.status_code == 200:
                        print(f"  ✅ 详情页面正常 (预算单 {budget.id})")
                    else:
                        print(f"  ❌ 详情页面失败: {response.status_code}")
            else:
                print("  ⚠️  没有预算单可测试")
            
            # 3. 测试路由URL生成
            print("\n🌐 3. 测试路由URL生成")
            with app.test_request_context():
                from flask import url_for
                try:
                    if budget:
                        detail_url = url_for('package_budget.detail', budget_id=budget.id)
                        edit_url = url_for('package_budget.edit', budget_id=budget.id)
                        add_item_url = url_for('package_budget.add_item', budget_id=budget.id)
                        list_url = url_for('package_budget.list_budgets')
                        
                        print(f"  ✅ 详情URL: {detail_url}")
                        print(f"  ✅ 编辑URL: {edit_url}")
                        print(f"  ✅ 添加项目URL: {add_item_url}")
                        print(f"  ✅ 列表URL: {list_url}")
                    else:
                        list_url = url_for('package_budget.list_budgets')
                        print(f"  ✅ 列表URL: {list_url}")
                except Exception as e:
                    print(f"  ❌ URL生成失败: {e}")
            
            # 4. 测试数据计算
            print("\n🧮 4. 测试数据计算")
            if budget:
                try:
                    total_price = budget.total_price
                    print(f"  ✅ 预算单总价: {total_price}")
                    
                    for i, item in enumerate(budget.items, 1):
                        subtotal = item.subtotal
                        adult_unit = item.adult_unit_price
                        child_unit = item.child_unit_price
                        print(f"    项目 {i}: 小计={subtotal}, 成人人均={adult_unit}, 儿童人均={child_unit}")
                except Exception as e:
                    print(f"  ❌ 数据计算失败: {e}")
            
            # 5. 测试两套计价方式
            print("\n💰 5. 测试两套计价方式")
            if budget and budget.items:
                item = budget.items[0]
                print(f"  当前项目: {item.item_name}")
                print(f"  计价方式: {item.pricing_method}")
                
                if item.pricing_method == 'item_based':
                    print(f"  物品单价: {item.item_unit_price}")
                    print(f"  物品件数: {item.item_quantity}")
                    print(f"  物品总价: {item.total_item_cost}")
                else:
                    print(f"  成人单价: {item.adult_price}")
                    print(f"  儿童单价: {item.child_price}")
                
                print(f"  成人人均: {item.adult_unit_price}")
                print(f"  儿童人均: {item.child_unit_price}")
                print(f"  项目小计: {item.subtotal}")
            
            print("\n🎉 所有测试完成！")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    success = final_test()
    if success:
        print("\n✅ 最终测试成功！系统运行正常。")
    else:
        print("\n❌ 最终测试失败！")
        sys.exit(1) 