# -*- coding: utf-8 -*-
"""
创建 payment_vouchers 表（结算凭证表）
并为 project_headers 表添加 payment_voucher_id 外键字段
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def create_payment_vouchers_table():
    """创建 payment_vouchers 表"""

    # 检查表是否已存在
    check_sql = """
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'payment_vouchers'
    """
    result = db.session.execute(text(check_sql))
    table_exists = result.fetchone()[0] > 0

    if table_exists:
        print("payment_vouchers 表已存在，跳过创建")
        return

    # 创建表
    create_sql = """
    CREATE TABLE payment_vouchers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        voucher_no VARCHAR(50) NOT NULL UNIQUE COMMENT '凭证号码',
        settle_date DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '结算日期',
        settled_by VARCHAR(50) NULL COMMENT '结算人',
        project_count INT DEFAULT 0 COMMENT '项目数量',
        total_selling DECIMAL(15, 2) DEFAULT 0 COMMENT '总销售金额',
        total_cost DECIMAL(15, 2) DEFAULT 0 COMMENT '总成本',
        total_profit DECIMAL(15, 2) DEFAULT 0 COMMENT '总利润',
        total_operator_profit DECIMAL(15, 2) DEFAULT 0 COMMENT '操作员利润合计',
        total_sales_profit DECIMAL(15, 2) DEFAULT 0 COMMENT '业务员利润合计',
        total_company_profit DECIMAL(15, 2) DEFAULT 0 COMMENT '公司利润合计',
        remarks TEXT NULL COMMENT '备注',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='付款凭证/结算凭证表';
    """
    db.session.execute(text(create_sql))
    db.session.commit()
    print("payment_vouchers 表创建成功!")


def add_payment_voucher_id_column():
    """为 project_headers 表添加 payment_voucher_id 外键字段"""

    # 检查字段是否已存在
    check_sql = """
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'project_headers'
    AND COLUMN_NAME = 'payment_voucher_id'
    """
    result = db.session.execute(text(check_sql))
    column_exists = result.fetchone()[0] > 0

    if column_exists:
        print("payment_voucher_id 字段已存在，跳过")
        return

    # 添加字段
    sql = """
    ALTER TABLE project_headers
    ADD COLUMN payment_voucher_id INT NULL COMMENT '付款凭证ID'
    AFTER settled_by
    """
    db.session.execute(text(sql))
    db.session.commit()
    print("payment_voucher_id 字段添加成功!")

    # 添加外键约束
    try:
        fk_sql = """
        ALTER TABLE project_headers
        ADD CONSTRAINT fk_project_headers_payment_voucher
        FOREIGN KEY (payment_voucher_id) REFERENCES payment_vouchers(id)
        ON DELETE SET NULL
        """
        db.session.execute(text(fk_sql))
        db.session.commit()
        print("外键约束添加成功!")
    except Exception as e:
        print(f"添加外键约束失败（可能已存在）: {e}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("创建结算凭证相关数据库结构")
        print("=" * 50)

        print("\n1. 创建 payment_vouchers 表...")
        create_payment_vouchers_table()

        print("\n2. 添加 payment_voucher_id 字段到 project_headers 表...")
        add_payment_voucher_id_column()

        print("\n" + "=" * 50)
        print("数据库迁移完成!")
        print("=" * 50)
