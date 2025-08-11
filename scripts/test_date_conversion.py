#!/usr/bin/env python3
"""
测试新加坡日期转换功能
"""

import pandas as pd
import sys
import os
from pathlib import Path

print("开始执行测试脚本...")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"项目根目录: {project_root}")
print(f"Python路径: {sys.path[:3]}")

try:
    from App.utils.Invoice import CountHid
    print("成功导入 CountHid 类")
except Exception as e:
    print(f"导入 CountHid 失败: {e}")
    sys.exit(1)

def test_singapore_date_conversion():
    """测试新加坡日期转换功能"""
    print("测试新加坡日期转换功能")
    print("=" * 50)
    
    # 创建测试实例
    booking_path = "E:\\MyProject\\MyTravelWork\\MyTravelPanel\\资源\\账单\\BOOKING"
    count = CountHid(booking_path)
    
    # 测试数据
    test_dates = [
        "2029/7/25",    # 应该转换为 2029-07-25
        "29/7/25",      # 应该转换为 2029-07-25 (年份+2000)
        "2025/12/31",   # 应该转换为 2025-12-31
        "25/12/31",     # 应该转换为 2025-12-31 (年份+2000)
        "2024/1/1",     # 应该转换为 2024-01-01
        "24/1/1",       # 应该转换为 2024-01-01 (年份+2000)
        "2023/6/15",    # 应该转换为 2023-06-15
        "23/6/15",      # 应该转换为 2023-06-15 (年份+2000)
        "",             # 空值
        None,           # None值
        "invalid_date", # 无效日期
        "2025-01-15",  # 标准格式
        "2025/01/15",  # 标准格式
    ]
    
    print("原始日期 -> 转换后日期")
    print("-" * 50)
    
    for test_date in test_dates:
        converted = count._convert_singapore_date(test_date)
        if pd.isna(converted):
            print(f"{test_date} -> NaT (无效日期)")
        else:
            print(f"{test_date} -> {converted.strftime('%Y-%m-%d')}")
    
    print("\n" + "=" * 50)
    print("测试完成")

def test_with_real_data():
    """使用真实数据测试"""
    print("\n使用真实数据测试日期转换")
    print("=" * 50)
    
    try:
        booking_path = "E:\\MyProject\\MyTravelWork\\MyTravelPanel\\资源\\账单\\BOOKING"
        count = CountHid(booking_path)
        
        # 读取数据并测试日期转换
        complete_month = count._get_complete_month()
        print(f"完成月份: {complete_month}")
        
        inv = count.read_all_inv(complete_month)
        hid = count.read_all_hid(complete_month)
        
        print(f"\nInvoice数据形状: {inv.shape}")
        if not inv.empty:
            print("Invoice数据列名:", list(inv.columns))
            # 检查日期列
            date_cols = ['order_date', 'travel_date', 'created_date']
            for col in date_cols:
                if col in inv.columns:
                    print(f"\n{col} 列的前5个值:")
                    print(inv[col].head())
        
        print(f"\nHID数据形状: {hid.shape}")
        if not hid.empty:
            print("HID数据列名:", list(hid.columns))
            # 检查日期列
            date_cols = ['order_date', 'travel_date', 'created_date']
            for col in date_cols:
                if col in hid.columns:
                    print(f"\n{col} 列的前5个值:")
                    print(hid[col].head())
        
    except Exception as e:
        print(f"测试过程中出错: {e}")

if __name__ == "__main__":
    test_singapore_date_conversion()
    test_with_real_data() 