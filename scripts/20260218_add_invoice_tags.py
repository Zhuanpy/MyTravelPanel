# -*- coding: utf-8 -*-
"""
迁移脚本：为 project_invoices 表添加 tags 字段
运行方式：python scripts/20260218_add_invoice_tags.py
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
            "SHOW COLUMNS FROM project_invoices LIKE 'tags'"
        ))
        if result.fetchone():
            print("tags 字段已存在，跳过")
        else:
            db.session.execute(db.text(
                "ALTER TABLE project_invoices ADD COLUMN tags TEXT NULL COMMENT '标签(JSON数组)' AFTER paid_amount"
            ))
            db.session.commit()
            print("成功添加 tags 字段到 project_invoices 表")
    except Exception as e:
        db.session.rollback()
        print(f"迁移失败：{e}")
        sys.exit(1)
