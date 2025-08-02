#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试登录重定向逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.auth import AuthUser, Role
from App.exts import db

def test_login_redirect():
    """测试登录重定向逻辑"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试登录重定向逻辑 ===")
        
        # 获取所有用户
        users = AuthUser.query.all()
        
        for user in users:
            print(f"\n用户: {user.username}")
            print(f"邮箱: {user.email}")
            print(f"角色ID: {user.role_id}")
            
            if user.role:
                print(f"角色名称: {user.role.name}")
                print(f"角色描述: {user.role.description}")
                
                # 模拟登录重定向逻辑
                if user.role.name == 'admin':
                    redirect_url = 'admin.dashboard'
                elif user.role.name == 'staff':
                    redirect_url = 'staff.dashboard'
                elif user.role.name == 'member':
                    redirect_url = 'member.dashboard'
                else:
                    redirect_url = 'public.index'
                
                print(f"预期重定向: {redirect_url}")
            else:
                print("❌ 用户没有角色")
        
        print("\n=== 检查路由是否存在 ===")
        
        # 检查路由是否存在
        with app.test_client() as client:
            try:
                # 测试admin路由
                response = client.get('/admin/dashboard')
                print(f"admin.dashboard 状态: {response.status_code}")
            except Exception as e:
                print(f"admin.dashboard 错误: {e}")
            
            try:
                # 测试staff路由
                response = client.get('/staff/dashboard')
                print(f"staff.dashboard 状态: {response.status_code}")
            except Exception as e:
                print(f"staff.dashboard 错误: {e}")
            
            try:
                # 测试member路由
                response = client.get('/member/dashboard')
                print(f"member.dashboard 状态: {response.status_code}")
            except Exception as e:
                print(f"member.dashboard 错误: {e}")

if __name__ == '__main__':
    test_login_redirect() 