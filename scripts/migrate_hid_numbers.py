#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移HID编号到新格式
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import db, ProjectHeader

def migrate_hid_numbers():
    """迁移HID编号到新格式"""
    app = create_app()
    
    with app.app_context():
        print("=== 迁移HID编号到新格式 ===")
        
        # 1. 查看现有的HID编号
        existing_headers = ProjectHeader.query.all()
        print(f"数据库中现有 {len(existing_headers)} 个项目")
        
        if not existing_headers:
            print("没有项目需要迁移")
            return
        
        print("现有HID编号:")
        for header in existing_headers:
            print(f"  ID: {header.id}, HID: {header.hid}, 描述: {header.desc}")
        
        # 2. 询问是否继续
        response = input(f"\n是否要迁移这些HID编号到新格式？(y/N): ")
        if response.lower() != 'y':
            print("取消迁移操作")
            return
        
        # 3. 执行迁移
        try:
            # 按ID排序，确保迁移顺序一致
            headers_to_migrate = ProjectHeader.query.order_by(ProjectHeader.id).all()
            
            for i, header in enumerate(headers_to_migrate):
                old_hid = header.hid
                new_hid = f"H{i+1}"
                
                print(f"迁移: {old_hid} -> {new_hid}")
                header.hid = new_hid
            
            db.session.commit()
            print("✅ 迁移完成！")
            
            # 4. 验证迁移结果
            print(f"\n迁移后的HID编号:")
            migrated_headers = ProjectHeader.query.order_by(ProjectHeader.id).all()
            for header in migrated_headers:
                print(f"  ID: {header.id}, HID: {header.hid}, 描述: {header.desc}")
            
            # 5. 测试新的生成逻辑
            print(f"\n测试新的HID编号生成:")
            for i in range(3):
                new_hid = ProjectHeader.generate_hid()
                print(f"  第{i+1}个新编号: {new_hid}")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 迁移失败: {str(e)}")

if __name__ == "__main__":
    migrate_hid_numbers() 