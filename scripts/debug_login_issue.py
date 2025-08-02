#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试登录重定向问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.auth import AuthUser, Role
from App.utils.permissions import has_role
from App.exts import db

def debug_login_issue():
    """调试登录重定向问题"""
    app = create_app()
    
    with app.app_context():
        print("=== 调试登录重定向问题 ===")
        
        # 获取所有用户
        users = AuthUser.query.all()
        
        for user in users:
            print(f"\n用户: {user.username}")
            print(f"角色: {user.role.name if user.role else 'None'}")
            
            # 测试权限检查
            is_admin = has_role(user, 'admin')
            is_staff = has_role(user, 'staff')
            is_member = has_role(user, 'member')
            
            print(f"is_admin: {is_admin}")
            print(f"is_staff: {is_staff}")
            print(f"is_member: {is_member}")
            
            # 测试装饰器逻辑
            print("装饰器逻辑测试:")
            
            # staff_only 装饰器逻辑
            if not has_role(user, 'staff') and not has_role(user, 'admin'):
                print("  staff_only: 拒绝访问")
            else:
                print("  staff_only: 允许访问")
            
            # member_only 装饰器逻辑
            if not has_role(user, 'member') and not has_role(user, 'staff') and not has_role(user, 'admin'):
                print("  member_only: 拒绝访问")
            else:
                print("  member_only: 允许访问")
            
            # 登录重定向逻辑
            if user.role.name == 'admin':
                redirect_url = 'admin.dashboard'
            elif user.role.name == 'staff':
                redirect_url = 'staff.dashboard'
            elif user.role.name == 'member':
                redirect_url = 'member.dashboard'
            else:
                redirect_url = 'public.index'
            
            print(f"登录重定向: {redirect_url}")

if __name__ == '__main__':
    debug_login_issue() 