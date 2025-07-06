#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试详情页面错误
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def debug_detail_error():
    """详细调试详情页面错误"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查找预算单
            budget = BudgetHeader.query.first()
            if not budget:
                print("❌ 没有找到预算单")
                return False
            
            print(f"📋 测试预算单 ID: {budget.id}")
            print(f"  套餐名称: {budget.package_name}")
            
            # 手动执行详情页面的逻辑
            print(f"\n🔍 手动执行详情页面逻辑...")
            
            try:
                # 计算分类统计
                category_totals = {}
                adult_total = 0
                child_total = 0
                tax_total = 0
                
                print(f"  开始处理 {len(budget.items)} 个项目...")
                
                for i, item in enumerate(budget.items, 1):
                    print(f"    处理项目 {i}: {item.item_name}")
                    
                    try:
                        # 分类统计
                        category = item.category or '未分类'
                        if category not in category_totals:
                            category_totals[category] = 0
                        
                        subtotal = item.subtotal or 0
                        category_totals[category] += subtotal
                        print(f"      分类: {category}, 小计: {subtotal}")
                        
                        # 计算成人费用
                        if item.count_adult_apply:
                            adult_count = item.adult_count_override or budget.adult_count
                            adult_unit_price = item.adult_unit_price or 0
                            adult_total += adult_unit_price * adult_count
                            print(f"      成人费用: {adult_unit_price} × {adult_count} = {adult_unit_price * adult_count}")
                        
                        # 计算儿童费用
                        if item.count_child_apply:
                            child_count = item.child_count_override or budget.child_count
                            child_unit_price = item.child_unit_price or 0
                            child_total += child_unit_price * child_count
                            print(f"      儿童费用: {child_unit_price} × {child_count} = {child_unit_price * child_count}")
                        
                        # 计算税费
                        if item.tax_rate:
                            tax_amount = (item.subtotal or 0) * item.tax_rate
                            tax_total += tax_amount
                            print(f"      税费: {item.subtotal or 0} × {item.tax_rate} = {tax_amount}")
                        
                        if item.tax_amount:
                            tax_total += float(item.tax_amount or 0)
                            print(f"      固定税费: {item.tax_amount}")
                            
                    except Exception as item_error:
                        print(f"      ❌ 处理项目 {i} 时出错: {item_error}")
                        import traceback
                        traceback.print_exc()
                
                print(f"\n  ✅ 计算完成:")
                print(f"    成人总费用: {adult_total}")
                print(f"    儿童总费用: {child_total}")
                print(f"    税费总额: {tax_total}")
                print(f"    分类统计: {category_totals}")
                
                # 测试模板渲染
                print(f"\n🎨 测试模板渲染...")
                from flask import render_template
                
                try:
                    template_result = render_template('package/budget/detail.html',
                                                   budget=budget,
                                                   category_totals=category_totals,
                                                   adult_total=adult_total,
                                                   child_total=child_total,
                                                   tax_total=tax_total)
                    print(f"  ✅ 模板渲染成功，长度: {len(template_result)} 字符")
                except Exception as template_error:
                    print(f"  ❌ 模板渲染失败: {template_error}")
                    import traceback
                    traceback.print_exc()
                
            except Exception as calc_error:
                print(f"  ❌ 计算过程出错: {calc_error}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"❌ 调试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    print("🚀 开始详细调试详情页面错误...")
    success = debug_detail_error()
    if success:
        print("\n🎉 调试完成！")
    else:
        print("\n💥 调试失败！")
        sys.exit(1) 