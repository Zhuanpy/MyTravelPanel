# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 todos 表添加工时字段
- estimated_hours: 预估工时（小时）
- actual_hours: 实际工时（小时）
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

def add_hours_fields():
    """添加工时字段到 todos 表"""
    app = create_app()

    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'todos' AND COLUMN_NAME IN ('estimated_hours', 'actual_hours')
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            # 添加 estimated_hours 字段
            if 'estimated_hours' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE todos
                    ADD COLUMN estimated_hours FLOAT DEFAULT 0 COMMENT '预估工时（小时）'
                """))
                print("已添加 estimated_hours 字段")
            else:
                print("estimated_hours 字段已存在，跳过")

            # 添加 actual_hours 字段
            if 'actual_hours' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE todos
                    ADD COLUMN actual_hours FLOAT DEFAULT 0 COMMENT '实际工时（小时）'
                """))
                print("已添加 actual_hours 字段")
            else:
                print("actual_hours 字段已存在，跳过")

            db.session.commit()
            print("数据库迁移完成！")

        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {str(e)}")
            raise

if __name__ == '__main__':
    add_hours_fields()
