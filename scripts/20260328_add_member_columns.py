# -*- coding: utf-8 -*-
"""
给 project_members 表添加新字段：gender, date_of_birth, nationality,
passport_issuing_country, passport_expiry_date, airline_memberships

运行方式: python scripts/20260328_add_member_columns.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

COLUMNS = [
    ("gender", "VARCHAR(10) COMMENT '性别: male/female'"),
    ("date_of_birth", "DATE COMMENT '出生日期'"),
    ("nationality", "VARCHAR(50) COMMENT '国籍'"),
    ("passport_issuing_country", "VARCHAR(50) COMMENT '护照签发国'"),
    ("passport_expiry_date", "DATE COMMENT '护照有效期'"),
    ("airline_memberships", "TEXT COMMENT '航空会员信息，JSON格式'"),
]

with app.app_context():
    for col_name, col_def in COLUMNS:
        try:
            db.session.execute(db.text(
                f"ALTER TABLE project_members ADD COLUMN {col_name} {col_def}"
            ))
            db.session.commit()
            print(f'  已添加: {col_name}')
        except Exception as e:
            db.session.rollback()
            if 'Duplicate' in str(e):
                print(f'  已存在: {col_name}')
            else:
                print(f'  失败 {col_name}: {e}')

    print('\n完成！')
