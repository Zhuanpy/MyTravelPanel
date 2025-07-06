#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加物品单价和件数字段到预算项目表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from sqlalchemy import text

def add_item_unit_fields():
    """为预算项目表添加物品单价和件数字段"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'package_budget_items' 
                AND COLUMN_NAME IN ('item_unit_price', 'item_quantity')
            """))
            
            existing_columns = [row[0] for row in result]
            
            # 添加物品单价字段
            if 'item_unit_price' not in existing_columns:
                print("添加 item_unit_price 字段...")
                db.session.execute(text("""
                    ALTER TABLE package_budget_items 
                    ADD COLUMN item_unit_price DECIMAL(10,2) NULL
                """))
                print("✓ item_unit_price 字段添加成功")
            else:
                print("✓ item_unit_price 字段已存在")
            
            # 添加物品件数字段
            if 'item_quantity' not in existing_columns:
                print("添加 item_quantity 字段...")
                db.session.execute(text("""
                    ALTER TABLE package_budget_items 
                    ADD COLUMN item_quantity INT DEFAULT 1
                """))
                print("✓ item_quantity 字段添加成功")
            else:
                print("✓ item_quantity 字段已存在")
            
            db.session.commit()
            print("\n✅ 所有字段添加完成！")
            
            # 显示表结构
            print("\n📋 当前表结构：")
            result = db.session.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'package_budget_items'
                ORDER BY ORDINAL_POSITION
            """))
            
            for row in result:
                print(f"  {row[0]}: {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'}) {f'DEFAULT {row[3]}' if row[3] else ''}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 错误: {e}")
            return False
        
        return True

if __name__ == "__main__":
    print("🚀 开始添加物品单价和件数字段...")
    success = add_item_unit_fields()
    if success:
        print("\n🎉 迁移完成！")
    else:
        print("\n💥 迁移失败！")
        sys.exit(1) 