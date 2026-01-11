# -*- coding: utf-8 -*-
"""
创建预付账款相关表
- supplier_prepayments: 预付账款主表
- prepayment_usages: 预付账款使用明细表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    # 创建供应商预付账款表
    create_prepayments_sql = """
    CREATE TABLE IF NOT EXISTS supplier_prepayments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        prepayment_number VARCHAR(30) NOT NULL UNIQUE COMMENT '预付编号',
        supplier_id INT NOT NULL COMMENT '供应商ID',
        amount DECIMAL(12,2) NOT NULL COMMENT '充值金额',
        currency VARCHAR(3) NOT NULL DEFAULT 'SGD' COMMENT '货币',
        payment_date DATE NOT NULL COMMENT '充值日期',
        payment_method ENUM('bank_transfer', 'credit_card', 'cash', 'paynow', 'other') NOT NULL DEFAULT 'bank_transfer' COMMENT '支付方式',
        balance_amount DECIMAL(12,2) NOT NULL COMMENT '剩余余额',
        bank_account_id INT NULL COMMENT '银行账户科目ID',
        prepayment_account_id INT NULL COMMENT '预付账款科目ID',
        status ENUM('draft', 'confirmed', 'partial_used', 'consumed', 'cancelled') NOT NULL DEFAULT 'draft' COMMENT '状态',
        journal_entry_id INT NULL COMMENT '日记账分录ID',
        remarks TEXT NULL COMMENT '备注',
        reference VARCHAR(100) NULL COMMENT '参考号/交易号',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        created_by VARCHAR(50) NULL COMMENT '创建人',

        INDEX idx_supplier_id (supplier_id),
        INDEX idx_status (status),
        INDEX idx_payment_date (payment_date),

        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
        FOREIGN KEY (bank_account_id) REFERENCES project_chart_of_accounts(id) ON DELETE SET NULL,
        FOREIGN KEY (prepayment_account_id) REFERENCES project_chart_of_accounts(id) ON DELETE SET NULL,
        FOREIGN KEY (journal_entry_id) REFERENCES project_journal_entries(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商预付账款表';
    """

    # 创建预付账款使用明细表
    create_usages_sql = """
    CREATE TABLE IF NOT EXISTS prepayment_usages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        prepayment_id INT NOT NULL COMMENT '预付记录ID',
        eo_id INT NULL COMMENT '关联EO ID',
        ref_id INT NULL COMMENT '关联REF ID',
        amount DECIMAL(12,2) NOT NULL COMMENT '使用金额',
        usage_date DATE NOT NULL COMMENT '使用日期',
        description VARCHAR(200) NULL COMMENT '使用说明',
        journal_entry_id INT NULL COMMENT '日记账分录ID',
        status ENUM('pending', 'confirmed', 'reversed') NOT NULL DEFAULT 'pending' COMMENT '状态',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        created_by VARCHAR(50) NULL COMMENT '创建人',

        INDEX idx_prepayment_id (prepayment_id),
        INDEX idx_eo_id (eo_id),
        INDEX idx_ref_id (ref_id),
        INDEX idx_usage_date (usage_date),

        FOREIGN KEY (prepayment_id) REFERENCES supplier_prepayments(id) ON DELETE CASCADE,
        FOREIGN KEY (eo_id) REFERENCES project_eos(id) ON DELETE SET NULL,
        FOREIGN KEY (ref_id) REFERENCES project_refs(id) ON DELETE SET NULL,
        FOREIGN KEY (journal_entry_id) REFERENCES project_journal_entries(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预付账款使用明细表';
    """

    try:
        # 执行创建表SQL
        print("正在创建 supplier_prepayments 表...")
        db.session.execute(db.text(create_prepayments_sql))
        print("supplier_prepayments 表创建成功!")

        print("正在创建 prepayment_usages 表...")
        db.session.execute(db.text(create_usages_sql))
        print("prepayment_usages 表创建成功!")

        db.session.commit()
        print("\n所有表创建完成!")

    except Exception as e:
        db.session.rollback()
        print(f"创建失败: {str(e)}")

        # 如果表已存在，提示用户
        if "already exists" in str(e).lower() or "1050" in str(e):
            print("表可能已存在，跳过创建")
