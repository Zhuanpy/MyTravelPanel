#!/usr/bin/env python3
"""
创建收款表的数据库迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from App.exts import db
from App.models.projects.BookingProject import ProjectReceipt
from sqlalchemy import text

def create_receipt_table():
    """创建收款表"""
    with app.app_context():
        try:
            # 创建表的SQL语句
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS project_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_number VARCHAR(30) UNIQUE NOT NULL,
                ref_id INTEGER NOT NULL,
                header_id INTEGER NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'SGD' NOT NULL,
                payment_method ENUM('cash', 'bank_transfer', 'credit_card', 'cheque', 'other') NOT NULL,
                payment_date DATE NOT NULL,
                payer_name VARCHAR(100),
                payer_contact VARCHAR(50),
                payer_company VARCHAR(100),
                bank_name VARCHAR(100),
                account_number VARCHAR(50),
                transaction_id VARCHAR(100),
                status ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'pending' NOT NULL,
                remarks TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                FOREIGN KEY (ref_id) REFERENCES project_refs(id),
                FOREIGN KEY (header_id) REFERENCES project_headers(id)
            );
            """
            
            # 执行创建表
            db.session.execute(text(create_table_sql))
            db.session.commit()
            
            print("✅ 收款表创建成功！")
            
            # 创建索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_receipt_ref_id ON project_receipts(ref_id);",
                "CREATE INDEX IF NOT EXISTS idx_receipt_header_id ON project_receipts(header_id);",
                "CREATE INDEX IF NOT EXISTS idx_receipt_payment_date ON project_receipts(payment_date);",
                "CREATE INDEX IF NOT EXISTS idx_receipt_status ON project_receipts(status);"
            ]
            
            for index_sql in indexes:
                db.session.execute(text(index_sql))
            
            db.session.commit()
            print("✅ 收款表索引创建成功！")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 创建收款表失败: {str(e)}")
            raise

if __name__ == "__main__":
    print("开始创建收款表...")
    create_receipt_table()
    print("收款表创建完成！") 