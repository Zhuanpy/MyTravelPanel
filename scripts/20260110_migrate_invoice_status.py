# -*- coding: utf-8 -*-
"""
独立发票状态迁移脚本 - 不依赖 Flask 应用
直接运行: py scripts/migrate_invoice_standalone.py
"""

import pymysql

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '***REMOVED***',
    'database': 'travelindustry',
    'charset': 'utf8mb4'
}

def run_migration():
    print('=' * 50)
    print('发票状态迁移 (独立脚本)')
    print('=' * 50)

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # 0. 检查当前状态
        print('\n0. 检查当前数据状态...')
        cursor.execute("SELECT status, COUNT(*) FROM project_invoices GROUP BY status")
        rows = cursor.fetchall()
        print('   当前 status 分布:')
        for row in rows:
            print(f'     {row[0]}: {row[1]} 条')

        # 1. 先恢复 status 列为包含所有值的 ENUM（临时）
        print('\n1. 临时扩展 status ENUM 类型...')
        try:
            cursor.execute(
                "ALTER TABLE project_invoices MODIFY COLUMN status ENUM('draft', 'sent', 'paid', 'partial_paid', 'overdue', 'cancelled', 'confirmed') DEFAULT 'confirmed' NOT NULL"
            )
            conn.commit()
            print('   status 列已扩展')
        except Exception as e:
            print(f'   警告: {e}')

        # 2. 添加 payment_status 列
        print('\n2. 添加 payment_status 列...')
        try:
            cursor.execute(
                "ALTER TABLE project_invoices ADD COLUMN payment_status ENUM('unpaid', 'partial_paid', 'paid') DEFAULT 'unpaid' NOT NULL AFTER status"
            )
            conn.commit()
            print('   payment_status 列已添加')
        except pymysql.err.OperationalError as e:
            if 'Duplicate column' in str(e):
                print('   payment_status 列已存在')
            else:
                raise e

        # 3. 迁移现有数据的 payment_status
        print('\n3. 迁移 payment_status 数据...')

        # draft, sent, overdue -> 设置 payment_status 为 unpaid
        cursor.execute("UPDATE project_invoices SET payment_status='unpaid' WHERE status IN ('draft', 'sent', 'overdue')")
        print(f'   设置 unpaid: {cursor.rowcount} 条')

        # partial_paid -> 设置 payment_status 为 partial_paid
        cursor.execute("UPDATE project_invoices SET payment_status='partial_paid' WHERE status='partial_paid'")
        print(f'   设置 partial_paid: {cursor.rowcount} 条')

        # paid -> 设置 payment_status 为 paid
        cursor.execute("UPDATE project_invoices SET payment_status='paid' WHERE status='paid'")
        print(f'   设置 paid: {cursor.rowcount} 条')

        conn.commit()
        print('   payment_status 迁移完成')

        # 4. 将所有非 cancelled 的 status 改为 confirmed
        print('\n4. 更新 status 值为 confirmed...')
        cursor.execute("UPDATE project_invoices SET status='confirmed' WHERE status NOT IN ('confirmed', 'cancelled')")
        print(f'   更新为 confirmed: {cursor.rowcount} 条')
        conn.commit()

        # 5. 修改 status 列的 ENUM 类型为最终版本
        print('\n5. 修改 status 列为最终 ENUM 类型...')
        try:
            cursor.execute(
                "ALTER TABLE project_invoices MODIFY COLUMN status ENUM('confirmed', 'cancelled') DEFAULT 'confirmed' NOT NULL"
            )
            conn.commit()
            print('   status 列已更新为新的 ENUM 类型')
        except Exception as e:
            print(f'   警告: {e}')

        # 6. 验证结果
        print('\n6. 验证结果...')
        cursor.execute('SELECT status, payment_status, COUNT(*) as cnt FROM project_invoices GROUP BY status, payment_status')
        rows = cursor.fetchall()
        print('   当前状态分布:')
        for row in rows:
            print(f'     status={row[0]}, payment_status={row[1]}: {row[2]} 条')

        print('\n' + '=' * 50)
        print('迁移完成!')
        print('=' * 50)

    except Exception as e:
        print(f'\n错误: {e}')
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    run_migration()
