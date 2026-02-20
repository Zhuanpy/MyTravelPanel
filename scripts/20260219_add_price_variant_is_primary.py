# -*- coding: utf-8 -*-
"""
迁移脚本：为 package_price_variant 表添加 is_primary 字段
运行方式：python scripts/20260219_add_price_variant_is_primary.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    try:
        # 检查字段是否已存在
        result = db.session.execute(db.text(
            "SHOW COLUMNS FROM package_price_variant LIKE 'is_primary'"
        ))
        if result.fetchone():
            print("is_primary 字段已存在，跳过")
        else:
            db.session.execute(db.text(
                "ALTER TABLE package_price_variant ADD COLUMN is_primary TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否主要价格' AFTER currency"
            ))
            db.session.commit()
            print("成功添加 is_primary 字段到 package_price_variant 表")
    except Exception as e:
        db.session.rollback()
        print(f"迁移失败：{e}")
        sys.exit(1)
