#!/usr/bin/env python3
"""
简单的CSV文件检查工具
"""

import pandas as pd
import os

def check_csv_file(csv_file):
    """检查单个CSV文件"""
    
    print(f"\n🔍 检查文件: {csv_file}")
    
    try:
        # 读取CSV
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        print(f"📊 数据信息:")
        print(f"   行数: {len(df)}")
        print(f"   列数: {len(df.columns)}")
        print(f"   列名: {list(df.columns)}")
        
        # 检查每列的数据类型和样本
        print(f"\n📋 列详细信息:")
        for col in df.columns:
            sample_values = df[col].dropna().head(3)
            print(f"   {col}: {df[col].dtype} - 样本: {list(sample_values)}")
        
        # 检查空值
        print(f"\n🔍 空值检查:")
        for col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                print(f"   {col}: {null_count} 个空值")
        
        return True
        
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return False

def main():
    """主函数"""
    
    # 检查CSV目录
    csv_dir = r"E:\DATA\20250725\csv_exports"
    
    if not os.path.exists(csv_dir):
        print(f"❌ 目录不存在: {csv_dir}")
        return
    
    # 获取所有CSV文件
    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"❌ 未找到CSV文件")
        return
    
    print(f"找到 {len(csv_files)} 个CSV文件")
    
    # 检查每个文件
    for csv_file in csv_files:
        file_path = os.path.join(csv_dir, csv_file)
        check_csv_file(file_path)

if __name__ == "__main__":
    main() 