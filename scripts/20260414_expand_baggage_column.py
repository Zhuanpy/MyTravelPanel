"""
扩展 project_flight_segments.baggage 字段长度
VARCHAR(20) → VARCHAR(50)

运行方式: python scripts/20260414_expand_baggage_column.py
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
            'ALTER TABLE project_flight_segments MODIFY COLUMN baggage VARCHAR(50) COMMENT "行李额"'
        ))
        db.session.commit()
        print('OK: baggage 字段已扩展到 VARCHAR(50)')
    except Exception as e:
        db.session.rollback()
        print(f'失败: {e}')
