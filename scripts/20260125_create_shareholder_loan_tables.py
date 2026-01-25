# -*- coding: utf-8 -*-
"""创建股东借款相关表"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Creating shareholder loan tables")
    print("=" * 60)

    # 检查表是否已存在
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    # 创建 shareholder_loans 表
    if 'shareholder_loans' not in existing_tables:
        sql_loans = """
        CREATE TABLE shareholder_loans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            loan_number VARCHAR(50) NOT NULL UNIQUE COMMENT 'loan number',
            amount DECIMAL(12, 2) NOT NULL COMMENT 'loan amount',
            loan_date DATE NOT NULL COMMENT 'loan date',
            description VARCHAR(200) COMMENT 'description',
            remarks TEXT COMMENT 'remarks',
            repaid_amount DECIMAL(12, 2) DEFAULT 0 COMMENT 'repaid amount',
            status VARCHAR(20) DEFAULT 'active' COMMENT 'status: active/partial/repaid/cancelled',
            journal_entry_id INT COMMENT 'journal entry id',
            bank_account_id INT COMMENT 'bank account id',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50),
            updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (journal_entry_id) REFERENCES project_journal_entries(id),
            FOREIGN KEY (bank_account_id) REFERENCES project_chart_of_accounts(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='shareholder loans';
        """
        db.session.execute(db.text(sql_loans))
        print("[OK] Created table shareholder_loans")
    else:
        print("[SKIP] Table shareholder_loans already exists")

    # 创建 shareholder_loan_repayments 表
    if 'shareholder_loan_repayments' not in existing_tables:
        sql_repayments = """
        CREATE TABLE shareholder_loan_repayments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            repayment_number VARCHAR(50) NOT NULL UNIQUE COMMENT 'repayment number',
            total_amount DECIMAL(12, 2) NOT NULL COMMENT 'total repayment amount',
            repayment_date DATE NOT NULL COMMENT 'repayment date',
            description VARCHAR(200) COMMENT 'description',
            remarks TEXT COMMENT 'remarks',
            status VARCHAR(20) DEFAULT 'posted' COMMENT 'status: posted/cancelled',
            journal_entry_id INT COMMENT 'journal entry id',
            bank_account_id INT COMMENT 'bank account id',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50),
            FOREIGN KEY (journal_entry_id) REFERENCES project_journal_entries(id),
            FOREIGN KEY (bank_account_id) REFERENCES project_chart_of_accounts(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='shareholder loan repayments';
        """
        db.session.execute(db.text(sql_repayments))
        print("[OK] Created table shareholder_loan_repayments")
    else:
        print("[SKIP] Table shareholder_loan_repayments already exists")

    # 创建 shareholder_loan_repayment_details 表
    if 'shareholder_loan_repayment_details' not in existing_tables:
        sql_details = """
        CREATE TABLE shareholder_loan_repayment_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            repayment_id INT NOT NULL,
            loan_id INT NOT NULL,
            amount DECIMAL(12, 2) NOT NULL COMMENT 'repayment amount for this loan',
            FOREIGN KEY (repayment_id) REFERENCES shareholder_loan_repayments(id),
            FOREIGN KEY (loan_id) REFERENCES shareholder_loans(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='repayment details';
        """
        db.session.execute(db.text(sql_details))
        print("[OK] Created table shareholder_loan_repayment_details")
    else:
        print("[SKIP] Table shareholder_loan_repayment_details already exists")

    db.session.commit()
    print("\n" + "=" * 60)
    print("Database tables created successfully")
    print("=" * 60)
