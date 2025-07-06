#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试预算单路由是否正常工作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def test_routes():
    """测试路由功能"""
    app = create_app()
    
    with app.app_context():
        try:
            # 创建测试预算单
            print("📋 创建测试预算单...")
            budget = BudgetHeader(
                package_name="路由测试预算单",
                adult_count=2,
                child_count=1,
                currency="SGD",
                status="draft",
                created_by="测试用户"
            )
            db.session.add(budget)
            db.session.commit()
            print(f"✓ 预算单创建成功，ID: {budget.id}")
            
            # 测试添加项目
            print("\n🔧 测试添加项目...")
            item = BudgetItem(
                header_id=budget.id,
                category="测试",
                item_type="测试类型",
                item_name="测试项目",
                pricing_method="person_based",
                adult_price=100.00,
                child_price=80.00,
                count_adult_apply=True,
                count_child_apply=True,
                sort_order=1
            )
            db.session.add(item)
            db.session.commit()
            print(f"✓ 项目添加成功，ID: {item.id}")
            
            # 测试路由URL生成
            print("\n🌐 测试路由URL生成...")
            with app.test_request_context():
                from flask import url_for
                
                # 测试详情页面路由
                detail_url = url_for('package_budget.detail', budget_id=budget.id)
                print(f"  详情页面URL: {detail_url}")
                
                # 测试添加项目路由
                add_item_url = url_for('package_budget.add_item', budget_id=budget.id)
                print(f"  添加项目URL: {add_item_url}")
                
                # 测试编辑项目路由
                edit_item_url = url_for('package_budget.edit_item', budget_id=budget.id, item_id=item.id)
                print(f"  编辑项目URL: {edit_item_url}")
                
                # 测试删除项目路由
                delete_item_url = url_for('package_budget.delete_item', budget_id=budget.id, item_id=item.id)
                print(f"  删除项目URL: {delete_item_url}")
                
                # 测试编辑预算单路由
                edit_budget_url = url_for('package_budget.edit', budget_id=budget.id)
                print(f"  编辑预算单URL: {edit_budget_url}")
                
                # 测试列表页面路由
                list_url = url_for('package_budget.list_budgets')
                print(f"  列表页面URL: {list_url}")
            
            print("\n✅ 路由测试完成！")
            
            # 清理测试数据
            print("\n🧹 清理测试数据...")
            db.session.delete(budget)
            db.session.commit()
            print("✓ 测试数据已清理")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    print("🚀 开始测试路由功能...")
    success = test_routes()
    if success:
        print("\n🎉 测试成功！")
    else:
        print("\n💥 测试失败！")
        sys.exit(1) 