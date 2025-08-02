#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的数据库测试
"""

import os
import sys

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_dir)

try:
    from App import create_app
    from App.models.auth import AuthUser, Role
    from App.exts import db
    
    print("=== 数据库连接测试 ===")
    
    app = create_app()
    
    with app.app_context():
        print("✅ 应用上下文创建成功")
        
        # 测试数据库连接
        try:
            # 获取所有角色
            roles = Role.query.all()
            print(f"✅ 角色数量: {len(roles)}")
            for role in roles:
                print(f"  - {role.name}: {role.description}")
        except Exception as e:
            print(f"❌ 角色查询失败: {e}")
        
        # 测试用户查询
        try:
            users = AuthUser.query.all()
            print(f"✅ 用户数量: {len(users)}")
            for user in users:
                role_name = user.role.name if user.role else "无角色"
                print(f"  - {user.username} ({user.email}): {role_name}")
        except Exception as e:
            print(f"❌ 用户查询失败: {e}")
        
        # 测试登录重定向逻辑
        print("\n=== 登录重定向逻辑测试 ===")
        for user in users:
            if user.role:
                if user.role.name == 'admin':
                    redirect_url = 'admin.dashboard'
                elif user.role.name == 'staff':
                    redirect_url = 'staff.dashboard'
                elif user.role.name == 'member':
                    redirect_url = 'member.dashboard'
                else:
                    redirect_url = 'public.index'
                
                print(f"{user.username} ({user.role.name}) -> {redirect_url}")
            else:
                print(f"{user.username} (无角色) -> public.index")

except ImportError as e:
    print(f"❌ 导入错误: {e}")
except Exception as e:
    print(f"❌ 其他错误: {e}") 