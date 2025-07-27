#!/usr/bin/env python3
"""
测试签证项目创建页面中的加载补充信息功能
"""

import requests
from urllib.parse import quote

def test_additional_info():
    """测试加载补充信息功能"""
    base_url = "http://127.0.0.1:5000"
    
    # 测试1: 访问签证项目创建页面
    print("测试1: 检查签证项目创建页面的加载补充信息按钮")
    try:
        visa_type = "台湾签证-中国护照"
        encoded_visa_type = quote(visa_type)
        response = requests.get(f"{base_url}/visa/project/visa_processing/{encoded_visa_type}")
        if response.status_code == 200:
            print("✓ 签证项目创建页面加载成功")
            if "加载补充信息" in response.text:
                print("✓ 加载补充信息按钮已添加")
            else:
                print("✗ 加载补充信息按钮未找到")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试2: 测试获取补充信息API
    print("测试2: 测试获取补充信息API")
    try:
        visa_type = "台湾签证-中国护照"
        identity = "PR"
        encoded_visa_type = quote(visa_type)
        encoded_identity = quote(identity)
        
        response = requests.get(f"{base_url}/visa/project/get_additional_info?visa_type={encoded_visa_type}&identity={encoded_identity}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ 获取补充信息API成功")
                print(f"✓ 共用资料补充信息: {data.get('share_additional_info', '无')[:50]}...")
                print(f"✓ 身份补充信息: {data.get('identity_additional_info', '无')[:50]}...")
            else:
                print(f"✗ API返回错误: {data.get('message')}")
        else:
            print(f"✗ API请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试3: 测试不同身份的补充信息
    print("测试3: 测试不同身份的补充信息")
    try:
        visa_type = "台湾签证-中国护照"
        identities = ["PR", "工作准证", "学生准证"]
        
        for identity in identities:
            encoded_visa_type = quote(visa_type)
            encoded_identity = quote(identity)
            
            response = requests.get(f"{base_url}/visa/project/get_additional_info?visa_type={encoded_visa_type}&identity={encoded_identity}")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    has_info = (data.get('share_additional_info') and data.get('share_additional_info') != '暂无补充信息') or \
                              (data.get('identity_additional_info') and data.get('identity_additional_info') != '暂无补充信息')
                    status = "有补充信息" if has_info else "无补充信息"
                    print(f"✓ {identity}: {status}")
                else:
                    print(f"✗ {identity}: API错误 - {data.get('message')}")
            else:
                print(f"✗ {identity}: 请求失败")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

if __name__ == "__main__":
    test_additional_info() 