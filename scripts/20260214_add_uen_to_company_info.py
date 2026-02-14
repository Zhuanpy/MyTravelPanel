"""
给 company_info 表添加 uen 字段
运行方式: python scripts/20260214_add_uen_to_company_info.py
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
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'company_info' AND COLUMN_NAME = 'uen'"
        ))
        exists = result.scalar()

        if exists:
            print("uen 字段已存在，跳过")
        else:
            db.session.execute(text(
                "ALTER TABLE company_info ADD COLUMN uen VARCHAR(20) NULL COMMENT 'UEN (Unique Entity Number)' AFTER ta_license"
            ))
            db.session.commit()
            print("成功添加 uen 字段")

    except Exception as e:
        db.session.rollback()
        print(f"执行失败: {e}")
