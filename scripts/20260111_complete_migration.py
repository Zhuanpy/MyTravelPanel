# -*- coding: utf-8 -*-
"""
完整数据库迁移脚本 - 不依赖 Flask 应用
直接使用 pymysql 连接数据库执行迁移

使用方法:
    # 方法1：设置环境变量
    export DB_HOST=localhost
    export DB_USER=root
    export DB_PASSWORD=your_password
    export DB_NAME=mytravel
    python scripts/20260111_complete_migration.py

    # 方法2：直接修改下面的 DB_CONFIG
"""

import pymysql
import os
import sys

# ============ 数据库配置 - 请根据实际情况修改 ============
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'mytravel'),
    'charset': 'utf8mb4'
}
# ========================================================

def get_connection():
    """获取数据库连接"""
    print(f"连接数据库: {DB_CONFIG['host']}/{DB_CONFIG['database']}")
    return pymysql.connect(**DB_CONFIG)

def column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (DB_CONFIG['database'], table_name, column_name))
    return cursor.fetchone()[0] > 0

def table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
    """, (DB_CONFIG['database'], table_name))
    return cursor.fetchone()[0] > 0

def add_column(cursor, conn, table_name, column_name, column_def):
    """安全添加列"""
    if column_exists(cursor, table_name, column_name):
        print(f"  - {table_name}.{column_name} 已存在，跳过")
        return False

    try:
        sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {column_def}"
        cursor.execute(sql)
        conn.commit()
        print(f"  ✓ {table_name}.{column_name} 已添加")
        return True
    except Exception as e:
        print(f"  ✗ {table_name}.{column_name} 添加失败: {e}")
        conn.rollback()
        return False

def run_migration():
    """执行完整迁移"""
    print("=" * 60)
    print("MyTravelPanel 数据库迁移脚本")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # ==========================================
        # 1. customer_companies 表 - 添加新字段
        # ==========================================
        print("\n[1/3] customer_companies 表迁移...")

        add_column(cursor, conn, "customer_companies", "is_customer",
                   "TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否为客户'")

        add_column(cursor, conn, "customer_companies", "is_supplier",
                   "TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否为供应商'")

        add_column(cursor, conn, "customer_companies", "supplier_type_id",
                   "INT DEFAULT NULL COMMENT '供应商类型ID'")

        add_column(cursor, conn, "customer_companies", "country",
                   "VARCHAR(50) DEFAULT NULL COMMENT '国家'")

        add_column(cursor, conn, "customer_companies", "city",
                   "VARCHAR(50) DEFAULT NULL COMMENT '城市'")

        add_column(cursor, conn, "customer_companies", "region",
                   "VARCHAR(50) DEFAULT NULL COMMENT '地区'")

        # ==========================================
        # 2. project_eos 表 - 添加付款记录关联字段
        # ==========================================
        print("\n[2/3] project_eos 表迁移...")

        add_column(cursor, conn, "project_eos", "payment_record_id",
                   "INT DEFAULT NULL COMMENT '付款记录ID'")

        # ==========================================
        # 3. supplier_payments 表 - 创建新表
        # ==========================================
        print("\n[3/3] supplier_payments 表迁移...")

        if table_exists(cursor, "supplier_payments"):
            print("  - 表 supplier_payments 已存在，跳过创建")
        else:
            create_sql = """
            CREATE TABLE `supplier_payments` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `payment_no` VARCHAR(30) NOT NULL COMMENT '付款编号',
                `supplier_id` INT DEFAULT NULL COMMENT '供应商ID',
                `payment_date` DATE NOT NULL COMMENT '付款日期',
                `total_amount` DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '付款总金额',
                `currency` VARCHAR(3) NOT NULL DEFAULT 'SGD' COMMENT '货币',
                `payment_source` ENUM('bank', 'prepayment', 'mixed') NOT NULL DEFAULT 'bank' COMMENT '付款来源',
                `payment_voucher_no` VARCHAR(50) DEFAULT NULL COMMENT '银行付款凭证号',
                `bank_account_id` INT DEFAULT NULL COMMENT '付款银行账户',
                `prepayment_amount` DECIMAL(12,2) DEFAULT 0.00 COMMENT '使用预付账款金额',
                `eo_count` INT DEFAULT 0 COMMENT '包含EO数量',
                `status` ENUM('draft', 'confirmed', 'cancelled') NOT NULL DEFAULT 'confirmed' COMMENT '状态',
                `remarks` TEXT COMMENT '备注',
                `journal_entry_id` INT DEFAULT NULL COMMENT '日记账分录ID',
                `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                `created_by` VARCHAR(50) DEFAULT NULL COMMENT '创建人',
                UNIQUE KEY `uk_payment_no` (`payment_no`),
                INDEX `idx_supplier_id` (`supplier_id`),
                INDEX `idx_payment_date` (`payment_date`),
                INDEX `idx_status` (`status`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商付款记录表'
            """
            try:
                cursor.execute(create_sql)
                conn.commit()
                print("  ✓ 表 supplier_payments 已创建")
            except Exception as e:
                print(f"  ✗ 创建表失败: {e}")
                conn.rollback()

        # ==========================================
        # 完成
        # ==========================================
        print("\n" + "=" * 60)
        print("迁移完成！")
        print("=" * 60)
        print("\n请重启 Flask 应用以加载新的模型。")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        print("\n当前数据库配置:")
        for k, v in DB_CONFIG.items():
            if k == 'password':
                print(f"  {k}: {'*' * len(str(v)) if v else '(空)'}")
            else:
                print(f"  {k}: {v}")
    else:
        run_migration()
