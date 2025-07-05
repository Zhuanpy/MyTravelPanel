#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的HID编号生成逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import db, ProjectHeader

def test_hid_generation():
    """测试HID编号生成"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试新的HID编号生成逻辑 ===")
        
        # 1. 查看现有的HID编号
        existing_headers = ProjectHeader.query.all()
        print(f"数据库中现有 {len(existing_headers)} 个项目")
        
        if existing_headers:
            print("现有HID编号:")
            for header in existing_headers:
                print(f"  ID: {header.id}, HID: {header.hid}, 描述: {header.desc}")
        
        # 2. 测试生成新的HID编号
        print(f"\n测试生成新的HID编号:")
        for i in range(5):
            new_hid = ProjectHeader.generate_hid()
            print(f"  第{i+1}个新编号: {new_hid}")
        
        # 3. 验证编号唯一性
        print(f"\n验证编号唯一性:")
        all_hids = [header.hid for header in existing_headers]
        unique_hids = set(all_hids)
        
        if len(all_hids) == len(unique_hids):
            print("✅ 所有现有HID编号都是唯一的")
        else:
            print("❌ 发现重复的HID编号")
            duplicates = [hid for hid in all_hids if all_hids.count(hid) > 1]
            print(f"重复的编号: {duplicates}")
        
        # 4. 测试编号格式
        print(f"\n验证编号格式:")
        for header in existing_headers:
            hid = header.hid
            if hid.startswith('H') and len(hid) > 1:
                try:
                    number = int(hid[1:])
                    print(f"  ✅ {hid}: 格式正确，数字部分为 {number}")
                except ValueError:
                    print(f"  ❌ {hid}: 数字部分格式错误")
            else:
                print(f"  ❌ {hid}: 不以'H'开头或长度不足")

if __name__ == "__main__":
    test_hid_generation() 