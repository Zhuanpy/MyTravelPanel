#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正REF路由中的重定向问题
"""

def fix_ref_routes():
    """修正REF路由文件中的重定向路由"""
    
    # 读取文件
    with open('App_new/business/projects/routes/project_ref.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换所有错误的重定向路由
    content = content.replace('business_projects.project_header.header_detail', 'business_projects.detail.project_detail')
    
    # 写入文件
    with open('App_new/business/projects/routes/project_ref.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("REF路由重定向问题已修正完成！")

if __name__ == "__main__":
    fix_ref_routes()
