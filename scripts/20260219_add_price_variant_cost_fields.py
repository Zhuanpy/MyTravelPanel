# -*- coding: utf-8 -*-
"""
迁移脚本：为 package_price_variant 表添加成本和利润字段
运行方式：python scripts/20260219_add_price_variant_cost_fields.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

COLUMNS = [
    ("cost_single_price", "FLOAT NULL COMMENT 'Single成本' AFTER currency"),
    ("cost_twin_price", "FLOAT NULL COMMENT 'Twin成本' AFTER cost_single_price"),
    ("cost_third_pax_price", "FLOAT NULL COMMENT '3rd Pax成本' AFTER cost_twin_price"),
    ("cost_child_no_bed_price", "FLOAT NULL COMMENT 'Child no Bed成本' AFTER cost_third_pax_price"),
    ("profit_per_person", "FLOAT NULL COMMENT '每人利润金额' AFTER cost_child_no_bed_price"),
]

with app.app_context():
    try:
        for col_name, col_def in COLUMNS:
            result = db.session.execute(db.text(
                f"SHOW COLUMNS FROM package_price_variant LIKE '{col_name}'"
            ))
            if result.fetchone():
                print(f"  {col_name} 已存在，跳过")
            else:
                db.session.execute(db.text(
                    f"ALTER TABLE package_price_variant ADD COLUMN {col_name} {col_def}"
                ))
                print(f"  添加 {col_name} 成功")

        db.session.commit()
        print("\n迁移完成！")

    except Exception as e:
        db.session.rollback()
        print(f"迁移失败：{e}")
        sys.exit(1)
