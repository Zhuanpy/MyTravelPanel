"""
为 products_ticket_variant 表添加有效期和库存字段
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

ALTER_STATEMENTS = [
    "ALTER TABLE products_ticket_variant ADD COLUMN valid_until DATE NULL COMMENT '有效截止日期'",
    "ALTER TABLE products_ticket_variant ADD COLUMN total_stock INT NULL COMMENT '总库存数量'",
    "ALTER TABLE products_ticket_variant ADD COLUMN sold_count INT DEFAULT 0 COMMENT '已售数量'",
]

with app.app_context():
    for stmt in ALTER_STATEMENTS:
        col_name = stmt.split('ADD COLUMN ')[1].split(' ')[0]
        try:
            db.session.execute(db.text(stmt))
            db.session.commit()
            print(f'[OK] 添加列 {col_name}')
        except Exception as e:
            db.session.rollback()
            if 'Duplicate column' in str(e):
                print(f'[SKIP] 列 {col_name} 已存在')
            else:
                print(f'[ERROR] {col_name}: {e}')

    print('\n迁移完成！')
