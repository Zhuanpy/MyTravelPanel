#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装Excel修复脚本所需的依赖包
"""

import subprocess
import sys

def install_package(package):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ 成功安装 {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装 {package} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 安装Excel修复脚本所需的依赖包")
    print("=" * 50)
    
    # 需要安装的包
    packages = [
        "pandas",
        "openpyxl", 
        "xlrd",
        "chardet",
        "odfpy"
    ]
    
    success_count = 0
    total_count = len(packages)
    
    for package in packages:
        print(f"\n📦 正在安装 {package}...")
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 安装结果: {success_count}/{total_count} 个包安装成功")
    
    if success_count == total_count:
        print("\n🎉 所有依赖包安装完成!")
        print("现在可以运行Excel修复脚本了。")
        print("\n使用方法:")
        print("1. 运行通用脚本: python scripts/fix_corrupted_excel.py '文件路径'")
        print("2. 运行专用脚本: python scripts/fix_202208_excel.py")
    else:
        print("\n⚠️ 部分包安装失败，请手动安装失败的包。")

if __name__ == "__main__":
    main() 