#!/usr/bin/env python3
"""
测试签证项目详细页面布局调整
验证"所需文件资料"是否在"备注信息"前面
"""

import requests
from bs4 import BeautifulSoup

def test_layout_adjustment():
    """测试页面布局调整"""
    base_url = "http://127.0.0.1:5000"
    
    print("测试签证项目详细页面布局调整")
    print("=" * 50)
    
    try:
        # 访问签证项目详细页面
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        
        if response.status_code == 200:
            print("✓ 页面加载成功")
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有section元素
            sections = soup.find_all('section', class_='visa-detail-section')
            
            if not sections:
                print("✗ 未找到visa-detail-section元素")
                return
            
            print(f"✓ 找到 {len(sections)} 个section")
            
            # 检查section的顺序
            section_titles = []
            for section in sections:
                header = section.find('h2')
                if header:
                    section_titles.append(header.get_text(strip=True))
            
            print("页面section顺序:")
            for i, title in enumerate(section_titles, 1):
                print(f"  {i}. {title}")
            
            # 检查"所需文件资料"是否在"备注信息"前面
            try:
                documents_index = section_titles.index("所需文件资料")
                remarks_index = section_titles.index("备注信息")
                
                if documents_index < remarks_index:
                    print("✓ 布局调整成功：'所需文件资料'在'备注信息'前面")
                else:
                    print("✗ 布局调整失败：'所需文件资料'不在'备注信息'前面")
                    
            except ValueError as e:
                print(f"✗ 未找到必要的section标题: {e}")
                
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

def test_section_content():
    """测试section内容是否完整"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n测试section内容完整性")
    print("=" * 30)
    
    try:
        project_id = 322
        response = requests.get(f"{base_url}/visa/project/visa_detail/id/{project_id}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查所需文件资料section
            documents_section = soup.find('h2', string='所需文件资料')
            if documents_section:
                documents_section_parent = documents_section.find_parent('section')
                if documents_section_parent:
                    # 检查是否有操作按钮
                    action_buttons = documents_section_parent.find_all('button')
                    if action_buttons:
                        print("✓ 所需文件资料section包含操作按钮")
                    else:
                        print("✗ 所需文件资料section缺少操作按钮")
                else:
                    print("✗ 未找到所需文件资料section的父容器")
            else:
                print("✗ 未找到所需文件资料section")
            
            # 检查备注信息section
            remarks_section = soup.find('h2', string='备注信息')
            if remarks_section:
                remarks_section_parent = remarks_section.find_parent('section')
                if remarks_section_parent:
                    # 检查是否有备注内容
                    remarks_content = remarks_section_parent.find(class_='visa-detail-remarks')
                    if remarks_content:
                        print("✓ 备注信息section包含内容区域")
                    else:
                        print("✗ 备注信息section缺少内容区域")
                else:
                    print("✗ 未找到备注信息section的父容器")
            else:
                print("✗ 未找到备注信息section")
                
        else:
            print(f"✗ 页面加载失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_layout_adjustment()
    test_section_content() 