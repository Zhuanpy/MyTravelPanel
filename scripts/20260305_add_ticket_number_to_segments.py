# -*- coding: utf-8 -*-
"""航段表增加 ticket_number 和 pnr 字段"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    # 添加 ticket_number 字段
    try:
        db.session.execute(db.text("""
            ALTER TABLE project_flight_segments
            ADD COLUMN ticket_number VARCHAR(50) NULL COMMENT '电子客票号'
            AFTER cabin_code
        """))
        db.session.commit()
        print("成功：添加 ticket_number 字段")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate column' in str(e):
            print("ticket_number 字段已存在，跳过")
        else:
            print(f"失败：{e}")
            raise

    # 添加 pnr 字段
    try:
        db.session.execute(db.text("""
            ALTER TABLE project_flight_segments
            ADD COLUMN pnr VARCHAR(10) NULL COMMENT 'PNR编码'
            AFTER ticket_number
        """))
        db.session.commit()
        print("成功：添加 pnr 字段")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate column' in str(e):
            print("pnr 字段已存在，跳过")
        else:
            print(f"失败：{e}")
            raise
