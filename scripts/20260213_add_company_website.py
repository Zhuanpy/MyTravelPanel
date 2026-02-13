# -*- coding: utf-8 -*-
"""
迁移脚本：为 company_info 表添加 website 字段
运行方式：python scripts/20260213_add_company_website.py
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
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='company_info' AND column_name='website'"
        ))
        exists = result.scalar()

        if exists:
            print("✅ website 字段已存在，无需迁移")
        else:
            db.session.execute(text(
                "ALTER TABLE company_info ADD COLUMN website VARCHAR(200) NULL COMMENT '公司网址' AFTER stamp_path"
            ))
            db.session.commit()
            print("✅ 成功添加 website 字段到 company_info 表")
    except Exception as e:
        db.session.rollback()
        print(f"❌ 迁移失败: {e}")
