#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试两套计价方式功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def test_pricing_methods():
    """测试两套计价方式"""
    app = create_app()
    
    with app.app_context():
        try:
            # 创建测试预算单
            print("📋 创建测试预算单...")
            budget = BudgetHeader(
                package_name="测试配套",
                adult_count=2,
                child_count=1,
                currency="SGD",
                status="draft",
                created_by="测试用户"
            )
            db.session.add(budget)
            db.session.commit()
            print(f"✓ 预算单创建成功，ID: {budget.id}")
            
            # 测试模板1：物品计价方式
            print("\n🔧 测试模板1：物品计价方式")
            item1 = BudgetItem(
                header_id=budget.id,
                category="住宿",
                item_type="酒店",
                item_name="豪华酒店房间",
                pricing_method="item_based",
                item_unit_price=200.00,  # 房间单价
                item_quantity=1,         # 1间房
                count_adult_apply=True,
                count_child_apply=True,
                sort_order=1
            )
            db.session.add(item1)
            db.session.commit()
            
            print(f"  物品单价: ${item1.item_unit_price}")
            print(f"  物品件数: {item1.item_quantity}")
            print(f"  物品总价: ${item1.total_item_cost}")
            print(f"  成人人均: ${item1.adult_unit_price}")
            print(f"  儿童人均: ${item1.child_unit_price}")
            print(f"  项目小计: ${item1.subtotal}")
            
            # 测试模板2：人均计价方式
            print("\n👥 测试模板2：人均计价方式")
            item2 = BudgetItem(
                header_id=budget.id,
                category="交通",
                item_type="机票",
                item_name="往返机票",
                pricing_method="person_based",
                adult_price=150.00,  # 成人单价
                child_price=120.00,  # 儿童单价
                count_adult_apply=True,
                count_child_apply=True,
                sort_order=2
            )
            db.session.add(item2)
            db.session.commit()
            
            print(f"  成人单价: ${item2.adult_price}")
            print(f"  儿童单价: ${item2.child_price}")
            print(f"  成人人均: ${item2.adult_unit_price}")
            print(f"  儿童人均: ${item2.child_unit_price}")
            print(f"  项目小计: ${item2.subtotal}")
            
            # 测试混合计价方式
            print("\n🔄 测试混合计价方式")
            item3 = BudgetItem(
                header_id=budget.id,
                category="餐饮",
                item_type="餐厅",
                item_name="特色餐厅",
                pricing_method="item_based",
                item_unit_price=80.00,   # 餐费单价
                item_quantity=3,         # 3餐
                count_adult_apply=True,
                count_child_apply=False,  # 儿童不计算
                sort_order=3
            )
            db.session.add(item3)
            db.session.commit()
            
            print(f"  物品单价: ${item3.item_unit_price}")
            print(f"  物品件数: {item3.item_quantity}")
            print(f"  物品总价: ${item3.total_item_cost}")
            print(f"  成人人均: ${item3.adult_unit_price}")
            print(f"  儿童人均: ${item3.child_unit_price}")
            print(f"  项目小计: ${item3.subtotal}")
            
            # 计算预算单总价
            print("\n💰 预算单汇总")
            total_price = sum(item.subtotal for item in budget.items)
            adult_total = sum(item.adult_unit_price * budget.adult_count for item in budget.items if item.count_adult_apply)
            child_total = sum(item.child_unit_price * budget.child_count for item in budget.items if item.count_child_apply)
            
            print(f"  总价: ${total_price}")
            print(f"  成人总费用: ${adult_total}")
            print(f"  儿童总费用: ${child_total}")
            
            # 显示所有项目
            print("\n📊 所有项目列表:")
            for i, item in enumerate(budget.items, 1):
                print(f"  {i}. {item.item_name} ({item.pricing_method})")
                print(f"     计价方式: {'物品计价' if item.pricing_method == 'item_based' else '人均计价'}")
                if item.pricing_method == 'item_based':
                    print(f"     物品单价: ${item.item_unit_price}, 件数: {item.item_quantity}")
                    print(f"     物品总价: ${item.total_item_cost}")
                else:
                    print(f"     成人单价: ${item.adult_price}, 儿童单价: ${item.child_price}")
                print(f"     项目小计: ${item.subtotal}")
                print()
            
            print("✅ 测试完成！")
            
            # 清理测试数据
            print("\n🧹 清理测试数据...")
            db.session.delete(budget)
            db.session.commit()
            print("✓ 测试数据已清理")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 测试失败: {e}")
            return False
        
        return True

if __name__ == "__main__":
    print("🚀 开始测试两套计价方式功能...")
    success = test_pricing_methods()
    if success:
        print("\n🎉 测试成功！")
    else:
        print("\n💥 测试失败！")
        sys.exit(1) 