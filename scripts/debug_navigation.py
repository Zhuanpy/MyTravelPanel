#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试导航功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import db, ProjectHeader, ProjectRef

def debug_navigation():
    """调试导航功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 调试导航功能 ===")
        
        # 1. 检查项目总数
        total_headers = ProjectHeader.query.count()
        print(f"数据库中共有 {total_headers} 个项目")
        
        if total_headers == 0:
            print("❌ 没有项目，无法测试导航")
            return
        
        # 2. 获取所有项目
        headers = ProjectHeader.query.order_by(ProjectHeader.id).all()
        print(f"\n所有项目列表:")
        for i, header in enumerate(headers):
            print(f"  {i+1}. ID: {header.id}, HID: {header.hid}")
        
        # 3. 测试第一个项目的导航
        if len(headers) > 0:
            first_header = headers[0]
            print(f"\n测试第一个项目 (ID: {first_header.id}):")
            
            # 获取上一个项目
            prev_header = ProjectHeader.query.filter(
                ProjectHeader.id < first_header.id
            ).order_by(ProjectHeader.id.desc()).first()
            
            # 获取下一个项目
            next_header = ProjectHeader.query.filter(
                ProjectHeader.id > first_header.id
            ).order_by(ProjectHeader.id.asc()).first()
            
            print(f"  上一个项目: {prev_header.hid if prev_header else '无'}")
            print(f"  下一个项目: {next_header.hid if next_header else '无'}")
            
            # 4. 检查模板变量
            print(f"\n模板变量检查:")
            print(f"  prev_header: {prev_header}")
            print(f"  next_header: {next_header}")
            print(f"  header: {first_header}")
            
            # 5. 测试URL生成
            if prev_header:
                print(f"  上一个项目URL: /projects/header/{prev_header.id}")
            if next_header:
                print(f"  下一个项目URL: /projects/header/{next_header.id}")
        
        # 6. 检查REF导航
        print(f"\n=== 检查REF导航 ===")
        refs = ProjectRef.query.all()
        print(f"数据库中共有 {len(refs)} 个REF")
        
        if len(refs) > 0:
            first_ref = refs[0]
            print(f"测试第一个REF (ID: {first_ref.id}, 项目ID: {first_ref.header_id}):")
            
            # 获取同一个header下的上一个和下一个REF
            prev_ref = ProjectRef.query.filter(
                ProjectRef.header_id == first_ref.header_id,
                ProjectRef.id < first_ref.id
            ).order_by(ProjectRef.id.desc()).first()
            
            next_ref = ProjectRef.query.filter(
                ProjectRef.header_id == first_ref.header_id,
                ProjectRef.id > first_ref.id
            ).order_by(ProjectRef.id.asc()).first()
            
            print(f"  上一个REF: {prev_ref.ref_number if prev_ref else '无'}")
            print(f"  下一个REF: {next_ref.ref_number if next_ref else '无'}")
        
        print(f"\n✅ 调试完成")

if __name__ == "__main__":
    debug_navigation() 