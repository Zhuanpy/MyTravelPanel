#!/usr/bin/env python3
"""
测试新的HID和Ref编号管理功能
验证根据关联状态显示不同界面
"""

import requests
from bs4 import BeautifulSoup

def test_new_hid_ref_management():
    """测试新的HID和Ref编号管理功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("测试新的HID和Ref编号管理功能")
    print("=" * 50)
    
    # 测试1: 检查基本信息中是否已移除HID和REF相关内容
    print("测试1: 检查基本信息中是否已移除HID和REF相关内容")
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            # 检查基本信息中是否还有HID和REF相关内容
            removed_elements = [
                "HID或序列号",
                "项目HID",
                "REF编号",
                "创建HID",
                "创建REF"
            ]
            
            found_elements = []
            for element in removed_elements:
                if element in response.text:
                    found_elements.append(element)
            
            if found_elements:
                print(f"✗ 基本信息中仍然包含: {', '.join(found_elements)}")
            else:
                print("✓ 基本信息中已成功移除HID和REF相关内容")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试2: 检查底部是否包含新的HID和REF管理界面
    print("测试2: 检查底部是否包含新的HID和REF管理界面")
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            if "HID和Ref编号管理" in response.text:
                print("✓ 底部包含HID和Ref编号管理界面")
                
                # 检查是否包含新的UI元素
                new_elements = [
                    "创建HID和Ref编号",
                    "解除关联",
                    "查看详情"
                ]
                
                found_new_elements = []
                for element in new_elements:
                    if element in response.text:
                        found_new_elements.append(element)
                
                if found_new_elements:
                    print(f"✓ 包含新的UI元素: {', '.join(found_new_elements)}")
                else:
                    print("✗ 缺少新的UI元素")
            else:
                print("✗ 底部不包含HID和Ref编号管理界面")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试3: 测试解除关联API
    print("测试3: 测试解除关联API")
    try:
        project_id = 322
        response = requests.post(f"{base_url}/visa/project/unlink_hid_ref", 
                               json={'project_id': project_id},
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ 解除关联API正常工作")
            else:
                print(f"✗ 解除关联API返回错误: {data.get('message')}")
        else:
            print(f"✗ 解除关联API请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_conditional_display():
    """测试条件显示功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试条件显示功能")
    print("=" * 30)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找HID和Ref管理section
            hid_ref_section = soup.find('h2', string='HID和Ref编号管理')
            if hid_ref_section:
                section_parent = hid_ref_section.find_parent('section')
                if section_parent:
                    # 检查是否包含创建界面或管理界面
                    create_interface = section_parent.find(string='创建HID和Ref编号')
                    manage_interface = section_parent.find(string='查看详情')
                    
                    if create_interface:
                        print("✓ 显示创建界面（未关联状态）")
                    elif manage_interface:
                        print("✓ 显示管理界面（已关联状态）")
                    else:
                        print("✗ 界面状态不明确")
                else:
                    print("✗ 未找到HID和Ref管理section")
            else:
                print("✗ 未找到HID和Ref编号管理标题")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_ui_consistency():
    """测试UI一致性"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试UI一致性")
    print("=" * 20)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            # 检查页面结构是否完整
            key_sections = [
                "基本信息",
                "所需文件资料",
                "备注信息",
                "HID和Ref编号管理"
            ]
            
            missing_sections = []
            for section in key_sections:
                if section not in response.text:
                    missing_sections.append(section)
            
            if missing_sections:
                print(f"✗ 缺少关键section: {', '.join(missing_sections)}")
            else:
                print("✓ 页面结构完整，所有关键section都存在")
                
            # 检查section顺序
            soup = BeautifulSoup(response.text, 'html.parser')
            sections = soup.find_all('h2')
            section_titles = [s.get_text(strip=True) for s in sections]
            
            print("页面section顺序:")
            for i, title in enumerate(section_titles, 1):
                print(f"  {i}. {title}")
                
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

if __name__ == "__main__":
    test_new_hid_ref_management()
    test_conditional_display()
    test_ui_consistency() 