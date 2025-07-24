#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修复CSRF令牌问题
"""

import os
import re
from pathlib import Path

def fix_csrf_in_file(file_path):
    """修复单个文件中的CSRF令牌问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修复各种CSRF令牌用法
        replacements = [
            # 修复 input 字段
            (r'value="{{ csrf_token\(\) }}"', 'value="{{ csrf_token }}"'),
            # 修复 meta 标签
            (r'content="{{ csrf_token\(\) }}"', 'content="{{ csrf_token }}"'),
            (r'content="{{ csrf_token\(\) if csrf_token else \'\' }}"', 'content="{{ csrf_token }}"'),
            # 修复 JavaScript 中的用法
            (r"'{{ csrf_token\(\) }}'", "'{{ csrf_token }}'"),
            (r'"{{ csrf_token\(\) }}"', '"{{ csrf_token }}"'),
            # 修复其他可能的用法
            (r'{{ csrf_token\(\) }}', '{{ csrf_token }}'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 已修复: {file_path}")
            return True
        else:
            print(f"- 无需修复: {file_path}")
            return False
            
    except Exception as e:
        print(f"✗ 修复失败: {file_path} - {e}")
        return False

def find_html_files(directory):
    """查找所有HTML文件"""
    html_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    return html_files

def main():
    """主函数"""
    print("=== 批量修复CSRF令牌问题 ===")
    
    # 查找所有HTML文件
    app_dir = Path("App/templates")
    html_files = find_html_files(app_dir)
    
    print(f"找到 {len(html_files)} 个HTML文件")
    
    fixed_count = 0
    for file_path in html_files:
        if fix_csrf_in_file(file_path):
            fixed_count += 1
    
    print(f"\n=== 修复完成 ===")
    print(f"总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main() 