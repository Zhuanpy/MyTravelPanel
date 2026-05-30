# -*- coding: utf-8 -*-
"""
迁移脚本：为 visa_documents_list 表添加 name_en（英文名称）字段
运行方式: python scripts/20260530_add_name_en_to_documents_list.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    TABLE = 'visa_documents_list'
    COLUMN = 'name_en'

    # 检查字段是否已存在（MySQL information_schema）
    exists = db.session.execute(text(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :t
          AND COLUMN_NAME = :c
        """
    ), {'t': TABLE, 'c': COLUMN}).scalar()

    if exists:
        print(f"字段 {TABLE}.{COLUMN} 已存在，无需迁移。")
    else:
        try:
            db.session.execute(text(
                f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} VARCHAR(150) NULL COMMENT '文档名称英文' AFTER name"
            ))
            db.session.commit()
            print(f"成功添加字段 {TABLE}.{COLUMN}")
        except Exception as e:
            db.session.rollback()
            print(f"迁移失败：{e}")
            raise
