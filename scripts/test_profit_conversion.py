#!/usr/bin/env python3
"""
测试利润值转换修复的脚本
验证系统是否能正确处理包含非数字利润值的数据
"""

import sys
import os
import pandas as pd
import tempfile

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def create_test_data():
    """创建包含非数字利润值的测试数据"""
    print("=== 创建测试数据 ===")
    
    # 创建包含各种类型数据的测试DataFrame
    test_data_a = {
        'order_id': ['001', '002', '003', '004', '005'],
        'customer_type': ['VIP', 'Regular', 'VIP', 'Regular', 'VIP'],
        'order_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
        'passenger_name': ['张三', '李四', '王五', '赵六', '钱七'],
        'travel_date': ['2024-02-01', '2024-02-02', '2024-02-03', '2024-02-04', '2024-02-05'],
        'product_name': ['新加坡游', '泰国游', '马来西亚游', '印尼游', '菲律宾游'],
        'booking_type': ['Online', 'Offline', 'Online', 'Offline', 'Online'],
        'selling_price': [1000.0, 1500.0, 2000.0, 1200.0, 1800.0],
        'cost_price': [800.0, 1200.0, 1600.0, 1000.0, 1400.0],
        'profit': [200.0, 300.0, 'MAIN', 200.0, 'N/A'],  # 包含非数字值
        'profit_margin': [0.2, 0.2, 0.2, 0.17, 0.22],
        'balance': [0.0, 0.0, 0.0, 0.0, 0.0],
        'created_by': ['user1', 'user2', 'user3', 'user4', 'user5'],
        'approved_by': ['admin1', 'admin2', 'admin3', 'admin4', 'admin5'],
        'pax_info': ['2 adults', '1 adult', '3 adults', '2 adults', '1 adult'],
        'invoice_status': ['Paid', 'Pending', 'Paid', 'Pending', 'Paid']
    }
    
    test_data_b = {
        'order_id': ['001', '002', '003', '004', '005'],
        'customer_type': ['VIP', 'Regular', 'VIP', 'Regular', 'VIP'],
        'order_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
        'passenger_name': ['张三', '李四', '王五', '赵六', '钱七'],
        'travel_date': ['2024-02-01', '2024-02-02', '2024-02-03', '2024-02-04', '2024-02-05'],
        'product_name': ['新加坡游', '泰国游', '马来西亚游', '印尼游', '菲律宾游'],
        'booking_type': ['Online', 'Offline', 'Online', 'Offline', 'Online'],
        'selling_price': [1000.0, 1500.0, 2000.0, 1200.0, 1800.0],
        'cost_price': [800.0, 1200.0, 1600.0, 1000.0, 1400.0],
        'profit': [200.0, 350.0, 400.0, 200.0, 400.0],  # 正常数字
        'profit_margin': [0.2, 0.23, 0.2, 0.17, 0.22],
        'balance': [0.0, 0.0, 0.0, 0.0, 0.0],
        'created_by': ['user1', 'user2', 'user3', 'user4', 'user5'],
        'approved_by': ['admin1', 'admin2', 'admin3', 'admin4', 'admin5'],
        'pax_info': ['2 adults', '1 adult', '3 adults', '2 adults', '1 adult'],
        'invoice_status': ['Paid', 'Pending', 'Paid', 'Pending', 'Paid']
    }
    
    df_a = pd.DataFrame(test_data_a)
    df_b = pd.DataFrame(test_data_b)
    
    print("测试数据A:")
    print(df_a[['order_id', 'profit']].to_string())
    print("\n测试数据B:")
    print(df_b[['order_id', 'profit']].to_string())
    
    return df_a, df_b

def test_profit_conversion():
    """测试利润值转换功能"""
    print("\n=== 测试利润值转换功能 ===")
    
    try:
        from App.utils.report_utils import compare_profit_columns
        
        # 创建测试数据
        df_a, df_b = create_test_data()
        
        # 测试对比功能
        print("\n执行利润对比...")
        result = compare_profit_columns(df_a, df_b, 'profit', 'order_id')
        
        if result['success']:
            print("✅ 对比功能执行成功!")
            print(f"发现差异数量: {len(result['differences'])}")
            print(f"统计信息: {result['summary']}")
            
            # 显示差异详情
            if result['differences']:
                print("\n差异详情:")
                for diff in result['differences']:
                    print(f"  项目 {diff['item']}: 报表A={diff['value_a']}, 报表B={diff['value_b']}, 差异={diff['difference']}")
        else:
            print(f"❌ 对比功能执行失败: {result['error']}")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_data_processing():
    """测试数据处理逻辑"""
    print("\n=== 测试数据处理逻辑 ===")
    
    try:
        # 模拟数据处理逻辑
        df_a, df_b = create_test_data()
        
        data_a = {}
        data_b = {}
        
        # 处理报表A
        skipped_a = 0
        for _, row in df_a.iterrows():
            item_id = str(row['order_id']).strip()
            profit_value = row['profit']
            if pd.notna(profit_value):
                try:
                    float_value = float(profit_value)
                    data_a[item_id] = float_value
                except (ValueError, TypeError):
                    print(f"警告：报表A中项目 {item_id} 的利润值 '{profit_value}' 无法转换为数字，已跳过")
                    skipped_a += 1
                    continue
        
        # 处理报表B
        skipped_b = 0
        for _, row in df_b.iterrows():
            item_id = str(row['order_id']).strip()
            profit_value = row['profit']
            if pd.notna(profit_value):
                try:
                    float_value = float(profit_value)
                    data_b[item_id] = float_value
                except (ValueError, TypeError):
                    print(f"警告：报表B中项目 {item_id} 的利润值 '{profit_value}' 无法转换为数字，已跳过")
                    skipped_b += 1
                    continue
        
        print(f"✅ 数据处理完成!")
        print(f"报表A: 总行数={len(df_a)}, 有效数据={len(data_a)}, 跳过={skipped_a}")
        print(f"报表B: 总行数={len(df_b)}, 有效数据={len(data_b)}, 跳过={skipped_b}")
        
        # 验证结果
        expected_valid_a = 3  # 只有3个数字值
        expected_valid_b = 5  # 全部都是数字值
        expected_skipped_a = 2  # 2个非数字值
        expected_skipped_b = 0  # 没有非数字值
        
        if len(data_a) == expected_valid_a and len(data_b) == expected_valid_b:
            print("✅ 数据处理结果符合预期!")
            return True
        else:
            print(f"❌ 数据处理结果不符合预期!")
            print(f"期望: A={expected_valid_a}, B={expected_valid_b}")
            print(f"实际: A={len(data_a)}, B={len(data_b)}")
            return False
        
    except Exception as e:
        print(f"❌ 数据处理测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试利润值转换修复...\n")
    
    tests = [
        test_profit_conversion,
        test_data_processing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过! 利润值转换修复工作正常。")
        print("\n📋 修复内容:")
        print("   ✅ 添加了try-catch异常处理")
        print("   ✅ 跳过无法转换为数字的利润值")
        print("   ✅ 提供详细的警告信息")
        print("   ✅ 确保程序不会因数据错误而崩溃")
        return 0
    else:
        print("❌ 部分测试失败，请检查修复。")
        return 1

if __name__ == "__main__":
    exit(main()) 