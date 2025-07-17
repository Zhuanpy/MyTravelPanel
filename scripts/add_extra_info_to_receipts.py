#!/usr/bin/env python3
"""
为project_receipts表添加extra_info字段的数据库迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from App.exts import db
from sqlalchemy import text

def add_extra_info_to_receipts():
    """为project_receipts表添加extra_info字段"""
    with app.app_context():
        try:
            # 检查字段是否已存在
            check_sql = """
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'project_receipts' AND column_name = 'extra_info';
            """
            result = db.session.execute(text(check_sql)).scalar()
            
            if result == 0:
                # 添加extra_info字段
                alter_sql = """
                ALTER TABLE project_receipts 
                ADD COLUMN extra_info TEXT;
                """
                db.session.execute(text(alter_sql))
                db.session.commit()
                print("✅ extra_info字段添加成功！")
            else:
                print("ℹ️ extra_info字段已存在，跳过添加。")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 添加字段失败：{str(e)}")

if __name__ == '__main__':
    add_extra_info_to_receipts() 