# -*- coding: utf-8 -*-
"""
迁移脚本：为门票变体表添加 date_type 字段
用途：区分开放票（open）和固定日期票（fixed）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    try:
        db.session.execute(db.text("""
            ALTER TABLE products_ticket_variant
            ADD COLUMN date_type VARCHAR(20) DEFAULT 'open'
            COMMENT '日期类型：open开放票/fixed固定日期票'
        """))
        db.session.commit()
        print("成功：已添加 date_type 字段到 products_ticket_variant 表")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate column' in str(e):
            print("字段已存在，跳过")
        else:
            print(f"错误：{e}")
            raise
