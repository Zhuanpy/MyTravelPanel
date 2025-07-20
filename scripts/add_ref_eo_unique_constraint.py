#!/usr/bin/env python3
"""
添加REF和EO的一对一约束脚本
确保每个REF只能有一个EO
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from sqlalchemy import text

def add_ref_eo_unique_constraint():
    """添加REF和EO的一对一约束"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始添加REF和EO的一对一约束...")
            
            # 首先检查是否已经存在约束
            existing_constraints = db.session.execute(text("""
                SELECT CONSTRAINT_NAME 
                FROM information_schema.TABLE_CONSTRAINTS 
                WHERE TABLE_NAME = 'project_eos' 
                AND CONSTRAINT_TYPE = 'UNIQUE'
                AND CONSTRAINT_NAME LIKE '%ref_id%'
            """)).fetchall()
            
            if existing_constraints:
                print("约束已存在，跳过添加")
                return
            
            # 添加唯一约束
            db.session.execute(text("""
                ALTER TABLE project_eos 
                ADD CONSTRAINT unique_ref_eo 
                UNIQUE (ref_id)
            """))
            
            db.session.commit()
            print("成功添加REF和EO的一对一约束")
            
        except Exception as e:
            db.session.rollback()
            print(f"添加约束时发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    add_ref_eo_unique_constraint() 