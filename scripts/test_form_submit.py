#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试旅游项目创建表单提交
"""

import requests
from datetime import datetime

def test_form_submit():
    """测试表单提交功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试旅游项目创建表单提交 ===")
    
    try:
        # 1. 先获取创建页面，获取CSRF令牌
        print("1. 获取创建页面...")
        response = requests.get(f"{base_url}/tour_projects/create")
        
        if response.status_code != 200:
            print(f"   ✗ 获取页面失败: {response.status_code}")
            return
        
        print("   ✓ 页面获取成功")
        
        # 从HTML中提取CSRF令牌
        html_content = response.text
        
        # 查找CSRF令牌的所有可能位置
        print("   查找CSRF令牌...")
        
        # 方法1: 从input字段中提取
        csrf_input_start = html_content.find('name="csrf_token" value="')
        if csrf_input_start != -1:
            csrf_input_start += 23
            csrf_input_end = html_content.find('"', csrf_input_start)
            csrf_token_input = html_content[csrf_input_start:csrf_input_end]
            print(f"   从input字段找到: {csrf_token_input}")
        else:
            print("   未找到input字段中的CSRF令牌")
            csrf_token_input = ""
        
        # 方法2: 从meta标签中提取
        csrf_meta_start = html_content.find('<meta name="csrf-token" content="')
        if csrf_meta_start != -1:
            csrf_meta_start += 32
            csrf_meta_end = html_content.find('"', csrf_meta_start)
            csrf_token_meta = html_content[csrf_meta_start:csrf_meta_end]
            print(f"   从meta标签找到: {csrf_token_meta}")
        else:
            print("   未找到meta标签中的CSRF令牌")
            csrf_token_meta = ""
        
        # 选择有效的CSRF令牌
        if csrf_token_input and len(csrf_token_input) > 10:
            csrf_token = csrf_token_input
            print(f"   使用input字段的CSRF令牌: {csrf_token}")
        elif csrf_token_meta and len(csrf_token_meta) > 10:
            csrf_token = csrf_token_meta
            print(f"   使用meta标签的CSRF令牌: {csrf_token}")
        else:
            print("   ✗ 无法获取有效的CSRF令牌")
            # 保存HTML内容到文件以便调试
            with open('debug_html.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print("   已保存HTML内容到debug_html.html文件")
            return
        
        # 2. 提交表单数据
        print("\n2. 提交表单数据...")
        
        form_data = {
            'csrf_token': csrf_token,
            'projectName': '测试项目',
            'projectHID': 'TEST123',
            'projectType': '自由行',
            'budget': '5000',
            'projectStatus': '处理中',
            'departureDate': '25/12/2024',
            'contactPerson': '张三',
            'contactInfo': '123456789',
            'remarks': '这是一个测试项目'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"   提交的表单数据: {form_data}")
        
        response = requests.post(
            f"{base_url}/tour_projects/create", 
            data=form_data,
            headers=headers,
            allow_redirects=False
        )
        
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应头: {dict(response.headers)}")
        
        if response.status_code == 302:  # 重定向
            print("   ✓ 表单提交成功，重定向到管理页面")
            print(f"   重定向到: {response.headers.get('Location', '未知')}")
        elif response.status_code == 400:
            print("   ⚠ 表单提交返回400错误")
            print(f"   响应内容: {response.text[:1000]}...")
            
            # 检查是否是CSRF错误
            if 'CSRF' in response.text or 'csrf' in response.text.lower():
                print("   ✗ CSRF验证失败")
            else:
                print("   ✗ 其他验证错误")
        elif response.status_code == 200:
            print("   ⚠ 表单提交后返回200，可能需要检查错误信息")
            print(f"   响应内容: {response.text[:500]}...")
        else:
            print(f"   ✗ 表单提交失败: {response.status_code}")
            print(f"   响应内容: {response.text[:500]}...")
        
        # 3. 检查管理页面
        print("\n3. 检查管理页面...")
        response = requests.get(f"{base_url}/tour_projects/manage")
        
        if response.status_code == 200:
            print("   ✓ 管理页面访问成功")
            if '测试项目' in response.text:
                print("   ✓ 新创建的项目出现在列表中")
            else:
                print("   ⚠ 新创建的项目未出现在列表中")
        else:
            print(f"   ✗ 管理页面访问失败: {response.status_code}")
        
    except requests.exceptions.ConnectionError:
        print("   ✗ 无法连接到服务器，请确保Flask应用正在运行")
    except Exception as e:
        print(f"   ✗ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_form_submit() 