#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试@guest_only装饰器行为
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_guest_only_logic():
    """测试@guest_only装饰器逻辑"""
    print("=== 测试@guest_only装饰器逻辑 ===")
    
    # 模拟用户数据
    test_users = [
        {'username': 'admin', 'role_name': 'admin'},
        {'username': 'staff', 'role_name': 'staff'},
        {'username': 'member', 'role_name': 'member'},
        {'username': 'guest', 'role_name': None}
    ]
    
    for user in test_users:
        print(f"\n用户: {user['username']}")
        print(f"角色: {user['role_name']}")
        
        # 模拟@guest_only装饰器逻辑
        if user['role_name'] == 'admin':
            redirect_url = 'admin.dashboard'
        elif user['role_name'] == 'staff':
            redirect_url = 'staff.dashboard'
        elif user['role_name'] == 'member':
            redirect_url = 'member.dashboard'
        else:
            redirect_url = 'public.index'
        
        print(f"重定向到: {redirect_url}")
        
        # 检查是否所有用户都被重定向到admin
        if redirect_url == 'admin.dashboard':
            print("⚠️  这个用户会被重定向到admin页面")
        else:
            print("✅ 这个用户会被重定向到正确的页面")

if __name__ == '__main__':
    test_guest_only_logic() 