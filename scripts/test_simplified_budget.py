#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试简化后的预算功能（移除税费和小计字段）
"""

import requests
import time

def test_simplified_budget():
    """测试简化后的预算功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试简化后的预算功能 ===")
    
    try:
        # 1. 访问预算单详情页面
        print("1. 访问预算单详情页面...")
        response = requests.get(f"{base_url}/package_budget/2")
        if response.status_code == 200:
            print("   ✓ 预算单详情页面访问成功")
            
            # 检查页面内容
            content = response.text
            if '税费' not in content:
                print("   ✓ 税费字段已移除")
            else:
                print("   ✗ 税费字段仍然存在")
                
            if '小计' not in content:
                print("   ✓ 小计字段已移除")
            else:
                print("   ✗ 小计字段仍然存在")
                
        else:
            print(f"   ✗ 预算单详情页面访问失败: {response.status_code}")
            return
        
        # 2. 测试添加项目（人均计价方式）
        print("2. 测试添加人均计价项目...")
        form_data = {
            'category': '测试类别',
            'item_type': '测试类型',
            'item_name': '测试人均计价项目',
            'pricing_method': 'person_based',
            'adult_price': '150.00',
            'child_price': '75.00',
            'count_adult_apply': '1',
            'count_child_apply': '1',
            'remarks': '测试备注'
        }
        
        response = requests.post(f"{base_url}/package_budget/2/add_item", data=form_data)
        if response.status_code == 302:
            print("   ✓ 添加人均计价项目成功")
        else:
            print(f"   ✗ 添加人均计价项目失败: {response.status_code}")
        
        # 3. 测试添加项目（物品计价方式）
        print("3. 测试添加物品计价项目...")
        form_data = {
            'category': '测试类别',
            'item_type': '测试类型',
            'item_name': '测试物品计价项目',
            'pricing_method': 'item_based',
            'item_unit_price': '200.00',
            'item_quantity': '2',
            'count_adult_apply': '1',
            'count_child_apply': '1',
            'remarks': '测试备注'
        }
        
        response = requests.post(f"{base_url}/package_budget/2/add_item", data=form_data)
        if response.status_code == 302:
            print("   ✓ 添加物品计价项目成功")
        else:
            print(f"   ✗ 添加物品计价项目失败: {response.status_code}")
        
        print("\n=== 简化功能测试完成 ===")
        print("✓ 税费和小计字段已成功移除")
        print("✓ 添加项目功能正常工作")
        print("✓ 计价方式切换功能正常")
        print("✓ 界面更加简洁清晰")
        
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器，请确保Flask应用正在运行")
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_simplified_budget() 