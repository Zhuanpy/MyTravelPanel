#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称：verify_project_rules.py
功能描述：验证项目规则是否得到正确应用
创建日期：2024-01-XX
作者：Assistant
版本：1.0
"""

import os
import re

def check_scripts_directory_structure():
    """检查scripts目录结构"""
    print("检查scripts目录结构...")
    
    required_dirs = ['database', 'testing', 'data_update', 'admin', 'utils']
    missing_dirs = []
    
    for dir_name in required_dirs:
        dir_path = os.path.join('scripts', dir_name)
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_name)
        else:
            print(f"✓ 目录存在：{dir_name}/")
    
    if missing_dirs:
        print(f"✗ 缺失目录：{missing_dirs}")
        return False
    else:
        print("✓ 所有必需目录都存在")
        return True

def check_file_naming_convention():
    """检查文件命名规范"""
    print("\n检查文件命名规范...")
    
    naming_issues = []
    
    for root, dirs, files in os.walk('scripts'):
        for file_name in files:
            if file_name.endswith('.py') or file_name.endswith('.sql'):
                # 检查文件名是否包含空格或特殊字符
                if ' ' in file_name or re.search(r'[^\w\-_\.]', file_name):
                    naming_issues.append(os.path.join(root, file_name))
                # 检查文件名是否过长
                if len(file_name) > 50:
                    naming_issues.append(os.path.join(root, file_name))
    
    if naming_issues:
        print("✗ 命名规范问题：")
        for issue in naming_issues:
            print(f"  - {issue}")
        return False
    else:
        print("✓ 所有文件命名符合规范")
        return True

def check_script_headers():
    """检查脚本头部注释"""
    print("\n检查脚本头部注释...")
    
    missing_headers = []
    
    for root, dirs, files in os.walk('scripts'):
        for file_name in files:
            if file_name.endswith('.py'):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(500)  # 读取前500字符
                        if not content.startswith('#!/usr/bin/env python3'):
                            missing_headers.append(file_path)
                except Exception as e:
                    print(f"读取文件失败 {file_path}: {str(e)}")
    
    if missing_headers:
        print("✗ 缺少标准头部注释的文件：")
        for file_path in missing_headers:
            print(f"  - {file_path}")
        return False
    else:
        print("✓ 所有Python脚本都有标准头部注释")
        return True

def check_temp_files():
    """检查临时文件"""
    print("\n检查临时文件...")
    
    temp_files = []
    temp_patterns = [
        '*.tmp', '*.temp', '*.log', '* --*', '* -ErrorAction*',
        '* --porcelain*', '* --name-only*', 'ion.html*', 'tatus*', 'how*'
    ]
    
    for pattern in temp_patterns:
        import glob
        matching_files = glob.glob(os.path.join('scripts', pattern))
        temp_files.extend(matching_files)
    
    if temp_files:
        print("✗ 发现临时文件：")
        for file_path in temp_files:
            print(f"  - {file_path}")
        return False
    else:
        print("✓ 没有发现临时文件")
        return True

def check_gitignore_rules():
    """检查.gitignore规则"""
    print("\n检查.gitignore规则...")
    
    gitignore_path = '.gitignore'
    if not os.path.exists(gitignore_path):
        print("✗ .gitignore文件不存在")
        return False
    
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否包含scripts相关的忽略规则
        required_patterns = [
            'scripts/*.tmp',
            'scripts/*.temp',
            'scripts/*.log',
            'scripts/__pycache__/',
            'scripts/*.pyc'
        ]
        
        missing_patterns = []
        for pattern in required_patterns:
            if pattern not in content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print("✗ .gitignore缺少以下规则：")
            for pattern in missing_patterns:
                print(f"  - {pattern}")
            return False
        else:
            print("✓ .gitignore规则完整")
            return True
            
    except Exception as e:
        print(f"读取.gitignore失败: {str(e)}")
        return False

def generate_report():
    """生成检查报告"""
    print("=" * 50)
    print("项目规则检查报告")
    print("=" * 50)
    
    checks = [
        ("目录结构", check_scripts_directory_structure),
        ("文件命名", check_file_naming_convention),
        ("脚本头部", check_script_headers),
        ("临时文件", check_temp_files),
        ("Git忽略规则", check_gitignore_rules)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"检查 {check_name} 时出错: {str(e)}")
            results.append((check_name, False))
    
    print("\n" + "=" * 50)
    print("检查结果汇总")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{check_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("🎉 所有检查都通过！项目规则得到正确应用。")
    else:
        print("⚠️  部分检查未通过，请根据上述建议进行修复。")

def main():
    """主函数"""
    print("开始验证项目规则...")
    
    # 检查是否在正确的目录
    if not os.path.exists('scripts'):
        print("错误：当前目录下没有scripts文件夹")
        return
    
    # 生成检查报告
    generate_report()

if __name__ == "__main__":
    main() 