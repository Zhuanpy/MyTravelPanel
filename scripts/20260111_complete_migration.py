#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整数据库迁移脚本
直接使用 pymysql，不依赖 Flask

使用方法:
    python scripts/20260111_complete_migration.py
"""

import pymysql
import sys

# ============================================
# 数据库配置 - 请修改为服务器实际配置
# ============================================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # 在这里填入数据库密码
    'database': 'mytravel',
    'charset': 'utf8mb4'
}
# ============================================


def main():
    print("=" * 50)
    print("MyTravelPanel 数据库迁移")
    print("=" * 50)

    # 连接数据库
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print(f"✓ 已连接到数据库: {DB_CONFIG['database']}")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        print("\n请检查 DB_CONFIG 配置是否正确")
        sys.exit(1)

    db_name = DB_CONFIG['database']

    # 定义需要添加的列
    columns_to_add = [
        # (表名, 列名, 列定义)
        ("customer_companies", "is_customer", "TINYINT(1) DEFAULT 1"),
        ("customer_companies", "is_supplier", "TINYINT(1) DEFAULT 0"),
        ("customer_companies", "supplier_type_id", "INT DEFAULT NULL"),
        ("customer_companies", "country", "VARCHAR(50) DEFAULT NULL"),
        ("customer_companies", "city", "VARCHAR(50) DEFAULT NULL"),
        ("customer_companies", "region", "VARCHAR(50) DEFAULT NULL"),
        ("project_eos", "payment_record_id", "INT DEFAULT NULL"),
    ]

    print("\n[1/2] 添加缺失的列...")

    for table, column, definition in columns_to_add:
        # 检查列是否存在
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """, (db_name, table, column))

        exists = cursor.fetchone()[0] > 0

        if exists:
            print(f"  - {table}.{column} 已存在")
        else:
            try:
                sql = f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}"
                cursor.execute(sql)
                conn.commit()
                print(f"  ✓ {table}.{column} 已添加")
            except Exception as e:
                print(f"  ✗ {table}.{column} 失败: {e}")

    print("\n[2/2] 创建 supplier_payments 表...")

    # 检查表是否存在
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'supplier_payments'
    """, (db_name,))

    table_exists = cursor.fetchone()[0] > 0

    if table_exists:
        print("  - 表 supplier_payments 已存在")
    else:
        try:
            cursor.execute("""
                CREATE TABLE `supplier_payments` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `payment_no` VARCHAR(30) NOT NULL,
                    `supplier_id` INT DEFAULT NULL,
                    `payment_date` DATE NOT NULL,
                    `total_amount` DECIMAL(12,2) DEFAULT 0.00,
                    `currency` VARCHAR(3) DEFAULT 'SGD',
                    `payment_source` VARCHAR(20) DEFAULT 'bank',
                    `payment_voucher_no` VARCHAR(50) DEFAULT NULL,
                    `bank_account_id` INT DEFAULT NULL,
                    `prepayment_amount` DECIMAL(12,2) DEFAULT 0.00,
                    `eo_count` INT DEFAULT 0,
                    `status` VARCHAR(20) DEFAULT 'confirmed',
                    `remarks` TEXT,
                    `journal_entry_id` INT DEFAULT NULL,
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    `created_by` VARCHAR(50) DEFAULT NULL,
                    UNIQUE KEY `uk_payment_no` (`payment_no`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            print("  ✓ 表 supplier_payments 已创建")
        except Exception as e:
            print(f"  ✗ 创建表失败: {e}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 50)
    print("迁移完成！请重启 Flask 应用")
    print("=" * 50)


if __name__ == '__main__':
    main()
