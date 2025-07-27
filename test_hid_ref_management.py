#!/usr/bin/env python3
"""
测试HID和Ref编号管理功能
"""

import requests
import json

def test_hid_ref_management():
    """测试HID和Ref编号管理功能"""
    base_url = "http://127.0.0.1:5000"
    project_id = 322
    
    print("测试HID和Ref编号管理功能")
    print("=" * 50)
    
    # 测试1: 检查页面是否包含HID和Ref管理界面
    print("测试1: 检查页面是否包含HID和Ref管理界面")
    try:
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            if "HID和Ref编号管理" in response.text:
                print("✓ 页面包含HID和Ref编号管理界面")
            else:
                print("✗ 页面不包含HID和Ref编号管理界面")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试2: 测试更新HID编号API
    print("测试2: 测试更新HID编号API")
    try:
        test_hid = "TEST_HID_123"
        response = requests.post(f"{base_url}/visa/project/update_hid", 
                               json={
                                   'project_id': project_id,
                                   'hid_number': test_hid
                               },
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ HID编号更新成功")
            else:
                print(f"✗ HID编号更新失败: {data.get('message')}")
        else:
            print(f"✗ API请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试3: 测试更新Ref编号API
    print("测试3: 测试更新Ref编号API")
    try:
        test_ref = "TEST_REF_456"
        response = requests.post(f"{base_url}/visa/project/update_ref", 
                               json={
                                   'project_id': project_id,
                                   'ref_number': test_ref
                               },
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ Ref编号更新成功")
            else:
                print(f"✗ Ref编号更新失败: {data.get('message')}")
        else:
            print(f"✗ API请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试4: 测试清空编号功能
    print("测试4: 测试清空编号功能")
    try:
        # 清空HID
        response1 = requests.post(f"{base_url}/visa/project/update_hid", 
                                json={
                                    'project_id': project_id,
                                    'hid_number': ''
                                },
                                headers={'Content-Type': 'application/json'})
        
        # 清空Ref
        response2 = requests.post(f"{base_url}/visa/project/update_ref", 
                                json={
                                    'project_id': project_id,
                                    'ref_number': ''
                                },
                                headers={'Content-Type': 'application/json'})
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            if data1.get('success') and data2.get('success'):
                print("✓ 编号清空成功")
            else:
                print(f"✗ 编号清空失败: {data1.get('message')} / {data2.get('message')}")
        else:
            print(f"✗ API请求失败，状态码: {response1.status_code} / {response2.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试5: 测试错误处理
    print("测试5: 测试错误处理")
    try:
        # 测试无效项目ID
        response = requests.post(f"{base_url}/visa/project/update_hid", 
                               json={
                                   'project_id': 99999,
                                   'hid_number': 'test'
                               },
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 404:
            print("✓ 无效项目ID错误处理正确")
        else:
            print(f"✗ 无效项目ID错误处理异常，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_ui_elements():
    """测试UI元素是否存在"""
    base_url = "http://127.0.0.1:5000"
    project_id = 322
    
    print("\n测试UI元素")
    print("=" * 30)
    
    try:
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            # 检查关键UI元素
            ui_elements = [
                "HID编号",
                "Ref编号",
                "保存",
                "清空编号",
                "复制编号"
            ]
            
            missing_elements = []
            for element in ui_elements:
                if element not in response.text:
                    missing_elements.append(element)
            
            if missing_elements:
                print(f"✗ 缺少UI元素: {', '.join(missing_elements)}")
            else:
                print("✓ 所有UI元素都存在")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

if __name__ == "__main__":
    test_hid_ref_management()
    test_ui_elements() 