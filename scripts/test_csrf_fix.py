#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CSRF修复
"""

import requests
import time

def test_csrf_fix():
    """测试CSRF修复"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试CSRF修复 ===")
    
    try:
        # 1. 测试账号点击次数增加API
        print("1. 测试账号点击次数增加API...")
        
        # 先获取一个账号ID（假设ID为178）
        account_id = 178
        
        response = requests.post(f"{base_url}/account/api/accounts/increment_click/{account_id}", 
                               headers={'Content-Type': 'application/json'})
        
        print(f"   响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ CSRF修复成功，点击次数增加API正常工作")
            try:
                data = response.json()
                print(f"   响应数据: {data}")
            except:
                print("   响应不是JSON格式")
        elif response.status_code == 400:
            print("   ✗ 仍然有CSRF错误")
            print(f"   响应内容: {response.text[:200]}")
        else:
            print(f"   ✗ 其他错误: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
        
        # 2. 测试其他API是否正常
        print("\n2. 测试其他API...")
        
        # 测试获取账号列表
        response = requests.get(f"{base_url}/account/api/accounts")
        if response.status_code == 200:
            print("   ✓ 获取账号列表API正常")
        else:
            print(f"   ✗ 获取账号列表API异常: {response.status_code}")
        
        # 测试获取热门账号
        response = requests.get(f"{base_url}/account/api/accounts/popular")
        if response.status_code == 200:
            print("   ✓ 获取热门账号API正常")
        else:
            print(f"   ✗ 获取热门账号API异常: {response.status_code}")
        
        print("\n✅ CSRF修复测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_csrf_fix() 