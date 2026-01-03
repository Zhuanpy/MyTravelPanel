# -*- coding: utf-8 -*-
"""
数据库迁移脚本：给 airport_data 表添加 city_name_en 字段
运行方式：python scripts/add_city_name_en.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # 检查字段是否已存在
        result = db.session.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'airport_data' AND COLUMN_NAME = 'city_name_en'"
        ))
        exists = result.fetchone()

        if exists:
            print("字段 city_name_en 已存在，无需添加")
        else:
            # 添加字段
            db.session.execute(text(
                "ALTER TABLE airport_data ADD COLUMN city_name_en VARCHAR(100) NULL COMMENT '城市英文名'"
            ))
            db.session.commit()
            print("成功添加字段 city_name_en 到 airport_data 表")

    except Exception as e:
        db.session.rollback()
        print(f"迁移失败: {e}")
