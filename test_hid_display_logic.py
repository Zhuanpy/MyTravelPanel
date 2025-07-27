#!/usr/bin/env python3
"""
测试HID显示逻辑
验证基本信息中的HID或序列号字段显示逻辑
"""

import requests
from bs4 import BeautifulSoup

def test_hid_display_logic():
    """测试HID显示逻辑"""
    base_url = "http://127.0.0.1:5000"
    
    print("测试HID显示逻辑")
    print("=" * 40)
    
    # 测试1: 检查基本信息中是否包含HID或序列号字段
    print("测试1: 检查基本信息中的HID或序列号字段")
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            if "HID或序列号" in response.text:
                print("✓ 基本信息中包含HID或序列号字段")
                
                # 解析页面查找HID显示内容
                soup = BeautifulSoup(response.text, 'html.parser')
                hid_label = soup.find('span', string='HID或序列号')
                if hid_label:
                    hid_item = hid_label.find_parent('div', class_='visa-detail-info-item')
                    if hid_item:
                        hid_value = hid_item.find('span', class_='visa-detail-info-value')
                        if hid_value:
                            hid_text = hid_value.get_text(strip=True)
                            print(f"✓ HID或序列号显示值: {hid_text}")
                            if hid_text != '未设置':
                                print("  → 格式: HID编号")
                            else:
                                print("  → 格式: 未设置")
                        else:
                            print("✗ 未找到HID值显示元素")
                    else:
                        print("✗ 未找到HID信息项")
                else:
                    print("✗ 未找到HID或序列号标签")
            else:
                print("✗ 基本信息中不包含HID或序列号字段")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试2: 检查底部HID管理界面是否显示临时编号
    print("测试2: 检查底部HID管理界面是否显示临时编号")
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            if "临时编号" in response.text:
                print("✓ 底部HID管理界面显示临时编号")
                
                # 查找临时编号的具体内容
                soup = BeautifulSoup(response.text, 'html.parser')
                temp_note = soup.find('p', class_='hid-ref-temp-note')
                if temp_note:
                    temp_text = temp_note.get_text(strip=True)
                    print(f"✓ 临时编号显示: {temp_text}")
                else:
                    print("✗ 未找到临时编号元素")
            else:
                print("✓ 底部HID管理界面不显示临时编号（可能已关联正式HID）")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 测试3: 检查HID显示优先级逻辑
    print("测试3: 检查HID显示优先级逻辑")
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否有正式的HID关联
            has_formal_hid = soup.find('a', class_='hid-ref-link')
            
            # 检查基本信息中的HID显示
            hid_label = soup.find('span', string='HID或序列号')
            if hid_label:
                hid_item = hid_label.find_parent('div', class_='visa-detail-info-item')
                if hid_item:
                    hid_value = hid_item.find('span', class_='visa-detail-info-value')
                    if hid_value:
                        hid_text = hid_value.get_text(strip=True)
                        
                        if has_formal_hid and hid_text != '未设置':
                            print("✓ 已关联正式HID，基本信息显示正式HID")
                        elif not has_formal_hid and hid_text != '未设置':
                            print("✓ 未关联正式HID，基本信息显示临时编号")
                        elif hid_text == '未设置':
                            print("✓ 基本信息显示未设置状态")
                        else:
                            print("✗ HID显示逻辑异常")
                    else:
                        print("✗ 未找到HID值显示")
                else:
                    print("✗ 未找到HID信息项")
            else:
                print("✗ 未找到HID或序列号标签")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_create_hid_functionality():
    """测试创建HID功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试创建HID功能")
    print("=" * 25)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            # 检查是否有创建HID按钮
            if "创建HID和Ref编号" in response.text:
                print("✓ 页面包含创建HID和Ref编号按钮")
                
                # 检查创建按钮的onclick事件
                soup = BeautifulSoup(response.text, 'html.parser')
                create_btn = soup.find('button', string='创建HID和Ref编号')
                if create_btn and 'onclick="createProjectLinks()"' in str(create_btn):
                    print("✓ 创建按钮包含正确的onclick事件")
                else:
                    print("✗ 创建按钮缺少onclick事件")
            else:
                print("✓ 页面不包含创建按钮（可能已有关联）")
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_page_structure():
    """测试页面结构完整性"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试页面结构完整性")
    print("=" * 25)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            # 检查关键section是否存在
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

def test_hid_ref_layout():
    """测试HID和REF布局"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试HID和REF布局")
    print("=" * 20)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查HID和REF状态容器
            hid_ref_status = soup.find('div', class_='hid-ref-status')
            if hid_ref_status:
                print("✓ 找到HID和REF状态容器")
                
                # 检查是否为flex布局
                style = hid_ref_status.get('style', '')
                if 'display: flex' in style or 'display:flex' in style:
                    print("✓ HID和REF状态容器使用flex布局")
                else:
                    # 检查CSS类是否应用了flex布局
                    print("✓ HID和REF状态容器使用CSS类布局")
                
                # 检查子元素数量
                status_items = hid_ref_status.find_all('div', class_='hid-ref-status-item')
                print(f"✓ 找到 {len(status_items)} 个状态项")
                
                if len(status_items) == 2:
                    print("✓ HID和REF状态项数量正确")
                else:
                    print(f"⚠ 状态项数量: {len(status_items)} (期望2个)")
                    
            else:
                print("✗ 未找到HID和REF状态容器")
                
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

if __name__ == "__main__":
    test_hid_display_logic()
    test_create_hid_functionality()
    test_page_structure()
    test_hid_ref_layout() 