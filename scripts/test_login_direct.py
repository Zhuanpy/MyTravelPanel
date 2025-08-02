#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试登录功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_login_direct():
    """直接测试登录功能"""
    try:
        from App import create_app
        from App.models.auth import AuthUser
        from werkzeug.security import check_password_hash
        
        app = create_app()
        
        with app.app_context():
            print("=== 直接测试登录功能 ===")
            
            # 测试用户数据
            test_cases = [
                {'email': 'admin@mytravelpanel.com', 'password': 'admin123'},
                {'email': 'staff@mytravelpanel.com', 'password': 'staff123'},
                {'email': 'member@mytravelpanel.com', 'password': 'member123'}
            ]
            
            for case in test_cases:
                print(f"\n测试用户: {case['email']}")
                
                # 查找用户
                user = AuthUser.query.filter_by(email=case['email']).first()
                
                if user:
                    print(f"✓ 用户存在 - ID: {user.id}, 用户名: {user.username}")
                    print(f"  角色ID: {user.role_id}, 角色名称: {user.role.name if user.role else 'None'}")
                    print(f"  密码哈希: {user.password_hash}")
                    
                    # 测试密码验证
                    is_valid = check_password_hash(user.password_hash, case['password'])
                    print(f"  密码验证结果: {'✓ 正确' if is_valid else '✗ 错误'}")
                    
                    if is_valid:
                        print(f"  ✓ 登录成功！应该重定向到: {user.role.name}.dashboard")
                    else:
                        print(f"  ✗ 密码验证失败")
                else:
                    print(f"✗ 用户不存在")
            
            print("\n=== 测试完成 ===")
            
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == '__main__':
    test_login_direct() 