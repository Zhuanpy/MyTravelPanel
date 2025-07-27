#!/usr/bin/env python3
"""
测试签证类型管理页面中的签证详细按钮
"""

import requests
from urllib.parse import quote

def test_detail_button():
    """测试签证详细按钮的功能"""
    base_url = "http://127.0.0.1:5000"
    
    # 测试1: 访问签证类型管理页面
    print("测试1: 访问签证类型管理页面")
    try:
        response = requests.get(f"{base_url}/visa/basic/visa_type_management")
        if response.status_code == 200:
            print("✓ 签证类型管理页面加载成功")
            
            # 检查是否包含签证详细按钮
            if '签证详细' in response.text:
                print("✓ 签证详细按钮已添加")
            else:
                print("✗ 签证详细按钮未找到")
                
            # 检查按钮链接是否正确
            if 'visa_type_detail' in response.text:
                print("✓ 签证详细按钮链接正确")
            else:
                print("✗ 签证详细按钮链接有问题")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试2: 测试签证详细按钮的链接
    print("测试2: 测试签证详细按钮的链接")
    try:
        # 测试中国签证的详细页面
        visa_type = "中国签证"
        encoded_visa_type = quote(visa_type)
        response = requests.get(f"{base_url}/visa/basic/visa_type_detail/{encoded_visa_type}")
        if response.status_code == 200:
            print("✓ 签证详细页面加载成功")
            if "签证类型详情" in response.text:
                print("✓ 签证详细页面内容正确")
            else:
                print("✗ 签证详细页面内容有问题")
        else:
            print(f"✗ 签证详细页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试3: 检查按钮样式
    print("测试3: 检查签证详细按钮的样式")
    try:
        response = requests.get(f"{base_url}/visa/basic/visa_type_management")
        if response.status_code == 200:
            # 检查CSS样式
            if 'action-button.detail' in response.text:
                print("✓ 签证详细按钮CSS样式已添加")
            else:
                print("✗ 签证详细按钮CSS样式未找到")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

if __name__ == "__main__":
    test_detail_button() 