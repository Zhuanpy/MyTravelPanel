#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试登录重定向
"""

import requests

def test_login_redirect():
    """测试登录重定向"""
    base_url = "http://192.168.5.60:5000"
    
    print("=== 测试登录重定向 ===")
    
    # 测试登录页面
    try:
        response = requests.get(f"{base_url}/auth/login")
        print(f"登录页面状态: {response.status_code}")
    except Exception as e:
        print(f"登录页面错误: {e}")
    
    # 测试各个仪表板页面
    dashboards = [
        ("admin.dashboard", "/admin/dashboard"),
        ("staff.dashboard", "/staff/dashboard"),
        ("member.dashboard", "/member/dashboard")
    ]
    
    for name, path in dashboards:
        try:
            response = requests.get(f"{base_url}{path}")
            print(f"{name}: {response.status_code}")
        except Exception as e:
            print(f"{name} 错误: {e}")

if __name__ == '__main__':
    test_login_redirect() 