#!/usr/bin/env python3
"""
测试移除签证项目详细页面中的补充信息功能
"""

import requests
from urllib.parse import quote

def test_remove_additional_info():
    """测试移除补充信息功能"""
    base_url = "http://127.0.0.1:5000"
    
    # 测试1: 访问签证项目详细页面，检查是否还有补充信息
    print("测试1: 检查签证项目详细页面是否已移除补充信息")
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            print("✓ 签证项目详细页面加载成功")
            if "补充信息" in response.text:
                print("✗ 补充信息部分仍然存在")
            else:
                print("✓ 补充信息部分已成功移除")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试2: 检查备注信息是否仍然存在
    print("测试2: 检查备注信息是否仍然存在")
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            if "备注信息" in response.text:
                print("✓ 备注信息部分仍然存在")
            else:
                print("✗ 备注信息部分不存在")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试3: 检查页面结构是否正常
    print("测试3: 检查页面结构是否正常")
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            # 检查关键元素是否仍然存在
            key_elements = [
                "签证项目详情",
                "基本信息",
                "项目名称",
                "签证状态",
                "操作按钮"
            ]
            
            missing_elements = []
            for element in key_elements:
                if element not in response.text:
                    missing_elements.append(element)
            
            if missing_elements:
                print(f"✗ 缺少关键元素: {', '.join(missing_elements)}")
            else:
                print("✓ 页面结构正常，所有关键元素都存在")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

if __name__ == "__main__":
    test_remove_additional_info() 