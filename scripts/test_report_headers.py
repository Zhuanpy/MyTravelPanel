#!/usr/bin/env python3
"""
测试报表表头配置的脚本
验证config中的表头配置和工具函数是否正常工作
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_config_headers():
    """测试Config中的表头配置"""
    print("=== 测试Config中的表头配置 ===")
    
    try:
        from App.config import Config
        
        # 测试获取表头列表
        print("\n1. 测试获取表头列表:")
        headers = Config.get_header_list('order_report')
        print(f"   标准订单报表表头: {headers}")
        print(f"   字段数量: {len(headers)}")
        
        # 测试获取表头字符串
        print("\n2. 测试获取表头字符串:")
        header_string = Config.get_header_string('order_report')
        print(f"   表头字符串: {header_string}")
        
        # 测试简化表头
        print("\n3. 测试简化表头:")
        simple_headers = Config.get_header_list('simple_order_report')
        print(f"   简化订单报表表头: {simple_headers}")
        print(f"   字段数量: {len(simple_headers)}")
        
        # 测试财务报表表头
        print("\n4. 测试财务报表表头:")
        financial_headers = Config.get_header_list('financial_report')
        print(f"   财务报表表头: {financial_headers}")
        print(f"   字段数量: {len(financial_headers)}")
        
        # 测试错误处理
        print("\n5. 测试错误处理:")
        try:
            Config.get_header_list('invalid_type')
        except ValueError as e:
            print(f"   正确捕获错误: {e}")
        
        print("\n✅ Config表头配置测试通过!")
        
    except Exception as e:
        print(f"❌ Config表头配置测试失败: {e}")
        return False
    
    return True

def test_report_utils():
    """测试report_utils工具函数"""
    print("\n=== 测试report_utils工具函数 ===")
    
    try:
        from App.utils.report_utils import (
            get_report_headers,
            get_report_headers_string,
            compare_profit_columns,
            add_comparison_column
        )
        import pandas as pd
        
        # 测试获取表头
        print("\n1. 测试获取表头:")
        headers = get_report_headers('order_report')
        print(f"   获取的表头: {headers}")
        
        header_string = get_report_headers_string('order_report')
        print(f"   获取的表头字符串: {header_string}")
        
        # 测试利润列对比
        print("\n2. 测试利润列对比:")
        
        # 创建测试数据
        data_a = {
            'order_id': ['001', '002', '003'],
            'profit': [100.0, 200.0, 300.0]
        }
        data_b = {
            'order_id': ['001', '002', '003'],
            'profit': [100.0, 250.0, 300.0]  # 002的利润不同
        }
        
        df_a = pd.DataFrame(data_a)
        df_b = pd.DataFrame(data_b)
        
        result = compare_profit_columns(df_a, df_b, 'profit', 'order_id')
        print(f"   对比结果: {result}")
        
        if result['success']:
            print(f"   发现 {result['differences']} 个差异")
            print(f"   统计信息: {result['summary']}")
        
        # 测试添加对比列
        print("\n3. 测试添加对比列:")
        df_a_with_col, df_b_with_col = add_comparison_column(df_a, df_b, 'profit', 'order_id')
        print(f"   报表A添加对比列后: {df_a_with_col.columns.tolist()}")
        print(f"   报表B添加对比列后: {df_b_with_col.columns.tolist()}")
        
        print("\n✅ report_utils工具函数测试通过!")
        
    except Exception as e:
        print(f"❌ report_utils工具函数测试失败: {e}")
        return False
    
    return True

def test_integration():
    """测试集成功能"""
    print("\n=== 测试集成功能 ===")
    
    try:
        from App.config import Config
        from App.utils.report_utils import get_report_headers_string
        
        # 测试Config和工具函数的集成
        config_headers = Config.get_header_string('order_report')
        utils_headers = get_report_headers_string('order_report')
        
        if config_headers == utils_headers:
            print("✅ Config和工具函数集成测试通过!")
            print(f"   表头一致: {config_headers}")
        else:
            print("❌ Config和工具函数集成测试失败!")
            print(f"   Config表头: {config_headers}")
            print(f"   工具函数表头: {utils_headers}")
            return False
        
    except Exception as e:
        print(f"❌ 集成功能测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("开始测试报表表头配置系统...\n")
    
    tests = [
        test_config_headers,
        test_report_utils,
        test_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过! 表头配置系统工作正常。")
        return 0
    else:
        print("❌ 部分测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    exit(main()) 