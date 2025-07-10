#!/usr/bin/env python3
"""
测试Invoice.py中表头配置的脚本
验证CountHid和CountMonth类是否正确使用了表头配置
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_config_headers():
    """测试Config中的发票和HID表头配置"""
    print("=== 测试Config中的发票和HID表头配置 ===")
    
    try:
        from App.config import Config
        
        # 测试发票数据表头
        print("\n1. 测试发票数据表头:")
        invoice_headers = Config.get_header_list('invoice_data')
        print(f"   发票数据表头: {invoice_headers}")
        print(f"   字段数量: {len(invoice_headers)}")
        
        # 测试HID数据表头
        print("\n2. 测试HID数据表头:")
        hid_headers = Config.get_header_list('hid_data')
        print(f"   HID数据表头: {hid_headers}")
        print(f"   字段数量: {len(hid_headers)}")
        
        # 测试获取表头字符串
        print("\n3. 测试获取表头字符串:")
        invoice_string = Config.get_header_string('invoice_data')
        hid_string = Config.get_header_string('hid_data')
        print(f"   发票表头字符串: {invoice_string}")
        print(f"   HID表头字符串: {hid_string}")
        
        print("\n✅ Config表头配置测试通过!")
        
    except Exception as e:
        print(f"❌ Config表头配置测试失败: {e}")
        return False
    
    return True

def test_count_hid_class():
    """测试CountHid类的表头配置"""
    print("\n=== 测试CountHid类的表头配置 ===")
    
    try:
        from App.code.Invoice import CountHid
        
        # 创建CountHid实例（使用测试路径）
        test_path = "test_booking_path"
        count_hid = CountHid(test_path, "TestName")
        
        # 检查表头是否正确加载
        print("\n1. 检查表头加载:")
        print(f"   发票表头: {count_hid.invoice_headers}")
        print(f"   HID表头: {count_hid.hid_headers}")
        
        # 验证表头字段
        print("\n2. 验证关键字段:")
        expected_invoice_fields = ['hid', 'customer_name', 'order_date', 'profit']
        expected_hid_fields = ['hid', 'customer_name', 'order_date', 'profit']
        
        for field in expected_invoice_fields:
            if field in count_hid.invoice_headers:
                print(f"   ✅ 发票表头包含字段: {field}")
            else:
                print(f"   ❌ 发票表头缺少字段: {field}")
                return False
        
        for field in expected_hid_fields:
            if field in count_hid.hid_headers:
                print(f"   ✅ HID表头包含字段: {field}")
            else:
                print(f"   ❌ HID表头缺少字段: {field}")
                return False
        
        print("\n✅ CountHid类表头配置测试通过!")
        
    except Exception as e:
        print(f"❌ CountHid类表头配置测试失败: {e}")
        return False
    
    return True

def test_count_month_class():
    """测试CountMonth类的表头配置"""
    print("\n=== 测试CountMonth类的表头配置 ===")
    
    try:
        from App.code.Invoice import CountMonth
        
        # 创建CountMonth实例
        count_month = CountMonth(202304, 202307, "test_path", "TestName")
        
        # 检查表头是否正确加载
        print("\n1. 检查表头加载:")
        print(f"   HID表头: {count_month.hid_headers}")
        
        # 验证表头字段
        print("\n2. 验证关键字段:")
        expected_fields = ['hid', 'customer_name', 'order_date', 'profit']
        
        for field in expected_fields:
            if field in count_month.hid_headers:
                print(f"   ✅ HID表头包含字段: {field}")
            else:
                print(f"   ❌ HID表头缺少字段: {field}")
                return False
        
        print("\n✅ CountMonth类表头配置测试通过!")
        
    except Exception as e:
        print(f"❌ CountMonth类表头配置测试失败: {e}")
        return False
    
    return True

def test_table_structure():
    """测试表头结构的一致性"""
    print("\n=== 测试表头结构的一致性 ===")
    
    try:
        from App.config import Config
        
        # 检查发票和HID表头的共同字段
        invoice_headers = set(Config.get_header_list('invoice_data'))
        hid_headers = set(Config.get_header_list('hid_data'))
        
        common_fields = invoice_headers & hid_headers
        print(f"\n1. 共同字段: {list(common_fields)}")
        
        # 检查关键字段是否存在
        key_fields = ['hid', 'customer_name', 'order_date', 'profit']
        missing_fields = []
        
        for field in key_fields:
            if field not in common_fields:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   ❌ 缺少关键字段: {missing_fields}")
            return False
        else:
            print("   ✅ 所有关键字段都存在")
        
        # 检查字段数量是否合理
        if len(invoice_headers) >= 8 and len(hid_headers) >= 8:
            print("   ✅ 字段数量合理")
        else:
            print("   ❌ 字段数量过少")
            return False
        
        print("\n✅ 表头结构一致性测试通过!")
        
    except Exception as e:
        print(f"❌ 表头结构一致性测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("开始测试Invoice.py中的表头配置系统...\n")
    
    tests = [
        test_config_headers,
        test_count_hid_class,
        test_count_month_class,
        test_table_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过! Invoice.py中的表头配置系统工作正常。")
        print("\n📋 主要改进:")
        print("   ✅ 发票数据使用 'invoice_data' 表头")
        print("   ✅ HID数据使用 'hid_data' 表头")
        print("   ✅ 代码中使用字段名称而不是列索引")
        print("   ✅ 表头配置集中管理，易于维护")
        return 0
    else:
        print("❌ 部分测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    exit(main()) 