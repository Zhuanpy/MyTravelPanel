# -*- coding: utf-8 -*-
"""
创建收款-发票分配表 receipt_invoice_allocations
用于实现一笔收款对应多张发票的多对多关系
"""

import sys
import os

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


def create_allocation_table():
    """创建收款-发票分配表"""
    app = create_minimal_app()

    with app.app_context():
        # 检查表是否已存在
        check_sql = """
            SELECT COUNT(*)
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'receipt_invoice_allocations'
        """
        result = db.session.execute(db.text(check_sql))
        exists = result.scalar()

        if exists:
            print("receipt_invoice_allocations 表已存在，跳过创建")
            return

        # 创建表
        create_sql = """
            CREATE TABLE receipt_invoice_allocations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                receipt_id INT NOT NULL COMMENT '收款记录ID',
                invoice_id INT NOT NULL COMMENT '发票ID',
                allocated_amount DECIMAL(10, 2) NOT NULL COMMENT '分配到该发票的金额',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_allocation_receipt FOREIGN KEY (receipt_id)
                    REFERENCES project_receipts(id) ON DELETE CASCADE,
                CONSTRAINT fk_allocation_invoice FOREIGN KEY (invoice_id)
                    REFERENCES project_invoices(id) ON DELETE CASCADE,
                CONSTRAINT uq_receipt_invoice UNIQUE (receipt_id, invoice_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收款-发票分配表'
        """

        try:
            db.session.execute(db.text(create_sql))
            db.session.commit()
            print("成功创建 receipt_invoice_allocations 表")
        except Exception as e:
            db.session.rollback()
            print(f"创建表失败: {e}")
            return

        # 创建索引
        index_sqls = [
            "CREATE INDEX idx_allocation_receipt ON receipt_invoice_allocations(receipt_id)",
            "CREATE INDEX idx_allocation_invoice ON receipt_invoice_allocations(invoice_id)"
        ]

        for sql in index_sqls:
            try:
                db.session.execute(db.text(sql))
                db.session.commit()
                print(f"索引创建成功")
            except Exception as e:
                print(f"创建索引失败（可能已存在）: {e}")

        # 打印表结构
        print("\n当前表结构:")
        desc_sql = "DESCRIBE receipt_invoice_allocations"
        result = db.session.execute(db.text(desc_sql))
        for row in result.fetchall():
            print(f"  {row[0]}: {row[1]}")

        print("\n创建完成!")


if __name__ == '__main__':
    create_allocation_table()
