# -*- coding: utf-8 -*-
"""航段表增加 seat 座位号字段"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    try:
        db.session.execute(db.text(
            "ALTER TABLE project_flight_segments ADD COLUMN seat VARCHAR(10) NULL COMMENT '座位号' AFTER baggage"
        ))
        db.session.commit()
        print("成功：project_flight_segments.seat")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate column' in str(e):
            print("跳过：project_flight_segments.seat 已存在")
        else:
            print(f"失败：project_flight_segments.seat - {e}")
