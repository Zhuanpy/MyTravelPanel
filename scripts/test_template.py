#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模板渲染
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def test_template():
    """测试模板渲染"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== 测试模板渲染 ===")
            
            # 1. 检查模板文件是否存在
            print("1. 检查模板文件...")
            template_path = "App/templates/package/budget/detail.html"
            if os.path.exists(template_path):
                print(f"   ✓ 模板文件存在: {template_path}")
            else:
                print(f"   ✗ 模板文件不存在: {template_path}")
                return
            
            # 2. 获取测试数据
            print("2. 获取测试数据...")
            budget = BudgetHeader.query.get(2)
            if not budget:
                print("   ✗ 预算单不存在")
                return
            
            print(f"   ✓ 找到预算单: {budget.package_name}")
            
            # 3. 计算数据
            print("3. 计算数据...")
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
            
            print(f"   ✓ 计算完成: 成人={adult_total}, 儿童={child_total}")
            
            # 4. 测试模板渲染
            print("4. 测试模板渲染...")
            from flask import render_template
            
            try:
                result = render_template('package/budget/detail.html',
                                       budget=budget,
                                       category_totals=category_totals,
                                       adult_total=adult_total,
                                       child_total=child_total)
                print(f"   ✓ 模板渲染成功，长度: {len(result)} 字符")
                
                # 检查渲染结果
                if '基本信息' in result:
                    print("   ✓ 包含基本信息")
                else:
                    print("   ✗ 缺少基本信息")
                    
                if '下载TXT' in result:
                    print("   ✓ 包含下载按钮")
                else:
                    print("   ✗ 缺少下载按钮")
                    
                if '项目详细' in result:
                    print("   ✓ 包含项目详细")
                else:
                    print("   ✗ 缺少项目详细")
                    
            except Exception as e:
                print(f"   ✗ 模板渲染失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n✅ 模板测试完成！")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_template() 