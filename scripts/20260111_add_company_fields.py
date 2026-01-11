# -*- coding: utf-8 -*-
"""
添加数据库缺失的字段
解决服务器报错: Unknown column
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

def add_column(table_name, col_name, col_def):
    """添加单个列"""
    try:
        # 检查列是否存在
        check_sql = f"""
        SELECT COUNT(*) as cnt FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = '{table_name}'
        AND COLUMN_NAME = '{col_name}'
        """
        result = db.session.execute(db.text(check_sql)).fetchone()

        if result[0] == 0:
            # 列不存在，添加它
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"
            db.session.execute(db.text(alter_sql))
            db.session.commit()
            print(f"✓ {table_name}.{col_name} 已添加")
        else:
            print(f"- {table_name}.{col_name} 已存在")

    except Exception as e:
        print(f"✗ {table_name}.{col_name} 失败: {e}")
        db.session.rollback()

def create_table_if_not_exists(table_name, create_sql):
    """创建表（如果不存在）"""
    try:
        check_sql = f"""
        SELECT COUNT(*) as cnt FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = '{table_name}'
        """
        result = db.session.execute(db.text(check_sql)).fetchone()

        if result[0] == 0:
            db.session.execute(db.text(create_sql))
            db.session.commit()
            print(f"✓ 表 {table_name} 已创建")
        else:
            print(f"- 表 {table_name} 已存在")

    except Exception as e:
        print(f"✗ 创建表 {table_name} 失败: {e}")
        db.session.rollback()

def run_migration():
    """运行所有迁移"""
    with app.app_context():
        print("=" * 50)
        print("开始数据库迁移...")
        print("=" * 50)

        # 1. customer_companies 表新字段
        print("\n[1] customer_companies 表:")
        add_column("customer_companies", "is_customer", "TINYINT(1) DEFAULT 1 COMMENT '是否为客户'")
        add_column("customer_companies", "is_supplier", "TINYINT(1) DEFAULT 0 COMMENT '是否为供应商'")
        add_column("customer_companies", "supplier_type_id", "INT DEFAULT NULL COMMENT '供应商类型ID'")
        add_column("customer_companies", "country", "VARCHAR(100) DEFAULT NULL COMMENT '国家'")
        add_column("customer_companies", "city", "VARCHAR(100) DEFAULT NULL COMMENT '城市'")
        add_column("customer_companies", "region", "VARCHAR(100) DEFAULT NULL COMMENT '地区'")

        # 2. project_eos 表新字段
        print("\n[2] project_eos 表:")
        add_column("project_eos", "payment_record_id", "INT DEFAULT NULL COMMENT '付款记录ID'")

        # 3. 创建 supplier_payments 表
        print("\n[3] supplier_payments 表:")
        create_table_if_not_exists("supplier_payments", """
            CREATE TABLE supplier_payments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                payment_no VARCHAR(50) NOT NULL COMMENT '付款编号',
                supplier_id INT DEFAULT NULL COMMENT '供应商ID',
                payment_date DATE NOT NULL COMMENT '付款日期',
                total_amount DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '付款总金额',
                currency VARCHAR(10) DEFAULT 'SGD' COMMENT '币种',
                payment_source VARCHAR(20) DEFAULT 'bank' COMMENT '付款来源: bank/prepayment',
                payment_voucher_no VARCHAR(100) DEFAULT NULL COMMENT '付款凭证号',
                prepayment_amount DECIMAL(12,2) DEFAULT 0 COMMENT '使用预付金额',
                eo_count INT DEFAULT 0 COMMENT 'EO数量',
                status VARCHAR(20) DEFAULT 'confirmed' COMMENT '状态',
                remarks TEXT COMMENT '备注',
                created_by VARCHAR(100) DEFAULT NULL COMMENT '创建人',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_payment_no (payment_no),
                INDEX idx_supplier_id (supplier_id),
                INDEX idx_payment_date (payment_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商付款记录表'
        """)

        print("\n" + "=" * 50)
        print("迁移完成！")
        print("=" * 50)

if __name__ == '__main__':
    run_migration()
