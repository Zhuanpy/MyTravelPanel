# -*- coding: utf-8 -*-
"""
添加项目操作员和业务员相关字段
- operator_id: 操作员ID
- operator_name: 操作员姓名
- salesperson_id: 业务员ID
- salesperson_name: 业务员姓名
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

def run_migration():
    """执行迁移"""
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'project_headers'
                AND COLUMN_NAME = 'operator_id'
            """))

            if result.fetchone():
                print("字段 operator_id 已存在，跳过迁移")
                return

            # 添加 operator_id 字段
            print("添加 operator_id 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN operator_id INT NULL
                COMMENT '操作员ID'
            """))

            # 添加 operator_name 字段
            print("添加 operator_name 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN operator_name VARCHAR(50) NULL
                COMMENT '操作员姓名'
            """))

            # 添加 salesperson_id 字段
            print("添加 salesperson_id 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN salesperson_id INT NULL
                COMMENT '业务员ID'
            """))

            # 添加 salesperson_name 字段
            print("添加 salesperson_name 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN salesperson_name VARCHAR(50) NULL
                COMMENT '业务员姓名'
            """))

            db.session.commit()
            print("迁移完成！")

        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {e}")
            raise

if __name__ == '__main__':
    run_migration()
