#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试数据库连接和用户数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_database_connection():
    """调试数据库连接和用户数据"""
    print("=== 调试数据库连接和用户数据 ===")
    
    try:
        # 导入必要的模块
        from App import create_app
        from App.models.auth import AuthUser, Role
        from App.exts import db
        from werkzeug.security import check_password_hash
        
        # 创建应用上下文
        app = create_app()
        
        with app.app_context():
            print("✓ 应用上下文创建成功")
            
            # 测试数据库连接
            try:
                # 检查roles表
                roles = Role.query.all()
                print(f"✓ 数据库连接成功，找到 {len(roles)} 个角色")
                
                for role in roles:
                    print(f"  角色: {role.name} (ID: {role.id})")
                
                # 检查auth_users表
                users = AuthUser.query.all()
                print(f"✓ 找到 {len(users)} 个用户")
                
                for user in users:
                    print(f"  用户: {user.username} (ID: {user.id}, 角色ID: {user.role_id})")
                    print(f"    邮箱: {user.email}")
                    print(f"    密码哈希: {user.password_hash[:50]}...")
                    
                    # 测试密码验证
                    test_password = f"{user.username}123"
                    is_valid = check_password_hash(user.password_hash, test_password)
                    print(f"    密码验证 ({test_password}): {'✓ 正确' if is_valid else '✗ 错误'}")
                    
                    # 检查角色关联
                    if user.role:
                        print(f"    角色: {user.role.name}")
                    else:
                        print(f"    ⚠️ 警告: 用户没有关联角色")
                    print()
                
                # 测试特定用户查找
                test_email = "member@mytravelpanel.com"
                user = AuthUser.query.filter_by(email=test_email).first()
                
                if user:
                    print(f"✓ 找到用户: {user.username}")
                    print(f"  用户ID: {user.id}")
                    print(f"  角色ID: {user.role_id}")
                    print(f"  角色名称: {user.role.name if user.role else 'None'}")
                    print(f"  密码哈希: {user.password_hash}")
                    
                    # 测试密码验证
                    test_password = "member123"
                    is_valid = check_password_hash(user.password_hash, test_password)
                    print(f"  密码验证结果: {'✓ 正确' if is_valid else '✗ 错误'}")
                else:
                    print(f"✗ 未找到邮箱为 {test_email} 的用户")
                
            except Exception as e:
                print(f"✗ 数据库查询失败: {e}")
                
    except Exception as e:
        print(f"✗ 应用创建失败: {e}")

if __name__ == '__main__':
    debug_database_connection() 