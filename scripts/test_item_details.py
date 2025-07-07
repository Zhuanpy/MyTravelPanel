#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试项目详细功能
"""

import requests
import time

def test_item_details_functionality():
    """测试项目详细功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试项目详细功能 ===")
    
    try:
        # 1. 访问预算单详情页面
        print("1. 访问预算单详情页面...")
        response = requests.get(f"{base_url}/package_budget/2")
        if response.status_code == 200:
            print("   ✓ 预算单详情页面访问成功")
            
            # 检查页面内容
            content = response.text
            if '项目详细' in content:
                print("   ✓ 项目详细字段显示正常")
            else:
                print("   ✗ 项目详细字段未显示")
                
            if '项目类型' not in content:
                print("   ✓ 项目类型字段已移除")
            else:
                print("   ✗ 项目类型字段仍然存在")
                
        else:
            print(f"   ✗ 预算单详情页面访问失败: {response.status_code}")
            return
        
        # 2. 测试添加带详细信息的项目
        print("2. 测试添加带详细信息的项目...")
        form_data = {
            'csrf_token': 'test_token',
            'category': '住宿',
            'item_name': '新加坡滨海湾金沙酒店',
            'item_details': '入住日期：2025-01-15，退房日期：2025-01-17，房型：豪华海景房，含早：是，楼层：25楼',
            'pricing_method': 'person_based',
            'adult_price': '200.00',
            'child_price': '150.00',
            'count_adult_apply': '1',
            'count_child_apply': '1'
        }
        
        response = requests.post(f"{base_url}/package_budget/2/add_item", data=form_data)
        if response.status_code == 302:
            print("   ✓ 添加项目成功")
        else:
            print(f"   ✗ 添加项目失败: {response.status_code}")
            return
        
        # 3. 验证添加的项目
        print("3. 验证添加的项目...")
        response = requests.get(f"{base_url}/package_budget/2")
        if response.status_code == 200:
            content = response.text
            if '新加坡滨海湾金沙酒店' in content:
                print("   ✓ 项目名称显示正常")
            else:
                print("   ✗ 项目名称未显示")
                
            if '入住日期：2025-01-15' in content:
                print("   ✓ 项目详细信息显示正常")
            else:
                print("   ✗ 项目详细信息未显示")
                
        else:
            print(f"   ✗ 验证失败: {response.status_code}")
        
        # 4. 测试编辑项目详细信息
        print("4. 测试编辑项目详细信息...")
        # 获取最新添加的项目ID（这里假设是最后一个项目）
        response = requests.get(f"{base_url}/package_budget/2")
        if response.status_code == 200:
            # 查找编辑链接
            import re
            edit_links = re.findall(r'/package_budget/2/item/(\d+)/edit', response.text)
            if edit_links:
                latest_item_id = edit_links[-1]
                print(f"   找到项目ID: {latest_item_id}")
                
                # 访问编辑页面
                response = requests.get(f"{base_url}/package_budget/2/item/{latest_item_id}/edit")
                if response.status_code == 200:
                    print("   ✓ 编辑页面访问成功")
                    
                    # 检查编辑页面是否包含项目详细字段
                    content = response.text
                    if '项目详细' in content:
                        print("   ✓ 编辑页面包含项目详细字段")
                    else:
                        print("   ✗ 编辑页面缺少项目详细字段")
                        
                else:
                    print(f"   ✗ 编辑页面访问失败: {response.status_code}")
            else:
                print("   ✗ 未找到项目编辑链接")
        
        print("\n✅ 项目详细功能测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_item_details_functionality() 