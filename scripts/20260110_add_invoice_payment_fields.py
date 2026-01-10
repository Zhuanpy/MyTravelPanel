# -*- coding: utf-8 -*-
"""
添加 project_invoices 表的付款状态字段
- payment_status: 付款状态
- paid_amount: 已付金额
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

def migrate():
    """执行迁移"""

    # 检查字段是否存在
    check_sql = """
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'project_invoices'
    AND COLUMN_NAME IN ('payment_status', 'paid_amount')
    """

    result = db.session.execute(text(check_sql))
    existing_columns = [row[0] for row in result.fetchall()]

    print(f"现有字段: {existing_columns}")

    # 添加 payment_status 字段
    if 'payment_status' not in existing_columns:
        print("添加 payment_status 字段...")
        add_payment_status_sql = """
        ALTER TABLE project_invoices
        ADD COLUMN payment_status ENUM('unpaid', 'partial_paid', 'paid')
        NOT NULL DEFAULT 'unpaid'
        COMMENT '付款状态'
        AFTER status
        """
        db.session.execute(text(add_payment_status_sql))
        print("  -> payment_status 字段添加成功")
    else:
        print("  -> payment_status 字段已存在，跳过")

    # 添加 paid_amount 字段
    if 'paid_amount' not in existing_columns:
        print("添加 paid_amount 字段...")
        add_paid_amount_sql = """
        ALTER TABLE project_invoices
        ADD COLUMN paid_amount DECIMAL(10,2)
        NOT NULL DEFAULT 0
        COMMENT '已付金额'
        AFTER payment_status
        """
        db.session.execute(text(add_paid_amount_sql))
        print("  -> paid_amount 字段添加成功")
    else:
        print("  -> paid_amount 字段已存在，跳过")

    db.session.commit()
    print("\n迁移完成!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("添加 Invoice 付款状态字段")
        print("=" * 50)
        migrate()
