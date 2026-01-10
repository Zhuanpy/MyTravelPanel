# -*- coding: utf-8 -*-
"""
添加项目结算相关字段
- is_settled: 是否已结算
- settled_at: 结算时间
- settled_by: 结算人
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
                AND COLUMN_NAME = 'is_settled'
            """))

            if result.fetchone():
                print("字段 is_settled 已存在，跳过迁移")
                return

            # 添加 is_settled 字段
            print("添加 is_settled 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN is_settled BOOLEAN NOT NULL DEFAULT FALSE
                COMMENT '是否已结算'
            """))

            # 添加 settled_at 字段
            print("添加 settled_at 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN settled_at DATETIME NULL
                COMMENT '结算时间'
            """))

            # 添加 settled_by 字段
            print("添加 settled_by 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN settled_by VARCHAR(50) NULL
                COMMENT '结算人'
            """))

            db.session.commit()
            print("迁移完成！")

        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {e}")
            raise

if __name__ == '__main__':
    run_migration()
