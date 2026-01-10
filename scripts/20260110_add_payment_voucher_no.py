# -*- coding: utf-8 -*-
"""
添加付款凭证号字段到 project_eos 表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def add_column():
    """添加 payment_voucher_no 字段"""

    # 检查字段是否已存在
    check_sql = """
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'project_eos'
    AND COLUMN_NAME = 'payment_voucher_no'
    """
    result = db.session.execute(text(check_sql))
    column_exists = result.fetchone()[0] > 0

    if column_exists:
        print("payment_voucher_no 字段已存在，跳过")
        return

    # 添加字段
    sql = """
    ALTER TABLE project_eos
    ADD COLUMN payment_voucher_no VARCHAR(50) NULL COMMENT '付款凭证号'
    AFTER payment_no
    """
    db.session.execute(text(sql))
    db.session.commit()
    print("payment_voucher_no 字段添加成功!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("添加付款凭证号字段")
        print("=" * 50)
        add_column()
