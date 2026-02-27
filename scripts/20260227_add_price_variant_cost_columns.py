"""
为 package_price_variant 表添加成本价格和利润字段
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

ALTER_STATEMENTS = [
    "ALTER TABLE package_price_variant ADD COLUMN cost_single_price FLOAT NULL COMMENT 'Single成本'",
    "ALTER TABLE package_price_variant ADD COLUMN cost_twin_price FLOAT NULL COMMENT 'Twin成本'",
    "ALTER TABLE package_price_variant ADD COLUMN cost_third_pax_price FLOAT NULL COMMENT '3rd Pax成本'",
    "ALTER TABLE package_price_variant ADD COLUMN cost_child_no_bed_price FLOAT NULL COMMENT 'Child no Bed成本'",
    "ALTER TABLE package_price_variant ADD COLUMN profit_per_person FLOAT NULL COMMENT '每人利润金额'",
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
