#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移REF编号到新格式
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import db, ProjectHeader, ProjectRef

def migrate_ref_numbers():
    """迁移REF编号到新格式"""
    app = create_app()
    
    with app.app_context():
        print("=== 迁移REF编号到新格式 ===")
        
        # 1. 查看现有的REF编号
        existing_refs = ProjectRef.query.all()
        print(f"数据库中现有 {len(existing_refs)} 个REF")
        
        if not existing_refs:
            print("没有REF需要迁移")
            return
        
        print("现有REF编号:")
        for ref in existing_refs:
            print(f"  ID: {ref.id}, 编号: {ref.ref_number}, 项目: {ref.header.hid if ref.header else 'N/A'}")
        
        # 2. 询问是否继续
        response = input(f"\n是否要迁移这些REF编号到新格式？(y/N): ")
        if response.lower() != 'y':
            print("取消迁移操作")
            return
        
        # 3. 执行迁移
        try:
            # 按ID排序，确保迁移顺序一致
            refs_to_migrate = ProjectRef.query.order_by(ProjectRef.id).all()
            
            for i, ref in enumerate(refs_to_migrate):
                old_number = ref.ref_number
                new_number = f"R{str(i+1).zfill(2)}"
                
                print(f"迁移: {old_number} -> {new_number}")
                ref.ref_number = new_number
            
            db.session.commit()
            print("✅ 迁移完成！")
            
            # 4. 验证迁移结果
            print(f"\n迁移后的REF编号:")
            migrated_refs = ProjectRef.query.order_by(ProjectRef.id).all()
            for ref in migrated_refs:
                print(f"  ID: {ref.id}, 编号: {ref.ref_number}")
            
            # 5. 测试新的生成逻辑
            print(f"\n测试新的REF编号生成:")
            for i in range(3):
                new_ref_number = ProjectRef.generate_ref_number()
                print(f"  第{i+1}个新编号: {new_ref_number}")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 迁移失败: {str(e)}")

if __name__ == "__main__":
    migrate_ref_numbers() 