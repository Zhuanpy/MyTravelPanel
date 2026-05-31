# -*- coding: utf-8 -*-
"""
迁移脚本：为 visa_project_files 表添加 updated_at（更新时间）字段
- 添加列后，将现有记录的 updated_at 初始化为 created_at
运行方式: python scripts/20260531_add_updated_at_to_visa_project_files.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    TABLE = 'visa_project_files'
    COLUMN = 'updated_at'

    exists = db.session.execute(text(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c
        """
    ), {'t': TABLE, 'c': COLUMN}).scalar()

    if exists:
        print(f"字段 {TABLE}.{COLUMN} 已存在，无需迁移。")
    else:
        try:
            db.session.execute(text(
                f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} DATETIME NULL COMMENT '更新时间' AFTER created_at"
            ))
            # 现有记录：更新时间初始化为上传时间
            db.session.execute(text(
                f"UPDATE {TABLE} SET {COLUMN} = created_at WHERE {COLUMN} IS NULL"
            ))
            db.session.commit()
            print(f"成功添加字段 {TABLE}.{COLUMN}，并已用 created_at 初始化现有记录。")
        except Exception as e:
            db.session.rollback()
            print(f"迁移失败：{e}")
            raise
