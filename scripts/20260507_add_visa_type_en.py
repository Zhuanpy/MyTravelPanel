# -*- coding: utf-8 -*-
"""
为 visa_types 表添加 visa_type_en 列（签证类型英文名）

运行方式: python scripts/20260507_add_visa_type_en.py

背景：原 visa_types.visa_type 仅有中文（如"中国M类签证"），
新增英文列以便在面向客户的页面（项目编辑、签证下拉等）显示英文名称。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()


def add_field():
    """添加 visa_type_en 字段到 visa_types 表"""
    with app.app_context():
        try:
            check_sql = text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'visa_types'
                AND COLUMN_NAME = 'visa_type_en'
            """)
            if db.session.execute(check_sql).fetchone():
                print("字段 'visa_type_en' 已存在，跳过")
                return

            alter_sql = text("""
                ALTER TABLE visa_types
                ADD COLUMN visa_type_en VARCHAR(100) NULL COMMENT '签证类型英文名'
                AFTER visa_type
            """)
            db.session.execute(alter_sql)
            db.session.commit()
            print("成功添加 'visa_type_en' 字段")

        except Exception as e:
            db.session.rollback()
            print(f"添加字段失败: {str(e)}")
            raise


if __name__ == '__main__':
    add_field()
