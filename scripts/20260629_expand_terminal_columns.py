"""
扩展 project_flight_segments 航站楼字段长度
departure_terminal / arrival_terminal: VARCHAR(10) → VARCHAR(50)

原因: 部分数据源返回航站楼为名称(如 "Changle Intl.")而非 "T1" 短代码,
原 VARCHAR(10) 不足导致插入报错 (Data too long for column 'arrival_terminal')。

运行方式: python scripts/20260629_expand_terminal_columns.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    try:
        db.session.execute(db.text(
            'ALTER TABLE project_flight_segments '
            'MODIFY COLUMN departure_terminal VARCHAR(50) COMMENT "出发航站楼"'
        ))
        db.session.execute(db.text(
            'ALTER TABLE project_flight_segments '
            'MODIFY COLUMN arrival_terminal VARCHAR(50) COMMENT "到达航站楼"'
        ))
        db.session.commit()
        print('OK: departure_terminal / arrival_terminal 字段已扩展到 VARCHAR(50)')
    except Exception as e:
        db.session.rollback()
        print(f'失败: {e}')
