#!/usr/bin/env python3
"""
更新收款表的ref_id字段为可空，支持项目级别收款
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from App.exts import db
from sqlalchemy import text

def update_receipt_table():
    """更新收款表结构，使ref_id字段可空"""
    with app.app_context():
        try:
            # 修改ref_id字段为可空
            alter_sql = """
            ALTER TABLE project_receipts 
            MODIFY COLUMN ref_id INT NULL COMMENT 'REF明细ID（可选）';
            """
            
            # 执行修改
            db.session.execute(text(alter_sql))
            db.session.commit()
            
            print("✅ 收款表ref_id字段已更新为可空！")
            print("现在支持项目级别收款（ref_id为NULL）")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 更新失败：{str(e)}")
            print("请检查数据库权限或手动执行以下SQL：")
            print("ALTER TABLE project_receipts MODIFY COLUMN ref_id INT NULL COMMENT 'REF明细ID（可选）';")

if __name__ == "__main__":
    update_receipt_table() 