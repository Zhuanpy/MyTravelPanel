# -*- coding: utf-8 -*-
"""
为股东借款和还款表添加核对状态字段
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Adding reconciliation fields to shareholder loan tables")
    print("=" * 60)

    # Step 1: Add columns to shareholder_loans table
    print("\n[Step 1] Adding columns to shareholder_loans...")
    try:
        sql = """
        ALTER TABLE shareholder_loans
        ADD COLUMN is_reconciled TINYINT(1) DEFAULT 0 COMMENT '是否已与银行记录核对',
        ADD COLUMN reconciled_at DATETIME COMMENT '核对时间',
        ADD COLUMN reconciled_by VARCHAR(50) COMMENT '核对人'
        """
        db.session.execute(db.text(sql))
        db.session.commit()
        print("[OK] Columns added to shareholder_loans")
    except Exception as e:
        if 'Duplicate column' in str(e):
            print("[SKIP] Columns already exist in shareholder_loans")
        else:
            print(f"[WARN] Error: {e}")
        db.session.rollback()

    # Step 2: Add columns to shareholder_loan_repayments table
    print("\n[Step 2] Adding columns to shareholder_loan_repayments...")
    try:
        sql = """
        ALTER TABLE shareholder_loan_repayments
        ADD COLUMN is_reconciled TINYINT(1) DEFAULT 0 COMMENT '是否已与银行记录核对',
        ADD COLUMN reconciled_at DATETIME COMMENT '核对时间',
        ADD COLUMN reconciled_by VARCHAR(50) COMMENT '核对人'
        """
        db.session.execute(db.text(sql))
        db.session.commit()
        print("[OK] Columns added to shareholder_loan_repayments")
    except Exception as e:
        if 'Duplicate column' in str(e):
            print("[SKIP] Columns already exist in shareholder_loan_repayments")
        else:
            print(f"[WARN] Error: {e}")
        db.session.rollback()

    print("\n" + "=" * 60)
    print("[DONE] Migration completed")
    print("=" * 60)
