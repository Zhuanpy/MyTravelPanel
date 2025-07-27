#!/usr/bin/env python3
"""
测试section header高度一致性
验证各个section的header高度是否统一
"""

import requests
from bs4 import BeautifulSoup

def test_section_header_height():
    """测试section header高度一致性"""
    base_url = "http://127.0.0.1:5000"
    
    print("测试section header高度一致性")
    print("=" * 40)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查不同类型的section header
            section_types = {
                'visa-project-section-header': '相关链接',
                'visa-detail-section-header': ['基本信息', '所需文件资料', '备注信息', 'HID和Ref编号管理']
            }
            
            for header_class, section_names in section_types.items():
                if isinstance(section_names, list):
                    for section_name in section_names:
                        # 查找对应的section
                        section = soup.find('h2', string=section_name)
                        if section:
                            header = section.find_parent('div', class_=header_class)
                            if header:
                                print(f"✓ 找到 {section_name} section header")
                                
                                # 检查padding样式
                                style = header.get('style', '')
                                if 'padding' in style:
                                    print(f"  → 内联样式padding: {style}")
                                else:
                                    print(f"  → 使用CSS类: {header_class}")
                                
                                # 检查是否包含按钮
                                buttons = header.find_all('button')
                                if buttons:
                                    print(f"  → 包含 {len(buttons)} 个按钮")
                                    for btn in buttons:
                                        btn_class = btn.get('class', [])
                                        if 'visa-project-btn' in btn_class:
                                            print(f"    → 按钮类: {' '.join(btn_class)}")
                                            # 检查按钮样式
                                            style = btn.get('style', '')
                                            if style:
                                                print(f"    → 内联样式: {style}")
                                else:
                                    print(f"  → 不包含按钮")
                            else:
                                print(f"✗ 未找到 {section_name} 的header")
                        else:
                            print(f"✗ 未找到 {section_name} section")
                else:
                    # 单个section
                    section = soup.find('h2', string=section_names)
                    if section:
                        header = section.find_parent('div', class_=header_class)
                        if header:
                            print(f"✓ 找到 {section_names} section header")
                            
                            # 检查padding样式
                            style = header.get('style', '')
                            if 'padding' in style:
                                print(f"  → 内联样式padding: {style}")
                            else:
                                print(f"  → 使用CSS类: {header_class}")
                            
                            # 检查是否包含按钮
                            buttons = header.find_all('button')
                            if buttons:
                                print(f"  → 包含 {len(buttons)} 个按钮")
                                for btn in buttons:
                                    btn_class = btn.get('class', [])
                                    if 'visa-project-btn' in btn_class:
                                        print(f"    → 按钮类: {' '.join(btn_class)}")
                                        # 检查按钮样式
                                        style = btn.get('style', '')
                                        if style:
                                            print(f"    → 内联样式: {style}")
                            else:
                                print(f"  → 不包含按钮")
                        else:
                            print(f"✗ 未找到 {section_names} 的header")
                    else:
                        print(f"✗ 未找到 {section_names} section")
            
            print()
            
            # 检查CSS样式定义
            print("检查CSS样式定义:")
            if 'visa-project-section-header' in response.text:
                print("✓ 找到 visa-project-section-header CSS类")
            if 'visa-detail-section-header' in response.text:
                print("✓ 找到 visa-detail-section-header CSS类")
                
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_header_consistency():
    """测试header一致性"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试header一致性")
    print("=" * 25)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取所有section header
            project_headers = soup.find_all('div', class_='visa-project-section-header')
            detail_headers = soup.find_all('div', class_='visa-detail-section-header')
            
            print(f"✓ 找到 {len(project_headers)} 个 visa-project-section-header")
            print(f"✓ 找到 {len(detail_headers)} 个 visa-detail-section-header")
            
            # 检查每个header的内容
            for i, header in enumerate(project_headers, 1):
                h2 = header.find('h2')
                if h2:
                    print(f"  {i}. {h2.get_text(strip=True)} (project-header)")
            
            for i, header in enumerate(detail_headers, 1):
                h2 = header.find('h2')
                if h2:
                    print(f"  {i}. {h2.get_text(strip=True)} (detail-header)")
                    
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_button_style_consistency():
    """测试按钮样式一致性"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试按钮样式一致性")
    print("=" * 25)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有visa-project-btn按钮
            buttons = soup.find_all('button', class_='visa-project-btn')
            print(f"✓ 找到 {len(buttons)} 个 visa-project-btn 按钮")
            
            # 检查按钮样式
            for i, btn in enumerate(buttons, 1):
                btn_text = btn.get_text(strip=True)
                btn_classes = btn.get('class', [])
                print(f"  {i}. {btn_text}")
                print(f"    → 类: {' '.join(btn_classes)}")
                
                # 检查是否有内联样式
                style = btn.get('style', '')
                if style:
                    print(f"    → 内联样式: {style}")
                else:
                    print(f"    → 使用CSS类样式")
                    
                # 检查父容器
                parent = btn.find_parent('div', class_='visa-detail-section-header')
                if parent:
                    print(f"    → 位于: visa-detail-section-header")
                else:
                    print(f"    → 位于: 其他容器")
                print()
                
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

if __name__ == "__main__":
    test_section_header_height()
    test_header_consistency()
    test_button_style_consistency() 