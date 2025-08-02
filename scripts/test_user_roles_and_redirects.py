#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用户角色和重定向逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_user_roles_and_redirects():
    """测试用户角色和重定向逻辑"""
    print("=== 测试用户角色和重定向逻辑 ===")
    
    # 模拟用户数据
    test_users = [
        {'username': 'admin', 'role_name': 'admin'},
        {'username': 'staff', 'role_name': 'staff'},
        {'username': 'member', 'role_name': 'member'}
    ]
    
    print("\n1. 登录重定向逻辑测试:")
    for user in test_users:
        print(f"\n用户: {user['username']}")
        print(f"角色: {user['role_name']}")
        
        # 模拟登录重定向逻辑
        if user['role_name'] == 'admin':
            redirect_url = 'admin.dashboard'
        elif user['role_name'] == 'staff':
            redirect_url = 'staff.dashboard'
        elif user['role_name'] == 'member':
            redirect_url = 'member.dashboard'
        else:
            redirect_url = 'public.index'
        
        print(f"预期重定向: {redirect_url}")
    
    print("\n2. 装饰器权限测试:")
    for user in test_users:
        print(f"\n用户: {user['username']} ({user['role_name']})")
        
        # 测试各个装饰器
        role_name = user['role_name']
        
        # admin_only 装饰器
        admin_access = role_name == 'admin'
        print(f"  admin_only: {'✓ 允许' if admin_access else '✗ 拒绝'}")
        
        # staff_only 装饰器
        staff_access = role_name in ['staff', 'admin']
        print(f"  staff_only: {'✓ 允许' if staff_access else '✗ 拒绝'}")
        
        # member_only 装饰器
        member_access = role_name in ['member', 'staff', 'admin']
        print(f"  member_only: {'✓ 允许' if member_access else '✗ 拒绝'}")
    
    print("\n3. 问题分析:")
    print("如果所有用户都被重定向到会员页面，可能的原因:")
    print("1. 用户角色数据不正确")
    print("2. 登录重定向逻辑有问题")
    print("3. 装饰器逻辑有问题")
    print("4. 路由注册有问题")
    
    print("\n4. 建议的调试步骤:")
    print("1. 检查数据库中用户的role_id")
    print("2. 检查roles表中的数据")
    print("3. 在登录时添加调试信息")
    print("4. 检查Flask-Login的配置")

if __name__ == '__main__':
    test_user_roles_and_redirects() 