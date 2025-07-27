#!/usr/bin/env python3
"""
专门测试header高度一致性
验证各个section header的实际高度是否统一
"""

import requests
from bs4 import BeautifulSoup
import re

def test_header_height_consistency():
    """测试header高度一致性"""
    base_url = "http://127.0.0.1:5000"
    
    print("测试header高度一致性")
    print("=" * 40)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查各个section header
            sections_to_check = [
                ('相关链接', 'visa-project-section-header'),
                ('基本信息', 'visa-detail-section-header'),
                ('所需文件资料', 'visa-detail-section-header'),
                ('备注信息', 'visa-detail-section-header'),
                ('HID和Ref编号管理', 'visa-detail-section-header')
            ]
            
            header_info = []
            
            for section_name, header_class in sections_to_check:
                # 查找对应的section
                section = soup.find('h2', string=section_name)
                if section:
                    header = section.find_parent('div', class_=header_class)
                    if header:
                        # 检查header的样式
                        style = header.get('style', '')
                        padding_match = re.search(r'padding:\s*([^;]+)', style)
                        padding = padding_match.group(1) if padding_match else "CSS类定义"
                        
                        # 检查是否包含按钮
                        buttons = header.find_all('button')
                        button_count = len(buttons)
                        
                        # 检查actions容器
                        actions = header.find('div', class_='visa-detail-actions')
                        has_actions = actions is not None
                        
                        header_info.append({
                            'name': section_name,
                            'class': header_class,
                            'padding': padding,
                            'buttons': button_count,
                            'has_actions': has_actions
                        })
                        
                        print(f"✓ {section_name}")
                        print(f"  → CSS类: {header_class}")
                        print(f"  → Padding: {padding}")
                        print(f"  → 按钮数量: {button_count}")
                        print(f"  → 包含actions: {has_actions}")
                        
                        if buttons:
                            for btn in buttons:
                                btn_text = btn.get_text(strip=True)
                                btn_classes = ' '.join(btn.get('class', []))
                                print(f"    → 按钮: {btn_text} ({btn_classes})")
                        print()
                    else:
                        print(f"✗ 未找到 {section_name} 的header")
                else:
                    print(f"✗ 未找到 {section_name} section")
            
            # 分析结果
            print("高度一致性分析:")
            print("-" * 30)
            
            # 检查padding是否一致
            paddings = [info['padding'] for info in header_info]
            unique_paddings = set(paddings)
            
            if len(unique_paddings) == 1:
                print("✓ 所有header的padding样式一致")
            else:
                print("✗ header的padding样式不一致:")
                for padding in unique_paddings:
                    sections = [info['name'] for info in header_info if info['padding'] == padding]
                    print(f"  → {padding}: {', '.join(sections)}")
            
            # 检查按钮对高度的影响
            sections_with_buttons = [info for info in header_info if info['buttons'] > 0]
            sections_without_buttons = [info for info in header_info if info['buttons'] == 0]
            
            if sections_with_buttons:
                print(f"\n包含按钮的section: {len(sections_with_buttons)}个")
                for info in sections_with_buttons:
                    print(f"  → {info['name']}: {info['buttons']}个按钮")
            
            if sections_without_buttons:
                print(f"不包含按钮的section: {len(sections_without_buttons)}个")
                for info in sections_without_buttons:
                    print(f"  → {info['name']}")
            
            # 检查actions容器的影响
            sections_with_actions = [info for info in header_info if info['has_actions']]
            if sections_with_actions:
                print(f"\n包含actions容器的section: {len(sections_with_actions)}个")
                for info in sections_with_actions:
                    print(f"  → {info['name']}")
                
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def test_css_specificity():
    """测试CSS优先级"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试CSS优先级")
    print("=" * 25)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        if response.status_code == 200:
            # 检查CSS规则
            css_content = response.text
            
            # 查找相关的CSS规则
            css_rules = [
                '.visa-project-section-header',
                '.visa-detail-section-header',
                '.visa-detail-actions',
                '.visa-detail-section-header .visa-detail-actions'
            ]
            
            for rule in css_rules:
                if rule in css_content:
                    print(f"✓ 找到CSS规则: {rule}")
                else:
                    print(f"✗ 未找到CSS规则: {rule}")
                    
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

if __name__ == "__main__":
    test_header_height_consistency()
    test_css_specificity() 