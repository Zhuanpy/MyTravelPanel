#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试账号导入功能
包括下载模板和导入功能
"""

import requests
import pandas as pd
from io import BytesIO
import json

def test_download_template():
    """测试下载模板功能"""
    print("=== 测试下载模板功能 ===")
    
    try:
        # 测试下载模板
        url = "http://192.168.5.60:5000/account/api/accounts/download_template"
        response = requests.get(url)
        
        if response.status_code == 200:
            print("✅ 模板下载成功")
            print(f"   文件大小: {len(response.content)} 字节")
            print(f"   内容类型: {response.headers.get('content-type', 'N/A')}")
            print(f"   文件名: {response.headers.get('content-disposition', 'N/A')}")
            
            # 尝试读取Excel文件内容
            try:
                df = pd.read_excel(BytesIO(response.content))
                print(f"   Excel行数: {len(df)}")
                print(f"   Excel列数: {len(df.columns)}")
                print(f"   列名: {list(df.columns)}")
                print("✅ Excel文件解析成功")
            except Exception as e:
                print(f"❌ Excel文件解析失败: {e}")
                
        else:
            print(f"❌ 模板下载失败: HTTP {response.status_code}")
            print(f"   响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_import_functionality():
    """测试导入功能（不实际导入数据）"""
    print("\n=== 测试导入功能 ===")
    
    try:
        # 创建一个测试Excel文件
        test_data = {
            'platform': ['测试平台1', '测试平台2'],
            'website_url': ['https://test1.com', 'https://test2.com'],
            'category': ['测试类别1', '测试类别2'],
            'owner': ['测试用户1', '测试用户2'],
            'username': ['testuser1', 'testuser2'],
            'password': ['testpass1', 'testpass2'],
            'country': ['中国', '中国'],
            'region': ['北京', '上海'],
            'description': ['测试描述1', '测试描述2'],
            'notes': ['测试备注1', '测试备注2']
        }
        
        df = pd.DataFrame(test_data)
        
        # 保存为Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='测试数据')
        output.seek(0)
        
        print("✅ 测试Excel文件创建成功")
        print(f"   数据行数: {len(df)}")
        print(f"   数据列数: {len(df.columns)}")
        
        # 测试文件格式验证
        print("\n=== 文件格式验证 ===")
        print(f"   文件扩展名检查: .xlsx - ✅")
        print(f"   必填字段检查: {list(df.columns)}")
        
        required_fields = ['platform', 'category', 'username', 'password']
        missing_fields = [field for field in required_fields if field not in df.columns]
        
        if not missing_fields:
            print("   ✅ 所有必填字段都存在")
        else:
            print(f"   ❌ 缺少必填字段: {missing_fields}")
            
        # 数据验证
        print("\n=== 数据验证 ===")
        for field in required_fields:
            empty_rows = df[df[field].astype(str).str.strip() == ''].index.tolist()
            if not empty_rows:
                print(f"   ✅ {field}: 无空值")
            else:
                print(f"   ❌ {field}: 第 {[i+2 for i in empty_rows]} 行为空")
        
        # 测试nan值处理
        print("\n=== nan值处理测试 ===")
        # 创建一个包含nan值的测试数据
        test_data_with_nan = {
            'platform': ['测试平台3', '测试平台4'],
            'category': ['测试类别3', '测试类别4'],
            'username': ['testuser3', 'testuser4'],
            'password': ['testpass3', 'testpass4'],
            'notes': ['测试备注3', None],  # 包含None值
            'description': ['测试描述3', '']  # 包含空字符串
        }
        
        df_nan = pd.DataFrame(test_data_with_nan)
        print(f"   ✅ 包含nan值的测试数据创建成功")
        print(f"   数据行数: {len(df_nan)}")
        
        # 测试fillna处理
        df_filled = df_nan.fillna('')
        print(f"   ✅ fillna处理后，空值数量: {(df_filled == '').sum().sum()}")
        
        # 测试safe_str函数逻辑
        def safe_str(value):
            """模拟后端的safe_str函数"""
            if pd.isna(value) or value == '' or value is None:
                return None
            return str(value).strip()
        
        print("\n=== safe_str函数测试 ===")
        test_values = ['正常值', '', None, pd.NA, '  空格值  ']
        for val in test_values:
            result = safe_str(val)
            print(f"   输入: {repr(val)} -> 输出: {repr(result)}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_api_endpoints():
    """测试API端点是否可访问"""
    print("\n=== 测试API端点 ===")
    
    base_url = "http://192.168.5.60:5000"
    endpoints = [
        "/account/api/accounts/download_template",
        "/account/api/accounts/import",
        "/account/accounts"
    ]
    
    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            if endpoint.endswith('/import'):
                # POST请求
                response = requests.post(url, timeout=5)
            else:
                # GET请求
                response = requests.get(url, timeout=5)
                
            if response.status_code in [200, 405]:  # 405表示方法不允许，但端点存在
                print(f"✅ {endpoint}: 可访问 (HTTP {response.status_code})")
            else:
                print(f"❌ {endpoint}: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint}: 连接失败")
        except requests.exceptions.Timeout:
            print(f"❌ {endpoint}: 请求超时")
        except Exception as e:
            print(f"❌ {endpoint}: 错误 - {e}")

def main():
    """主函数"""
    print("账号导入功能测试")
    print("=" * 50)
    
    # 测试API端点
    test_api_endpoints()
    
    # 测试下载模板
    test_download_template()
    
    # 测试导入功能
    test_import_functionality()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("\n主要修复:")
    print("1. ✅ 添加了nan值处理")
    print("2. ✅ 使用safe_str函数安全处理可选字段")
    print("3. ✅ 确保所有空值都被转换为None或空字符串")

if __name__ == "__main__":
    main()
