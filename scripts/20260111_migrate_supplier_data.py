# -*- coding: utf-8 -*-
"""
迁移 supplier_data 表数据到 customer_companies 表
并清理旧的 supplier_data 表

使用方法:
    cd /var/www/MyTravelPanel
    source venv/bin/activate
    python scripts/20260111_migrate_supplier_data.py
"""

import pymysql
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_config():
    """从项目配置文件读取数据库配置"""
    try:
        from App_new.config import Config

        # 解析 SQLALCHEMY_DATABASE_URI
        uri = Config.SQLALCHEMY_DATABASE_URI
        uri = uri.replace('mysql+pymysql://', '')

        if '@' in uri:
            user_pass, host_db = uri.split('@', 1)
        else:
            raise ValueError("无法解析数据库URI")

        if ':' in user_pass:
            user, password = user_pass.split(':', 1)
        else:
            user = user_pass
            password = ''

        if '/' in host_db:
            host_port, db_rest = host_db.split('/', 1)
        else:
            raise ValueError("无法解析数据库名")

        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host = host_port
            port = '3306'

        if '?' in db_rest:
            database = db_rest.split('?')[0]
        else:
            database = db_rest

        return {
            'host': host,
            'port': int(port),
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4'
        }
    except Exception as e:
        print(f"✗ 读取配置失败: {e}")
        sys.exit(1)


def main():
    print("=" * 60)
    print("supplier_data 表迁移到 customer_companies")
    print("=" * 60)

    db_config = get_db_config()
    print(f"数据库: {db_config['user']}@{db_config['host']}/{db_config['database']}")

    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        print("✓ 数据库连接成功\n")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        sys.exit(1)

    db_name = db_config['database']

    # 步骤1：检查 supplier_data 表是否存在
    print("[1/4] 检查 supplier_data 表...")
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'supplier_data'
    """, (db_name,))

    if cursor.fetchone()['cnt'] == 0:
        print("  - supplier_data 表不存在，无需迁移")
        cursor.close()
        conn.close()
        print("\n迁移完成！")
        return

    # 步骤2：查看 supplier_data 表中的数据
    print("\n[2/4] 检查 supplier_data 表数据...")
    cursor.execute("SELECT COUNT(*) as cnt FROM supplier_data")
    count = cursor.fetchone()['cnt']
    print(f"  - 共有 {count} 条供应商记录")

    if count == 0:
        print("  - 表中无数据，跳过迁移")
    else:
        # 步骤3：迁移数据到 customer_companies
        print("\n[3/4] 迁移数据到 customer_companies...")

        # 获取所有 supplier_data 记录
        cursor.execute("SELECT * FROM supplier_data")
        suppliers = cursor.fetchall()

        migrated = 0
        skipped = 0

        for supplier in suppliers:
            # 检查是否已存在同名公司
            cursor.execute("""
                SELECT id FROM customer_companies WHERE name = %s
            """, (supplier['name'],))
            existing = cursor.fetchone()

            if existing:
                # 已存在，更新 is_supplier 标记
                cursor.execute("""
                    UPDATE customer_companies
                    SET is_supplier = 1,
                        country = COALESCE(country, %s),
                        region = COALESCE(region, %s)
                    WHERE id = %s
                """, (supplier.get('country'), supplier.get('region'), existing['id']))
                skipped += 1
                print(f"  - 跳过（已存在）: {supplier['name']}")
            else:
                # 不存在，插入新记录
                cursor.execute("""
                    INSERT INTO customer_companies
                    (name, address, contact_person, contact_info, status, country, region,
                     is_customer, is_supplier, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 1, %s)
                """, (
                    supplier['name'],
                    supplier.get('address'),
                    supplier.get('contact_person'),
                    supplier.get('contact_info'),
                    supplier.get('status', 'active'),
                    supplier.get('country'),
                    supplier.get('region'),
                    supplier.get('create_date')
                ))
                migrated += 1
                print(f"  ✓ 迁移: {supplier['name']}")

        conn.commit()
        print(f"\n  迁移完成: {migrated} 条新增, {skipped} 条已存在")

    # 步骤4：备份并删除旧表
    print("\n[4/4] 处理旧表...")

    # 先备份表（重命名）
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'supplier_data_backup'
    """, (db_name,))

    if cursor.fetchone()['cnt'] > 0:
        print("  - 删除旧备份表 supplier_data_backup")
        cursor.execute("DROP TABLE supplier_data_backup")

    print("  - 备份表: supplier_data → supplier_data_backup")
    cursor.execute("RENAME TABLE supplier_data TO supplier_data_backup")
    conn.commit()
    print("  ✓ 表已备份（如需恢复可使用 supplier_data_backup）")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print("\n后续步骤:")
    print("1. 验证数据迁移正确后，可删除备份表:")
    print("   DROP TABLE supplier_data_backup;")
    print("2. 重启 Flask 应用:")
    print("   sudo systemctl restart mytravel")


if __name__ == '__main__':
    main()
