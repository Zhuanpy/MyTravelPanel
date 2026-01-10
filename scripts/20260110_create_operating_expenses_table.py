# -*- coding: utf-8 -*-
"""
创建运营费用表 (operating_expenses)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def create_table():
    """创建 operating_expenses 表"""

    # 检查表是否存在
    check_sql = """
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'operating_expenses'
    """
    result = db.session.execute(text(check_sql))
    table_exists = result.fetchone()[0] > 0

    if table_exists:
        print("operating_expenses 表已存在，跳过创建")
        return

    print("创建 operating_expenses 表...")

    create_sql = """
    CREATE TABLE operating_expenses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        expense_number VARCHAR(30) UNIQUE NOT NULL COMMENT '费用单编号',

        -- 费用信息
        expense_date DATE NOT NULL COMMENT '费用日期',
        expense_account_id INT NOT NULL COMMENT '费用科目ID',

        -- 金额信息
        amount DECIMAL(12, 2) NOT NULL COMMENT '金额',
        currency VARCHAR(3) NOT NULL DEFAULT 'SGD' COMMENT '货币',

        -- 付款信息
        payment_method ENUM('cash', 'bank_transfer', 'cheque', 'credit_card', 'other')
                       NOT NULL DEFAULT 'bank_transfer' COMMENT '付款方式',
        bank_account_id INT NULL COMMENT '付款银行科目ID',
        payment_reference VARCHAR(100) NULL COMMENT '付款参考号',

        -- 收款方信息
        payee_name VARCHAR(100) NULL COMMENT '收款方名称',
        payee_account VARCHAR(100) NULL COMMENT '收款方账号',

        -- 描述和备注
        description VARCHAR(200) NOT NULL COMMENT '费用描述',
        remarks TEXT NULL COMMENT '备注',

        -- 附件
        attachment_path VARCHAR(255) NULL COMMENT '附件路径',

        -- 状态
        status ENUM('draft', 'confirmed', 'paid', 'cancelled')
               NOT NULL DEFAULT 'draft' COMMENT '状态',

        -- 日记账关联
        journal_entry_id INT NULL COMMENT '日记账分录ID',

        -- 时间信息
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        created_by VARCHAR(50) NULL COMMENT '创建人',

        -- 外键
        FOREIGN KEY (expense_account_id) REFERENCES project_chart_of_accounts(id),
        FOREIGN KEY (bank_account_id) REFERENCES project_chart_of_accounts(id),
        FOREIGN KEY (journal_entry_id) REFERENCES project_journal_entries(id),

        INDEX idx_expense_date (expense_date),
        INDEX idx_status (status),
        INDEX idx_expense_account (expense_account_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='运营费用表'
    """

    db.session.execute(text(create_sql))
    db.session.commit()

    print("operating_expenses 表创建成功!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("创建运营费用表")
        print("=" * 50)
        create_table()
