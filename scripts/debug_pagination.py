#!/usr/bin/env python3
"""
分页调试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from flask import url_for

def debug_pagination():
    """调试分页URL生成"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始调试分页URL生成...")
            
            # 测试URL生成
            base_url = url_for('projects.list_projects')
            print(f"基础URL: {base_url}")
            
            # 测试带参数的URL
            url_with_page = url_for('projects.list_projects', page=2)
            print(f"第2页URL: {url_with_page}")
            
            url_with_page3 = url_for('projects.list_projects', page=3)
            print(f"第3页URL: {url_with_page3}")
            
            # 测试带多个参数的URL
            url_with_filters = url_for('projects.list_projects', page=2, status='active', search='test')
            print(f"带筛选的第2页URL: {url_with_filters}")
            
            print("URL生成测试完成！")
                
        except Exception as e:
            print(f"调试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    debug_pagination() 