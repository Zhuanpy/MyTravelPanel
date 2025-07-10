#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试批量报表对比功能修复
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
    
    # 创建测试数据
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
    
    # 创建Excel文件
    df_a = pd.DataFrame(test_data_a)
    df_b = pd.DataFrame(test_data_b)
    
    file_a_path = os.path.join(folder_a_dir, '2024-01_report.xlsx')
    file_b_path = os.path.join(folder_b_dir, '2024-01_report.xlsx')
    
    df_a.to_excel(file_a_path, index=False)
    df_b.to_excel(file_b_path, index=False)
    
    print(f"测试文件已创建:")
    print(f"文件夹A: {folder_a_dir}")
    print(f"文件夹B: {folder_b_dir}")
    
    return folder_a_dir, folder_b_dir

def test_batch_comparer():
    """测试批量报表对比功能"""
    print("\n=== 测试批量报表对比功能修复 ===")
    
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
        
        for filename in os.listdir(folder_b_dir):
            if filename.lower().endswith(('.xlsx', '.xls', '.csv')):
                filepath = os.path.join(folder_b_dir, filename)
                folder_b_files.append(MockFile(filepath))
        
        print(f"文件夹A文件数量: {len(folder_a_files)}")
        print(f"文件夹B文件数量: {len(folder_b_files)}")
        
        # 创建批量对比器
        comparer = BatchReportComparer('order_report')
        
        # 执行批量对比
        print("\n执行批量对比...")
        results = comparer.compare_reports_by_filename(folder_a_files, folder_b_files)
        
        # 显示结果
        print("\n=== 批量对比结果 ===")
        print(f"汇总信息: {results['summary']}")
        print(f"差异数量: {len(results['differences'])}")
        
        if results['differences']:
            print("\n详细差异:")
            for i, diff in enumerate(results['differences'][:5]):  # 只显示前5个
                print(f"  {i+1}. {diff}")
        
        # 测试生成Excel报告
        print("\n测试生成Excel报告...")
        excel_path = comparer.generate_excel_report_new(results)
        if excel_path:
            print(f"Excel报告已生成: {excel_path}")
        else:
            print("Excel报告生成失败")
        
        print("\n✅ 批量对比功能修复测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_comparer() 