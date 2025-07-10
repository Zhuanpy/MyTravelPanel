#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试批量报表对比业务逻辑
"""

import os
import sys
import pandas as pd
import tempfile

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_files():
    """创建测试文件"""
    print("创建测试文件...")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    folder_a_dir = os.path.join(temp_dir, 'folder_a')
    folder_b_dir = os.path.join(temp_dir, 'folder_b')
    
    os.makedirs(folder_a_dir, exist_ok=True)
    os.makedirs(folder_b_dir, exist_ok=True)
    
    # 创建测试数据 - 有差异的数据
    test_data_a = {
        'hid': ['HID001', 'HID002', 'HID003', 'HID004'],
        'customer_name': ['客户A', '客户B', '客户C', '客户D'],
        'order_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
        'product_name': ['产品A', '产品B', '产品C', '产品D'],
        'travel_date': ['2024-02-01', '2024-02-02', '2024-02-03', '2024-02-04'],
        'selling_price': [1000, 2000, 3000, 4000],
        'cost_price': [800, 1600, 2400, 3200],
        'profit': [200, 400, 600, 800],  # 有差异
        'balance': [0, 0, 0, 0],
        'created_by': ['用户A', '用户B', '用户C', '用户D'],
        'approved_by': ['审批A', '审批B', '审批C', '审批D']
    }
    
    test_data_b = {
        'hid': ['HID001', 'HID002', 'HID003', 'HID005'],  # HID004缺失，HID005新增
        'customer_name': ['客户A', '客户B', '客户C', '客户E'],
        'order_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-05'],
        'product_name': ['产品A', '产品B', '产品C', '产品E'],
        'travel_date': ['2024-02-01', '2024-02-02', '2024-02-03', '2024-02-05'],
        'selling_price': [1000, 2000, 3000, 5000],
        'cost_price': [800, 1600, 2400, 4000],
        'profit': [200, 450, 600, 1000],  # HID002有差异，HID005新增
        'balance': [0, 0, 0, 0],
        'created_by': ['用户A', '用户B', '用户C', '用户E'],
        'approved_by': ['审批A', '审批B', '审批C', '审批E']
    }
    
    # 创建Excel文件 - 使用相同的文件名
    df_a = pd.DataFrame(test_data_a)
    df_b = pd.DataFrame(test_data_b)
    
    file_a_path = os.path.join(folder_a_dir, '2024-01_report.xlsx')
    file_b_path = os.path.join(folder_b_dir, '2024-01_report.xlsx')
    
    df_a.to_excel(file_a_path, index=False)
    df_b.to_excel(file_b_path, index=False)
    
    print(f"测试文件已创建:")
    print(f"文件夹A: {folder_a_dir}")
    print(f"文件夹B: {folder_b_dir}")
    print(f"文件A: {file_a_path}")
    print(f"文件B: {file_b_path}")
    
    return folder_a_dir, folder_b_dir

def debug_batch_comparer():
    """调试批量报表对比功能"""
    print("\n=== 调试批量报表对比功能 ===")
    
    try:
        from App.utils.report_utils import BatchReportComparer
        
        # 创建测试文件
        folder_a_dir, folder_b_dir = create_test_files()
        
        # 模拟文件对象
        class MockFile:
            def __init__(self, filepath):
                self.filepath = filepath
                self.filename = os.path.basename(filepath)
            
            def __enter__(self):
                return open(self.filepath, 'rb')
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        
        # 获取文件夹中的文件
        folder_a_files = []
        folder_b_files = []
        
        for filename in os.listdir(folder_a_dir):
            if filename.lower().endswith(('.xlsx', '.xls', '.csv')):
                filepath = os.path.join(folder_a_dir, filename)
                folder_a_files.append(MockFile(filepath))
                print(f"文件夹A文件: {filename}")
        
        for filename in os.listdir(folder_b_dir):
            if filename.lower().endswith(('.xlsx', '.xls', '.csv')):
                filepath = os.path.join(folder_b_dir, filename)
                folder_b_files.append(MockFile(filepath))
                print(f"文件夹B文件: {filename}")
        
        print(f"\n文件夹A文件数量: {len(folder_a_files)}")
        print(f"文件夹B文件数量: {len(folder_b_files)}")
        
        # 创建批量对比器
        comparer = BatchReportComparer('order_report')
        
        # 调试文件分组
        print("\n=== 调试文件分组 ===")
        grouped_a = comparer.group_files_by_name(folder_a_files)
        grouped_b = comparer.group_files_by_name(folder_b_files)
        
        print("文件夹A分组结果:")
        for key, files in grouped_a.items():
            print(f"  Key: '{key}' -> {len(files)} 个文件")
            for file in files:
                print(f"    - {file.filename}")
        
        print("\n文件夹B分组结果:")
        for key, files in grouped_b.items():
            print(f"  Key: '{key}' -> {len(files)} 个文件")
            for file in files:
                print(f"    - {file.filename}")
        
        # 调试文件读取
        print("\n=== 调试文件读取 ===")
        for file in folder_a_files:
            print(f"\n读取文件A: {file.filename}")
            df_a = comparer.read_report_file(file)
            if df_a is not None:
                print(f"  数据形状: {df_a.shape}")
                print(f"  列名: {list(df_a.columns)}")
                print(f"  HID列表: {list(df_a['hid'])}")
                print(f"  利润列表: {list(df_a['profit'])}")
            else:
                print("  读取失败")
        
        for file in folder_b_files:
            print(f"\n读取文件B: {file.filename}")
            df_b = comparer.read_report_file(file)
            if df_b is not None:
                print(f"  数据形状: {df_b.shape}")
                print(f"  列名: {list(df_b.columns)}")
                print(f"  HID列表: {list(df_b['hid'])}")
                print(f"  利润列表: {list(df_b['profit'])}")
            else:
                print("  读取失败")
        
        # 执行批量对比
        print("\n=== 执行批量对比 ===")
        results = comparer.compare_reports_by_filename(folder_a_files, folder_b_files)
        
        # 显示结果
        print("\n=== 批量对比结果 ===")
        print(f"汇总信息: {results['summary']}")
        print(f"差异数量: {len(results['differences'])}")
        
        if results['differences']:
            print("\n详细差异:")
            for i, diff in enumerate(results['differences']):
                print(f"  {i+1}. {diff}")
        else:
            print("\n❌ 没有检测到差异！")
        
        print("\n✅ 调试完成！")
        
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_batch_comparer() 