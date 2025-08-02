#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复会员用户密码
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash, check_password_hash

def fix_member_password():
    """修复会员用户密码"""
    print("=== 修复会员用户密码 ===")
    
    # 测试密码
    password = "member123"
    
    # 生成新的密码哈希
    new_hash = generate_password_hash(password)
    print(f"密码: {password}")
    print(f"新哈希: {new_hash}")
    
    # 验证密码
    is_valid = check_password_hash(new_hash, password)
    print(f"验证结果: {'✓ 正确' if is_valid else '✗ 错误'}")
    
    # 生成SQL更新语句
    print("\n=== SQL更新语句 ===")
    print("请在MySQL中执行以下SQL语句来更新会员用户密码:")
    print()
    print(f"UPDATE auth_users SET password_hash = '{new_hash}' WHERE username = 'member';")
    print()
    
    # 检查其他用户密码
    print("=== 其他用户密码哈希 ===")
    test_passwords = {
        'admin': 'admin123',
        'staff': 'staff123',
        'member': 'member123'
    }
    
    for username, pwd in test_passwords.items():
        hash_value = generate_password_hash(pwd)
        print(f"{username}: {hash_value}")
    
    print("\n=== 完整的用户更新SQL ===")
    for username, pwd in test_passwords.items():
        hash_value = generate_password_hash(pwd)
        print(f"UPDATE auth_users SET password_hash = '{hash_value}' WHERE username = '{username}';")

if __name__ == '__main__':
    fix_member_password() 