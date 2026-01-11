# -*- coding: utf-8 -*-
"""
纯 SQL 数据库迁移脚本（不依赖 Flask 应用）
直接使用 pymysql 连接数据库
"""

import pymysql
import os

# 数据库配置 - 根据服务器实际配置修改
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'mytravel'),
    'charset': 'utf8mb4'
}

def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = %s
        AND COLUMN_NAME = %s
    """, (DB_CONFIG['database'], table_name, column_name))
    return cursor.fetchone()[0] > 0

def table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = %s
    """, (DB_CONFIG['database'], table_name))
    return cursor.fetchone()[0] > 0

def add_column(cursor, table_name, column_name, column_def):
    """添加列"""
    if not column_exists(cursor, table_name, column_name):
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
        cursor.execute(sql)
        print(f"✓ {table_name}.{column_name} 已添加")
    else:
        print(f"- {table_name}.{column_name} 已存在")

def run_migration():
    """执行迁移"""
    print("=" * 50)
    print("数据库迁移脚本")
    print(f"数据库: {DB_CONFIG['database']}")
    print("=" * 50)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. customer_companies 表
        print("\n[1] customer_companies 表:")
        add_column(cursor, "customer_companies", "is_customer", "TINYINT(1) DEFAULT 1 COMMENT '是否为客户'")
        add_column(cursor, "customer_companies", "is_supplier", "TINYINT(1) DEFAULT 0 COMMENT '是否为供应商'")
        add_column(cursor, "customer_companies", "supplier_type_id", "INT DEFAULT NULL COMMENT '供应商类型ID'")
        add_column(cursor, "customer_companies", "country", "VARCHAR(100) DEFAULT NULL COMMENT '国家'")
        add_column(cursor, "customer_companies", "city", "VARCHAR(100) DEFAULT NULL COMMENT '城市'")
        add_column(cursor, "customer_companies", "region", "VARCHAR(100) DEFAULT NULL COMMENT '地区'")
        conn.commit()

        # 2. project_eos 表
        print("\n[2] project_eos 表:")
        add_column(cursor, "project_eos", "payment_record_id", "INT DEFAULT NULL COMMENT '付款记录ID'")
        conn.commit()

        # 3. supplier_payments 表
        print("\n[3] supplier_payments 表:")
        if not table_exists(cursor, "supplier_payments"):
            cursor.execute("""
                CREATE TABLE supplier_payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    payment_no VARCHAR(50) NOT NULL COMMENT '付款编号',
                    supplier_id INT DEFAULT NULL COMMENT '供应商ID',
                    payment_date DATE NOT NULL COMMENT '付款日期',
                    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '付款总金额',
                    currency VARCHAR(10) DEFAULT 'SGD' COMMENT '币种',
                    payment_source VARCHAR(20) DEFAULT 'bank' COMMENT '付款来源',
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
            conn.commit()
            print("✓ 表 supplier_payments 已创建")
        else:
            print("- 表 supplier_payments 已存在")

        print("\n" + "=" * 50)
        print("迁移完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # 如果命令行传入参数，可以覆盖默认配置
    import sys
    if len(sys.argv) > 1:
        print("用法: python 20260111_raw_migration.py")
        print("或设置环境变量: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME")
        print("\n当前配置:")
        for k, v in DB_CONFIG.items():
            if k == 'password':
                print(f"  {k}: {'*' * len(v) if v else '(空)'}")
            else:
                print(f"  {k}: {v}")
    else:
        run_migration()
