# -*- coding: utf-8 -*-
"""乘客表增加 passport_number，航段表增加 airline_name/baggage/departure_terminal/arrival_terminal"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db

app = create_app()

# 需要添加的字段：(表名, 列定义, AFTER哪个列)
columns = [
    ('project_flight_passengers', 'passport_number VARCHAR(20) NULL COMMENT "护照号"', 'pnr'),
    ('project_flight_segments', 'airline_name VARCHAR(50) NULL COMMENT "航司名称"', 'flight_number'),
    ('project_flight_segments', 'departure_terminal VARCHAR(10) NULL COMMENT "出发航站楼"', 'arrival_time'),
    ('project_flight_segments', 'arrival_terminal VARCHAR(10) NULL COMMENT "到达航站楼"', 'departure_terminal'),
    ('project_flight_segments', 'baggage VARCHAR(20) NULL COMMENT "行李额"', 'cabin_code'),
]

with app.app_context():
    for table, col_def, after_col in columns:
        col_name = col_def.split()[0]
        try:
            db.session.execute(db.text(
                f"ALTER TABLE {table} ADD COLUMN {col_def} AFTER {after_col}"
            ))
            db.session.commit()
            print(f"成功：{table}.{col_name}")
        except Exception as e:
            db.session.rollback()
            if 'Duplicate column' in str(e):
                print(f"跳过：{table}.{col_name} 已存在")
            else:
                print(f"失败：{table}.{col_name} - {e}")
