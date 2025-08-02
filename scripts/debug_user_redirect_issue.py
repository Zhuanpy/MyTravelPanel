#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试用户重定向问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_user_redirect_issue():
    """调试用户重定向问题"""
    print("=== 调试用户重定向问题 ===")
    
    print("\n1. 模拟登录重定向逻辑:")
    test_cases = [
        {'username': 'admin', 'role_name': 'admin', 'expected': 'admin.dashboard'},
        {'username': 'staff', 'role_name': 'staff', 'expected': 'staff.dashboard'},
        {'username': 'member', 'role_name': 'member', 'expected': 'member.dashboard'},
        {'username': 'unknown', 'role_name': 'unknown', 'expected': 'public.index'}
    ]
    
    for case in test_cases:
        print(f"\n用户: {case['username']}")
        print(f"角色: {case['role_name']}")
        
        # 模拟登录重定向逻辑
        if case['role_name'] == 'admin':
            actual_redirect = 'admin.dashboard'
        elif case['role_name'] == 'staff':
            actual_redirect = 'staff.dashboard'
        elif case['role_name'] == 'member':
            actual_redirect = 'member.dashboard'
        else:
            actual_redirect = 'public.index'
        
        print(f"预期重定向: {case['expected']}")
        print(f"实际重定向: {actual_redirect}")
        print(f"状态: {'✓ 正确' if actual_redirect == case['expected'] else '✗ 错误'}")
    
    print("\n2. 装饰器权限分析:")
    print("admin_only: 只允许 admin 角色")
    print("staff_only: 允许 staff 和 admin 角色")
    print("member_only: 允许 member、staff 和 admin 角色")
    
    print("\n3. 可能的问题原因:")
    print("A. 用户角色数据问题:")
    print("   - 所有用户的role_id都是3 (member)")
    print("   - roles表中的数据不正确")
    print("   - 用户角色关联有问题")
    
    print("\nB. 登录重定向逻辑问题:")
    print("   - 登录重定向代码有bug")
    print("   - 用户角色检查逻辑错误")
    
    print("\nC. Flask-Login配置问题:")
    print("   - login_manager配置错误")
    print("   - 用户加载函数有问题")
    
    print("\n4. 建议的修复步骤:")
    print("1. 检查数据库中的用户角色数据")
    print("2. 在登录时添加更多调试信息")
    print("3. 检查用户角色关联是否正确")
    print("4. 验证roles表中的数据")

if __name__ == '__main__':
    debug_user_redirect_issue() 