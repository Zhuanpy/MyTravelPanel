# -*- coding: utf-8 -*-
"""
添加 invoice_id 字段到 project_receipts 表
用于关联收款记录与发票
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from App_new.exts import db
from App_new.config import Config


def create_minimal_app():
    """创建最小化应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def add_invoice_id_column():
    """添加 invoice_id 字段"""
    app = create_minimal_app()

    with app.app_context():
        # 检查字段是否已存在
        check_sql = """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'project_receipts'
            AND COLUMN_NAME = 'invoice_id'
        """
        result = db.session.execute(db.text(check_sql))
        exists = result.scalar()

        if exists:
            print("invoice_id 字段已存在，跳过创建")
            return

        # 添加 invoice_id 字段
        alter_sql = """
            ALTER TABLE project_receipts
            ADD COLUMN invoice_id INT NULL
            COMMENT '关联发票ID'
            AFTER header_id
        """

        try:
            db.session.execute(db.text(alter_sql))
            db.session.commit()
            print("成功添加 invoice_id 字段")
        except Exception as e:
            db.session.rollback()
            print(f"添加字段失败: {e}")
            return

        # 添加外键约束
        fk_sql = """
            ALTER TABLE project_receipts
            ADD CONSTRAINT fk_receipt_invoice
            FOREIGN KEY (invoice_id)
            REFERENCES project_invoices(id)
            ON DELETE SET NULL
        """

        try:
            db.session.execute(db.text(fk_sql))
            db.session.commit()
            print("成功添加外键约束")
        except Exception as e:
            db.session.rollback()
            print(f"添加外键约束失败（可能已存在）: {e}")

        # 打印当前表结构
        print("\n当前 project_receipts 表结构:")
        desc_sql = "DESCRIBE project_receipts"
        result = db.session.execute(db.text(desc_sql))
        for row in result.fetchall():
            print(f"  {row[0]}: {row[1]}")


if __name__ == '__main__':
    add_invoice_id_column()
