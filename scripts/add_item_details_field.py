#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加item_details字段，移除item_type字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from sqlalchemy import text

def migrate_database():
    """执行数据库迁移"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始数据库迁移...")
            
            # 1. 添加item_details字段
            print("1. 添加item_details字段...")
            try:
                db.session.execute(text("""
                    ALTER TABLE package_budget_items 
                    ADD COLUMN item_details TEXT
                """))
                print("   ✓ item_details字段添加成功")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print("   ✓ item_details字段已存在")
                else:
                    print(f"   ✗ 添加item_details字段失败: {e}")
            
            # 2. 移除item_type字段
            print("2. 移除item_type字段...")
            try:
                db.session.execute(text("""
                    ALTER TABLE package_budget_items 
                    DROP COLUMN item_type
                """))
                print("   ✓ item_type字段移除成功")
            except Exception as e:
                if "doesn't exist" in str(e) or "Unknown column" in str(e):
                    print("   ✓ item_type字段不存在，无需移除")
                else:
                    print(f"   ✗ 移除item_type字段失败: {e}")
            
            # 3. 提交更改
            db.session.commit()
            print("3. 数据库迁移完成！")
            
            # 4. 验证迁移结果
            print("4. 验证迁移结果...")
            result = db.session.execute(text("""
                DESCRIBE package_budget_items
            """))
            
            columns = [row[0] for row in result]
            print(f"   当前字段列表: {', '.join(columns)}")
            
            if 'item_details' in columns:
                print("   ✓ item_details字段存在")
            else:
                print("   ✗ item_details字段不存在")
                
            if 'item_type' not in columns:
                print("   ✓ item_type字段已移除")
            else:
                print("   ✗ item_type字段仍然存在")
            
        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {e}")
            return False
        
        return True

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n✅ 数据库迁移成功完成！")
    else:
        print("\n❌ 数据库迁移失败！")
        sys.exit(1) 