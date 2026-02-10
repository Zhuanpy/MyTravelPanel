# -*- coding: utf-8 -*-
"""
添加结算单(settlement_batch)功能的数据库迁移脚本

新增:
1. settlement_batches 表
2. project_headers 表新增 settlement_batch_id 字段

运行方式: python scripts/20260210_add_settlement_batch.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def migrate():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("添加结算单功能")
        print("=" * 60)

        # 第1步：创建 settlement_batches 表
        print("\n--- 第1步：创建 settlement_batches 表 ---")
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'settlement_batches'"
        )).scalar()

        if result == 0:
            db.session.execute(text("""
                CREATE TABLE settlement_batches (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    batch_number VARCHAR(30) NOT NULL UNIQUE COMMENT '结算单号',
                    settlement_date DATETIME NOT NULL COMMENT '结算日期',
                    settled_by VARCHAR(50) NOT NULL COMMENT '结算人',
                    project_count INT NOT NULL DEFAULT 0 COMMENT '项目数量',
                    total_profit DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '总利润',
                    total_operator_profit DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '操作员利润合计',
                    total_sales_profit DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '业务员利润合计',
                    total_company_profit DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '公司利润合计',
                    status VARCHAR(20) NOT NULL DEFAULT 'confirmed' COMMENT '状态(confirmed/cancelled)',
                    remarks TEXT NULL COMMENT '备注',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='结算单'
            """))
            db.session.commit()
            print("  settlement_batches 表创建完成")
        else:
            print("  settlement_batches 表已存在，跳过")

        # 第2步：给 project_headers 添加 settlement_batch_id 字段
        print("\n--- 第2步：添加 settlement_batch_id 字段 ---")
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'project_headers' "
            "AND column_name = 'settlement_batch_id'"
        )).scalar()

        if result == 0:
            db.session.execute(text(
                "ALTER TABLE project_headers ADD COLUMN settlement_batch_id INT NULL "
                "COMMENT '结算单ID'"
            ))
            db.session.execute(text(
                "ALTER TABLE project_headers ADD CONSTRAINT fk_project_settlement_batch "
                "FOREIGN KEY (settlement_batch_id) REFERENCES settlement_batches(id)"
            ))
            db.session.commit()
            print("  settlement_batch_id 字段添加完成")
        else:
            print("  settlement_batch_id 字段已存在，跳过")

        # 第3步：重置已结算但无结算单的项目
        print("\n--- 第3步：重置无结算单的已结算项目 ---")
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM project_headers "
            "WHERE is_settled = 1 AND settlement_batch_id IS NULL"
        )).scalar()

        if result > 0:
            db.session.execute(text(
                "UPDATE project_headers SET is_settled = 0, settled_at = NULL, settled_by = NULL "
                "WHERE is_settled = 1 AND settlement_batch_id IS NULL"
            ))
            db.session.commit()
            print(f"  已重置 {result} 个项目的结算状态（无关联结算单）")
        else:
            print("  没有需要重置的项目")

        print("\n✓ 迁移完成！")


if __name__ == '__main__':
    migrate()
