# -*- coding: utf-8 -*-
"""
创建银行交易匹配关联表
用于支持多对多匹配：
- 一笔银行转账 → 多个收款/EO
- 多笔银行转账 → 一个收款/EO
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

def create_table():
    """创建银行交易匹配关联表"""
    with app.app_context():
        # 检查表是否已存在
        check_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = 'bank_transaction_matches'
        """
        result = db.session.execute(db.text(check_sql)).fetchone()

        if result[0] > 0:
            print("表 bank_transaction_matches 已存在，跳过创建")
            return

        # 创建表
        create_sql = """
        CREATE TABLE bank_transaction_matches (
            id INT AUTO_INCREMENT PRIMARY KEY,
            transaction_id INT NOT NULL COMMENT '银行交易ID',
            match_type ENUM('receipt', 'eo') NOT NULL COMMENT '匹配类型：receipt=收款，eo=EO',
            match_id INT NOT NULL COMMENT '匹配记录ID（收款ID或EO ID）',
            allocated_amount DECIMAL(12,2) NOT NULL COMMENT '分配金额',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (transaction_id) REFERENCES bank_transactions(id) ON DELETE CASCADE,
            UNIQUE KEY unique_tx_match (transaction_id, match_type, match_id),
            INDEX idx_match_type_id (match_type, match_id),
            INDEX idx_transaction_id (transaction_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='银行交易匹配关联表（收入匹配收款，支出匹配EO）'
        """

        db.session.execute(db.text(create_sql))
        db.session.commit()
        print("表 bank_transaction_matches 创建成功！")

        # 迁移现有匹配数据
        migrate_existing_matches()


def migrate_existing_matches():
    """迁移现有的匹配数据到新表"""
    print("\n开始迁移现有匹配数据...")

    # 迁移收款匹配（从 matched_receipt_id）
    receipt_migrate_sql = """
    INSERT INTO bank_transaction_matches (transaction_id, match_type, match_id, allocated_amount, created_by)
    SELECT
        bt.id,
        'receipt',
        bt.matched_receipt_id,
        bt.amount,
        bt.confirmed_by
    FROM bank_transactions bt
    WHERE bt.matched_receipt_id IS NOT NULL
    ON DUPLICATE KEY UPDATE updated_at = NOW()
    """
    result1 = db.session.execute(db.text(receipt_migrate_sql))
    print(f"迁移收款匹配记录: {result1.rowcount} 条")

    # 迁移EO匹配（从 eo_id）
    eo_migrate_sql = """
    INSERT INTO bank_transaction_matches (transaction_id, match_type, match_id, allocated_amount, created_by)
    SELECT
        bt.id,
        'eo',
        bt.eo_id,
        bt.amount,
        bt.confirmed_by
    FROM bank_transactions bt
    WHERE bt.eo_id IS NOT NULL AND bt.eo_id != 0
    ON DUPLICATE KEY UPDATE updated_at = NOW()
    """
    result2 = db.session.execute(db.text(eo_migrate_sql))
    print(f"迁移EO匹配记录: {result2.rowcount} 条")

    db.session.commit()
    print("数据迁移完成！")


if __name__ == '__main__':
    create_table()
