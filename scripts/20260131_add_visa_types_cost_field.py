# -*- coding: utf-8 -*-
"""
添加 visa_types 表的 cost 和 validity_period 字段
运行方式: python scripts/20260131_add_visa_types_cost_field.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

def add_fields():
    """添加 cost 和 validity_period 字段到 visa_types 表"""
    with app.app_context():
        try:
            # 检查 cost 字段是否已存在
            check_sql = text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'visa_types'
                AND COLUMN_NAME = 'cost'
            """)
            result = db.session.execute(check_sql)
            if result.fetchone():
                print("字段 'cost' 已存在，跳过")
            else:
                # 添加 cost 字段
                alter_sql = text("""
                    ALTER TABLE visa_types
                    ADD COLUMN cost VARCHAR(200) NULL COMMENT '成本价格'
                    AFTER fee
                """)
                db.session.execute(alter_sql)
                print("成功添加 'cost' 字段")

            # 检查 validity_period 字段是否已存在
            check_sql2 = text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'visa_types'
                AND COLUMN_NAME = 'validity_period'
            """)
            result2 = db.session.execute(check_sql2)
            if result2.fetchone():
                print("字段 'validity_period' 已存在，跳过")
            else:
                # 添加 validity_period 字段
                alter_sql2 = text("""
                    ALTER TABLE visa_types
                    ADD COLUMN validity_period VARCHAR(100) NULL COMMENT '签证有效期'
                    AFTER cost
                """)
                db.session.execute(alter_sql2)
                print("成功添加 'validity_period' 字段")

            db.session.commit()
            print("迁移完成")

        except Exception as e:
            db.session.rollback()
            print(f"添加字段失败: {str(e)}")
            raise

if __name__ == '__main__':
    add_fields()
