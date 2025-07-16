#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门修复 E:\Todays file\aaa\202208.xls 文件的脚本
"""

import os
import pandas as pd
import chardet
from pathlib import Path
import shutil
from datetime import datetime

def fix_202208_excel():
    """修复202208.xls文件"""
    
    # 文件路径
    file_path = r"E:\Todays file\aaa\202208.xls"
    
    print(f"开始修复文件: {file_path}")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在 - {file_path}")
        return False
    
    # 创建备份
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = r"E:\Todays file\aaa\202208_backup_" + timestamp + ".xls"
    
    try:
        shutil.copy2(file_path, backup_path)
        print(f"✅ 已创建备份文件: {backup_path}")
    except Exception as e:
        print(f"❌ 创建备份失败: {e}")
        return False
    
    # 检测文件编码
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            print(f"📊 检测到编码: {result}")
    except Exception as e:
        print(f"⚠️ 编码检测失败: {e}")
    
    # 尝试不同的读取方法
    df = None
    success_method = None
    
    # 方法1: 直接读取
    print("\n🔍 尝试方法1: 直接读取Excel...")
    try:
        df = pd.read_excel(file_path)
        success_method = "直接读取"
    except Exception as e:
        print(f"❌ 方法1失败: {e}")
    
    # 方法2: 使用openpyxl引擎
    if df is None:
        print("\n🔍 尝试方法2: 使用openpyxl引擎...")
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
            success_method = "openpyxl引擎"
        except Exception as e:
            print(f"❌ 方法2失败: {e}")
    
    # 方法3: 使用xlrd引擎
    if df is None:
        print("\n🔍 尝试方法3: 使用xlrd引擎...")
        try:
            df = pd.read_excel(file_path, engine='xlrd')
            success_method = "xlrd引擎"
        except Exception as e:
            print(f"❌ 方法3失败: {e}")
    
    # 方法4: 尝试作为CSV读取（如果是CSV格式的Excel）
    if df is None:
        print("\n🔍 尝试方法4: 作为CSV读取...")
        common_encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin1', 'cp1252']
        for encoding in common_encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                success_method = f"CSV读取 (编码: {encoding})"
                break
            except Exception as e:
                print(f"❌ CSV读取失败 (编码: {encoding}): {e}")
    
    if df is not None:
        print(f"\n✅ 成功读取文件!")
        print(f"📋 使用的方法: {success_method}")
        print(f"📊 数据形状: {df.shape}")
        print(f"📝 列名: {list(df.columns)}")
        
        # 显示前几行数据
        print("\n📄 前5行数据预览:")
        print(df.head())
        
        # 保存修复后的文件
        output_path = r"E:\Todays file\aaa\202208_fixed.xlsx"
        try:
            df.to_excel(output_path, index=False, engine='openpyxl')
            print(f"\n✅ 修复后的文件已保存: {output_path}")
            return True
        except Exception as e:
            print(f"❌ 保存修复文件失败: {e}")
            return False
    else:
        print("\n❌ 所有读取方法都失败了")
        print("💡 建议:")
        print("1. 检查文件是否损坏")
        print("2. 尝试用其他软件打开文件")
        print("3. 检查文件格式是否正确")
        return False

if __name__ == "__main__":
    print("🔧 Excel文件修复工具")
    print("=" * 50)
    
    success = fix_202208_excel()
    
    if success:
        print("\n🎉 修复完成!")
        print("请检查生成的修复文件: E:\\Todays file\\aaa\\202208_fixed.xlsx")
    else:
        print("\n💥 修复失败!")
        print("请检查备份文件和日志信息。") 