#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复登录重定向问题
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
            print(f"角色: {user.role.name if user.role else 'None'}")
            
            # 模拟登录重定向逻辑
            if user.role and user.role.name == 'admin':
                redirect_url = 'admin.dashboard'
            elif user.role and user.role.name == 'staff':
                redirect_url = 'staff.dashboard'
            elif user.role and user.role.name == 'member':
                redirect_url = 'member.dashboard'
            else:
                redirect_url = 'public.index'
            
            print(f"预期重定向: {redirect_url}")
            
            # 测试实际重定向
            print("实际重定向测试:")
            try:
                with app.test_client() as client:
                    # 模拟登录
                    response = client.get(f'/auth/login')
                    print(f"  登录页面状态: {response.status_code}")
                    
                    # 测试各个仪表板页面
                    response = client.get('/admin/dashboard')
                    print(f"  admin.dashboard: {response.status_code}")
                    
                    response = client.get('/staff/dashboard')
                    print(f"  staff.dashboard: {response.status_code}")
                    
                    response = client.get('/member/dashboard')
                    print(f"  member.dashboard: {response.status_code}")
                    
            except Exception as e:
                print(f"  错误: {e}")

def check_auth_routes():
    """检查认证路由"""
    app = create_app()
    
    print("\n=== 检查认证路由 ===")
    
    with app.test_client() as client:
        # 检查登录页面
        response = client.get('/auth/login')
        print(f"登录页面: {response.status_code}")
        
        # 检查注册页面
        response = client.get('/auth/register')
        print(f"注册页面: {response.status_code}")

if __name__ == '__main__':
    test_login_redirect()
    check_auth_routes() 