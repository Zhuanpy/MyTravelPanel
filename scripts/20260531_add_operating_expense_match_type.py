# -*- coding: utf-8 -*-
"""
迁移脚本：为 bank_transaction_matches.match_type 枚举增加 'operating_expense' 值
（用于银行支出对比中匹配"运营费用"）
运行方式: python scripts/20260531_add_operating_expense_match_type.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from sqlalchemy import text
from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    TABLE = 'bank_transaction_matches'
    COLUMN = 'match_type'

    # 读取当前列定义，检查是否已含 operating_expense
    col = db.session.execute(text(
        """
        SELECT COLUMN_TYPE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c
        """
    ), {'t': TABLE, 'c': COLUMN}).scalar()

    if col and 'operating_expense' in col:
        print(f"枚举已包含 operating_expense，无需迁移。当前: {col}")
    else:
        try:
            db.session.execute(text(
                """
                ALTER TABLE bank_transaction_matches
                MODIFY COLUMN match_type
                ENUM('receipt','eo','payment','prepayment','loan_borrow','loan_repay','operating_expense')
                NOT NULL COMMENT '匹配类型'
                """
            ))
            db.session.commit()
            print("成功为 match_type 增加 operating_expense 枚举值。")
        except Exception as e:
            db.session.rollback()
            print(f"迁移失败：{e}")
            raise
