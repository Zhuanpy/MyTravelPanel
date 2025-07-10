#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量报表对比功能测试脚本

测试BatchReportComparer类的各项功能
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def create_test_files():
    """创建测试用的报表文件"""
    print("=== 创建测试文件 ===")
    
    # 创建测试数据
    test_data_a = {
        'hid': ['HID001', 'HID002', 'HID003', 'HID004'],
        'customer_name': ['张三', '李四', '王五', '赵六'],
        'order_date': ['2024-01-15', '2024-01-16', '2024-01-17', '2024-01-18'],
        'product_name': ['泰国游', '新加坡游', '马来西亚游', '印尼游'],
        'travel_date': ['2024-02-01', '2024-02-02', '2024-02-03', '2024-02-04'],
        'selling_price': [1000, 1200, 800, 1500],
        'cost_price': [700, 900, 600, 1100],
        'profit': [300, 300, 200, 400],
        'balance': [0, 0, 0, 0],
        'created_by': ['user1', 'user1', 'user2', 'user2'],
        'approved_by': ['admin', 'admin', 'admin', 'admin']
    }
    
    test_data_b = {
        'hid': ['HID001', 'HID002', 'HID003', 'HID005'],  # HID004缺失，HID005新增
        'customer_name': ['张三', '李四', '王五', '钱七'],
        'order_date': ['2024-01-15', '2024-01-16', '2024-01-17', '2024-01-19'],
        'product_name': ['泰国游', '新加坡游', '马来西亚游', '越南游'],
        'travel_date': ['2024-02-01', '2024-02-02', '2024-02-03', '2024-02-05'],
        'selling_price': [1000, 1200, 800, 1300],
        'cost_price': [700, 900, 600, 900],
        'profit': [300, 350, 200, 400],  # HID002的利润不同
        'balance': [0, 0, 0, 0],
        'created_by': ['user1', 'user1', 'user2', 'user3'],
        'approved_by': ['admin', 'admin', 'admin', 'admin']
    }
    
    # 创建测试目录
    test_dir = 'test_batch_files'
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    folder_a_dir = os.path.join(test_dir, 'folder_a')
    folder_b_dir = os.path.join(test_dir, 'folder_b')
    
    for dir_path in [folder_a_dir, folder_b_dir]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    # 创建文件夹A的文件
    df_a = pd.DataFrame(test_data_a)
    file_a_path = os.path.join(folder_a_dir, '2024-01_report.xlsx')
    df_a.to_excel(file_a_path, index=False)
    print(f"✅ 创建文件A: {file_a_path}")
    
    # 创建文件夹B的文件
    df_b = pd.DataFrame(test_data_b)
    file_b_path = os.path.join(folder_b_dir, '2024-01_report.xlsx')
    df_b.to_excel(file_b_path, index=False)
    print(f"✅ 创建文件B: {file_b_path}")
    
    return folder_a_dir, folder_b_dir

def test_batch_comparer():
    """测试批量报表对比功能"""
    print("\n=== 测试批量报表对比功能 ===")
    
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
        results = comparer.compare_reports_by_date(folder_a_files, folder_b_files)
        
        # 显示结果
        print("\n=== 批量对比结果 ===")
        print(f"汇总信息: {results['summary']}")
        print(f"差异报表数量: {len(results['differences'])}")
        print(f"缺失HID数量: {len(results['missing_hids'])}")
        
        if results['differences']:
            print("\n差异报表详情:")
            for diff in results['differences']:
                print(f"  - {diff['report_name']}: {diff['difference_count']}个差异")
        
        if results['missing_hids']:
            print(f"\n缺失HID: {', '.join(results['missing_hids'])}")
        
        # 生成Excel报告
        print("\n生成Excel报告...")
        report_path = comparer.generate_excel_report(results)
        if report_path:
            print(f"✅ Excel报告已生成: {report_path}")
        else:
            print("❌ Excel报告生成失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_date_extraction():
    """测试日期提取功能"""
    print("\n=== 测试日期提取功能 ===")
    
    try:
        from App.utils.report_utils import BatchReportComparer
        
        comparer = BatchReportComparer()
        
        test_filenames = [
            '2024-01_report.xlsx',
            '2024_02_report.xlsx',
            '202403_report.xlsx',
            'report_2024-04.xlsx',
            'no_date_report.xlsx'
        ]
        
        for filename in test_filenames:
            date = comparer.extract_date_from_filename(filename)
            print(f"文件名: {filename} -> 提取日期: {date}")
        
        return True
        
    except Exception as e:
        print(f"❌ 日期提取测试失败: {e}")
        return False

def test_file_matching():
    """测试文件匹配功能"""
    print("\n=== 测试文件匹配功能 ===")
    
    try:
        from App.utils.report_utils import BatchReportComparer
        
        comparer = BatchReportComparer()
        
        # 模拟文件对象
        class MockFile:
            def __init__(self, filename):
                self.filename = filename
        
        test_pairs = [
            (MockFile('2024-01_report.xlsx'), MockFile('2024-01_report.xlsx')),
            (MockFile('2024-01_report.xlsx'), MockFile('2024-01_report.xls')),
            (MockFile('report_a.xlsx'), MockFile('report_b.xlsx')),
        ]
        
        for file_a, file_b in test_pairs:
            is_match = comparer._files_match(file_a, file_b)
            print(f"文件A: {file_a.filename}, 文件B: {file_b.filename} -> 匹配: {is_match}")
        
        return True
        
    except Exception as e:
        print(f"❌ 文件匹配测试失败: {e}")
        return False

def cleanup_test_files():
    """清理测试文件"""
    print("\n=== 清理测试文件 ===")
    
    test_dir = 'test_batch_files'
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
        print(f"✅ 已删除测试目录: {test_dir}")

def main():
    """主测试函数"""
    print("🚀 开始批量报表对比功能测试")
    
    tests = [
        test_date_extraction,
        test_file_matching,
        test_batch_comparer
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_func.__name__} 测试通过")
            else:
                print(f"❌ {test_func.__name__} 测试失败")
        except Exception as e:
            print(f"❌ {test_func.__name__} 测试异常: {e}")
    
    # 清理测试文件
    cleanup_test_files()
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，请检查代码")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 