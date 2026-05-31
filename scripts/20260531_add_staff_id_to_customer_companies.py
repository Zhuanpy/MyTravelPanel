# -*- coding: utf-8 -*-
"""
迁移脚本：为 customer_companies 表添加 staff_id（所属员工）字段
- 设置后该客户仅归属员工本人 + 2级员工/管理员可见可编辑；为空则共享
运行方式: python scripts/20260531_add_staff_id_to_customer_companies.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from sqlalchemy import text
from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    TABLE = 'customer_companies'
    COLUMN = 'staff_id'

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
                f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} INT NULL COMMENT '所属员工ID' AFTER legal_person"
            ))
            db.session.commit()
            print(f"成功添加字段 {TABLE}.{COLUMN}")
        except Exception as e:
            db.session.rollback()
            print(f"迁移失败：{e}")
            raise
