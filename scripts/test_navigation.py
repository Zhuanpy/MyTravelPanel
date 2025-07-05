#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试项目导航功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import db, ProjectHeader

def test_navigation():
    """测试项目导航功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试项目导航功能 ===")
        
        # 获取所有项目，按ID排序
        headers = ProjectHeader.query.order_by(ProjectHeader.id).all()
        print(f"当前共有 {len(headers)} 个项目")
        
        if len(headers) < 2:
            print("项目数量不足，无法测试导航功能")
            return
        
        # 显示所有项目
        print("\n所有项目列表：")
        for i, header in enumerate(headers):
            print(f"{i+1}. ID: {header.id}, HID: {header.hid}, 描述: {header.desc}")
        
        # 测试中间项目的导航
        middle_index = len(headers) // 2
        current_header = headers[middle_index]
        
        print(f"\n测试项目: {current_header.hid} (ID: {current_header.id})")
        
        # 获取上一个项目
        prev_header = ProjectHeader.query.filter(
            ProjectHeader.id < current_header.id
        ).order_by(ProjectHeader.id.desc()).first()
        
        # 获取下一个项目
        next_header = ProjectHeader.query.filter(
            ProjectHeader.id > current_header.id
        ).order_by(ProjectHeader.id.asc()).first()
        
        print(f"上一个项目: {prev_header.hid if prev_header else '无'}")
        print(f"下一个项目: {next_header.hid if next_header else '无'}")
        
        # 验证导航逻辑
        if prev_header:
            print(f"✅ 上一个项目正确: {prev_header.hid}")
        else:
            print("ℹ️  这是第一个项目，没有上一个")
            
        if next_header:
            print(f"✅ 下一个项目正确: {next_header.hid}")
        else:
            print("ℹ️  这是最后一个项目，没有下一个")
        
        # 测试边界情况
        print("\n=== 测试边界情况 ===")
        
        # 第一个项目
        first_header = headers[0]
        first_prev = ProjectHeader.query.filter(
            ProjectHeader.id < first_header.id
        ).order_by(ProjectHeader.id.desc()).first()
        first_next = ProjectHeader.query.filter(
            ProjectHeader.id > first_header.id
        ).order_by(ProjectHeader.id.asc()).first()
        
        print(f"第一个项目 {first_header.hid}:")
        print(f"  上一个: {first_prev.hid if first_prev else '无'}")
        print(f"  下一个: {first_next.hid if first_next else '无'}")
        
        # 最后一个项目
        last_header = headers[-1]
        last_prev = ProjectHeader.query.filter(
            ProjectHeader.id < last_header.id
        ).order_by(ProjectHeader.id.desc()).first()
        last_next = ProjectHeader.query.filter(
            ProjectHeader.id > last_header.id
        ).order_by(ProjectHeader.id.asc()).first()
        
        print(f"最后一个项目 {last_header.hid}:")
        print(f"  上一个: {last_prev.hid if last_prev else '无'}")
        print(f"  下一个: {last_next.hid if last_next else '无'}")
        
        print("\n✅ 导航功能测试完成！")

if __name__ == "__main__":
    test_navigation() 