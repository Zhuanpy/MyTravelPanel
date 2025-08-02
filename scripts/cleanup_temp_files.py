#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称：cleanup_temp_files.py
功能描述：清理scripts文件夹中的临时文件
创建日期：2024-01-XX
作者：Assistant
版本：1.0
"""

import os
import glob
import re

def cleanup_temp_files():
    """清理临时文件"""
    
    # 定义临时文件模式
    temp_patterns = [
        '*.tmp',
        '*.temp',
        '*.log',
        '* --*',
        '* -ErrorAction*',
        '* --porcelain*',
        '* --name-only*',
        'ion.html*',
        'tatus*',
        'how*'
    ]
    
    cleaned_files = []
    
    for pattern in temp_patterns:
        # 使用glob查找匹配的文件
        matching_files = glob.glob(os.path.join('scripts', pattern))
        for file_path in matching_files:
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    cleaned_files.append(os.path.basename(file_path))
                    print(f"删除临时文件：{os.path.basename(file_path)}")
                except Exception as e:
                    print(f"删除文件失败 {os.path.basename(file_path)}: {str(e)}")
    
    # 清理__pycache__目录
    pycache_dirs = []
    for root, dirs, files in os.walk('scripts'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_path = os.path.join(root, dir_name)
                try:
                    import shutil
                    shutil.rmtree(pycache_path)
                    pycache_dirs.append(pycache_path)
                    print(f"删除缓存目录：{pycache_path}")
                except Exception as e:
                    print(f"删除目录失败 {pycache_path}: {str(e)}")
    
    # 清理.pyc文件
    pyc_files = []
    for root, dirs, files in os.walk('scripts'):
        for file_name in files:
            if file_name.endswith('.pyc'):
                pyc_path = os.path.join(root, file_name)
                try:
                    os.remove(pyc_path)
                    pyc_files.append(pyc_path)
                    print(f"删除缓存文件：{file_name}")
                except Exception as e:
                    print(f"删除文件失败 {file_name}: {str(e)}")
    
    return cleaned_files, pycache_dirs, pyc_files

def list_remaining_files():
    """列出剩余的文件"""
    print("\n剩余文件：")
    for root, dirs, files in os.walk('scripts'):
        level = root.replace('scripts', '').count(os.sep)
        indent = ' ' * 2 * level
        if level > 0:
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                if not file.startswith('.'):  # 忽略隐藏文件
                    print(f"{subindent}{file}")

def main():
    """主函数"""
    print("开始清理scripts文件夹中的临时文件...")
    
    # 检查是否在正确的目录
    if not os.path.exists('scripts'):
        print("错误：当前目录下没有scripts文件夹")
        return
    
    # 清理临时文件
    cleaned_files, pycache_dirs, pyc_files = cleanup_temp_files()
    
    # 显示清理结果
    print(f"\n清理完成！")
    print(f"删除的临时文件：{len(cleaned_files)} 个")
    print(f"删除的缓存目录：{len(pycache_dirs)} 个")
    print(f"删除的缓存文件：{len(pyc_files)} 个")
    
    # 显示剩余文件
    list_remaining_files()

if __name__ == "__main__":
    main() 