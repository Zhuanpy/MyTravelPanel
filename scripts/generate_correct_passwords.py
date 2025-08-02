#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成正确的密码哈希
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_correct_passwords():
    """生成正确的密码哈希"""
    try:
        from werkzeug.security import generate_password_hash, check_password_hash
        
        passwords = {
            'admin': 'admin123',
            'staff': 'staff123', 
            'member': 'member123'
        }
        
        print("=== 生成正确的密码哈希 ===")
        for username, password in passwords.items():
            hash_value = generate_password_hash(password)
            print(f"{username}: {hash_value}")
            
            # 验证哈希是否正确
            is_valid = check_password_hash(hash_value, password)
            print(f"验证结果: {'✓ 正确' if is_valid else '✗ 错误'}")
            print()
            
        print("=== SQL更新语句 ===")
        for username, password in passwords.items():
            hash_value = generate_password_hash(password)
            print(f"UPDATE auth_users SET password_hash = '{hash_value}' WHERE username = '{username}';")
            
    except ImportError as e:
        print(f"错误: 无法导入werkzeug - {e}")
        print("请确保在虚拟环境中运行此脚本")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == '__main__':
    generate_correct_passwords() 