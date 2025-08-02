#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称：organize_scripts.py
功能描述：整理scripts文件夹中的脚本文件到对应的子目录
创建日期：2024-01-XX
作者：Assistant
版本：1.0
"""

import os
import shutil
import re

def create_directory_if_not_exists(directory):
    """创建目录（如果不存在）"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录：{directory}")

def move_file_to_category(file_path, category_dir, file_name):
    """移动文件到指定分类目录"""
    source_path = os.path.join('scripts', file_name)
    target_path = os.path.join('scripts', category_dir, file_name)
    
    if os.path.exists(source_path):
        shutil.move(source_path, target_path)
        print(f"移动文件：{file_name} -> {category_dir}/")
    else:
        print(f"文件不存在：{file_name}")

def categorize_scripts():
    """整理脚本文件到对应分类"""
    
    # 定义文件分类规则
    categories = {
        'database': [
            'create_auth_tables.sql',
            'fix_passwords_final.sql',
            'fix_password_hashes.sql',
            'fix_passwords_simple.py',
            'fix_all_user_passwords.sql',
            'fix_member_password.py',
            'check_member_user_data.sql',
            'check_member_login_issue.sql',
            'check_user_roles_in_db.sql',
            'verify_roles_data.sql',
            'check_tables_and_data.sql',
            'check_user_roles.sql',
            'debug_auth_users.sql',
            'check_and_fix_roles.sql',
            'create_invitation_codes_table.py'
        ],
        'testing': [
            'test_login.py',
            'test_login_direct.py',
            'test_auth_system.py',
            'test_user_roles_and_redirects.py',
            'test_guest_only.py',
            'test_login_redirect.py',
            'test_dashboard_fix.py',
            'test_flight_ref_name.py',
            'simple_test.py',
            'debug_login_issue.py',
            'debug_user_roles.py',
            'debug_user_redirect_issue.py',
            'fix_login_redirect.py',
            'fix_login_issue.py'
        ],
        'data_update': [
            'update_flight_ref_names_direct.py',
            'update_flight_ref_names_simple.py',
            'update_flight_ref_names.py'
        ],
        'admin': [
            'create_admin.py',
            'init_auth_system.py'
        ],
        'utils': [
            'debug_database_connection.py',
            'manual_fix_guide.md'
        ]
    }
    
    # 创建分类目录
    for category in categories.keys():
        create_directory_if_not_exists(os.path.join('scripts', category))
    
    # 移动文件到对应分类
    for category, files in categories.items():
        for file_name in files:
            move_file_to_category('scripts', category, file_name)
    
    # 处理剩余文件（按文件名模式分类）
    remaining_files = []
    for file_name in os.listdir('scripts'):
        file_path = os.path.join('scripts', file_name)
        if os.path.isfile(file_path) and file_name != 'README.md' and file_name != 'organize_scripts.py':
            # 检查是否已经在分类中
            categorized = False
            for category_files in categories.values():
                if file_name in category_files:
                    categorized = True
                    break
            
            if not categorized:
                remaining_files.append(file_name)
    
    # 处理剩余文件
    if remaining_files:
        print("\n剩余文件（需要手动分类）：")
        for file_name in remaining_files:
            print(f"  - {file_name}")
        
        # 尝试自动分类剩余文件
        for file_name in remaining_files:
            if file_name.endswith('.sql'):
                move_file_to_category('scripts', 'database', file_name)
            elif file_name.startswith('test_') or file_name.startswith('debug_'):
                move_file_to_category('scripts', 'testing', file_name)
            elif file_name.startswith('update_'):
                move_file_to_category('scripts', 'data_update', file_name)
            elif file_name.startswith('create_') or file_name.startswith('init_'):
                move_file_to_category('scripts', 'admin', file_name)
            else:
                move_file_to_category('scripts', 'utils', file_name)

def cleanup_temp_files():
    """清理临时文件"""
    temp_patterns = [
        '*.tmp',
        '*.temp',
        '* --*',
        '* -ErrorAction*',
        '* --porcelain*',
        '* --name-only*'
    ]
    
    for pattern in temp_patterns:
        # 这里可以添加具体的清理逻辑
        pass

def main():
    """主函数"""
    print("开始整理scripts文件夹...")
    
    # 检查是否在正确的目录
    if not os.path.exists('scripts'):
        print("错误：当前目录下没有scripts文件夹")
        return
    
    # 整理脚本文件
    categorize_scripts()
    
    # 清理临时文件
    cleanup_temp_files()
    
    print("\n整理完成！")
    print("\n目录结构：")
    
    # 显示整理后的目录结构
    for root, dirs, files in os.walk('scripts'):
        level = root.replace('scripts', '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")

if __name__ == "__main__":
    main() 