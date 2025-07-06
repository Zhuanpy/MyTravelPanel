#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加计价方式字段到预算项目表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from sqlalchemy import text

def add_pricing_method_field():
    """为预算项目表添加计价方式字段"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'package_budget_items' 
                AND COLUMN_NAME = 'pricing_method'
            """))
            
            existing_columns = [row[0] for row in result]
            
            # 添加计价方式字段
            if 'pricing_method' not in existing_columns:
                print("添加 pricing_method 字段...")
                db.session.execute(text("""
                    ALTER TABLE package_budget_items 
                    ADD COLUMN pricing_method VARCHAR(20) DEFAULT 'person_based'
                """))
                print("✓ pricing_method 字段添加成功")
            else:
                print("✓ pricing_method 字段已存在")
            
            db.session.commit()
            print("\n✅ 计价方式字段添加完成！")
            
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
    print("🚀 开始添加计价方式字段...")
    success = add_pricing_method_field()
    if success:
        print("\n🎉 迁移完成！")
    else:
        print("\n💥 迁移失败！")
        sys.exit(1) 