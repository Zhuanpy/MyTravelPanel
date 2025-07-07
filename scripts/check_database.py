#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库连接和模型
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def check_database():
    """检查数据库连接和模型"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== 检查数据库连接和模型 ===")
            
            # 1. 检查数据库连接
            print("1. 检查数据库连接...")
            try:
                db.session.execute("SELECT 1")
                print("   ✓ 数据库连接正常")
            except Exception as e:
                print(f"   ✗ 数据库连接失败: {e}")
                return
            
            # 2. 检查预算单表
            print("2. 检查预算单表...")
            try:
                budgets = BudgetHeader.query.all()
                print(f"   ✓ 找到 {len(budgets)} 个预算单")
                for budget in budgets:
                    print(f"     ID: {budget.id}, 名称: {budget.package_name}")
            except Exception as e:
                print(f"   ✗ 查询预算单失败: {e}")
                return
            
            # 3. 检查预算项目表
            print("3. 检查预算项目表...")
            try:
                items = BudgetItem.query.all()
                print(f"   ✓ 找到 {len(items)} 个项目")
                for item in items:
                    print(f"     ID: {item.id}, 名称: {item.item_name}, 预算单ID: {item.header_id}")
            except Exception as e:
                print(f"   ✗ 查询预算项目失败: {e}")
                return
            
            # 4. 检查特定预算单
            print("4. 检查特定预算单...")
            try:
                budget = BudgetHeader.query.get(2)
                if budget:
                    print(f"   ✓ 找到预算单 ID=2: {budget.package_name}")
                    print(f"     成人数量: {budget.adult_count}")
                    print(f"     儿童数量: {budget.child_count}")
                    print(f"     项目数量: {len(budget.items)}")
                    
                    # 检查项目
                    for item in budget.items:
                        print(f"       项目: {item.item_name}")
                        print(f"         类别: {item.category}")
                        print(f"         计价方式: {item.pricing_method}")
                        print(f"         成人单价: {item.adult_price}")
                        print(f"         儿童单价: {item.child_price}")
                        print(f"         物品单价: {item.item_unit_price}")
                        print(f"         物品件数: {item.item_quantity}")
                        print(f"         项目详细: {item.item_details}")
                else:
                    print("   ✗ 预算单 ID=2 不存在")
            except Exception as e:
                print(f"   ✗ 查询特定预算单失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n✅ 数据库检查完成！")
            
        except Exception as e:
            print(f"❌ 检查过程中出现错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_database() 