# -*- coding: utf-8 -*-
"""为付款和预付款表添加核对状态字段，扩展匹配类型枚举"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=" * 70)
    print("数据库迁移：添加核对字段和扩展匹配类型")
    print("=" * 70)

    # 1. supplier_payments 添加核对字段
    print("\n【1】supplier_payments 添加核对字段...")
    try:
        db.session.execute(text("""
            ALTER TABLE supplier_payments
            ADD COLUMN is_reconciled TINYINT(1) DEFAULT 0 COMMENT '是否已核对',
            ADD COLUMN reconciled_at DATETIME NULL COMMENT '核对时间',
            ADD COLUMN reconciled_by VARCHAR(50) NULL COMMENT '核对人'
        """))
        db.session.commit()
        print("  成功添加 is_reconciled, reconciled_at, reconciled_by")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate column' in str(e) or 'already exists' in str(e):
            print(f"  字段已存在，跳过")
        else:
            print(f"  错误: {e}")

    # 2. supplier_prepayments 添加核对字段
    print("\n【2】supplier_prepayments 添加核对字段...")
    try:
        db.session.execute(text("""
            ALTER TABLE supplier_prepayments
            ADD COLUMN is_reconciled TINYINT(1) DEFAULT 0 COMMENT '是否已核对',
            ADD COLUMN reconciled_at DATETIME NULL COMMENT '核对时间',
            ADD COLUMN reconciled_by VARCHAR(50) NULL COMMENT '核对人'
        """))
        db.session.commit()
        print("  成功添加 is_reconciled, reconciled_at, reconciled_by")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate column' in str(e) or 'already exists' in str(e):
            print(f"  字段已存在，跳过")
        else:
            print(f"  错误: {e}")

    # 3. bank_transaction_matches 扩展 match_type 枚举
    print("\n【3】bank_transaction_matches 扩展 match_type 枚举...")
    try:
        db.session.execute(text("""
            ALTER TABLE bank_transaction_matches
            MODIFY COLUMN match_type ENUM('receipt', 'eo', 'payment', 'prepayment')
            NOT NULL COMMENT '匹配类型：receipt=收款，eo=EO，payment=付款，prepayment=预付款'
        """))
        db.session.commit()
        print("  成功扩展 match_type 枚举为 ('receipt', 'eo', 'payment', 'prepayment')")
    except Exception as e:
        db.session.rollback()
        print(f"  错误: {e}")

    print("\n" + "=" * 70)
    print("迁移完成")
    print("=" * 70)
