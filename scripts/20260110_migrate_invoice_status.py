# -*- coding: utf-8 -*-
"""
发票状态迁移脚本 - 使用 Flask 应用配置
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def run_migration():
    print('=' * 50)
    print('发票状态迁移')
    print('=' * 50)

    try:
        # 0. 检查当前状态
        print('\n0. 检查当前数据状态...')
        result = db.session.execute(text("SELECT status, COUNT(*) FROM project_invoices GROUP BY status"))
        rows = result.fetchall()
        print('   当前 status 分布:')
        for row in rows:
            print(f'     {row[0]}: {row[1]} 条')

        # 1. 检查 payment_status 列是否存在
        print('\n1. 检查 payment_status 列...')
        check_sql = """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'project_invoices'
        AND COLUMN_NAME = 'payment_status'
        """
        result = db.session.execute(text(check_sql))
        has_payment_status = result.fetchone() is not None

        if not has_payment_status:
            print('   添加 payment_status 列...')
            db.session.execute(text(
                "ALTER TABLE project_invoices ADD COLUMN payment_status ENUM('unpaid', 'partial_paid', 'paid') DEFAULT 'unpaid' NOT NULL AFTER status"
            ))
            db.session.commit()
            print('   -> payment_status 列已添加')
        else:
            print('   -> payment_status 列已存在')

        # 2. 检查当前 status 列的 ENUM 值
        print('\n2. 检查 status 列的 ENUM 值...')
        check_enum_sql = """
        SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'project_invoices'
        AND COLUMN_NAME = 'status'
        """
        result = db.session.execute(text(check_enum_sql))
        enum_type = result.fetchone()[0]
        print(f'   当前 status 类型: {enum_type}')

        # 如果 status 包含旧的值，需要迁移
        if 'draft' in enum_type or 'sent' in enum_type or 'paid' in enum_type or 'overdue' in enum_type:
            print('\n3. 迁移 payment_status 数据...')

            # 临时扩展 ENUM 类型（如果需要）
            if 'confirmed' not in enum_type:
                db.session.execute(text(
                    "ALTER TABLE project_invoices MODIFY COLUMN status ENUM('draft', 'sent', 'paid', 'partial_paid', 'overdue', 'cancelled', 'confirmed') DEFAULT 'confirmed' NOT NULL"
                ))
                db.session.commit()

            # draft, sent, overdue -> unpaid
            result = db.session.execute(text("UPDATE project_invoices SET payment_status='unpaid' WHERE status IN ('draft', 'sent', 'overdue')"))
            print(f'   设置 unpaid: {result.rowcount} 条')

            # partial_paid -> partial_paid
            result = db.session.execute(text("UPDATE project_invoices SET payment_status='partial_paid' WHERE status='partial_paid'"))
            print(f'   设置 partial_paid: {result.rowcount} 条')

            # paid -> paid
            result = db.session.execute(text("UPDATE project_invoices SET payment_status='paid' WHERE status='paid'"))
            print(f'   设置 paid: {result.rowcount} 条')

            db.session.commit()

            # 4. 将所有非 cancelled 的 status 改为 confirmed
            print('\n4. 更新 status 值为 confirmed...')
            result = db.session.execute(text("UPDATE project_invoices SET status='confirmed' WHERE status NOT IN ('confirmed', 'cancelled')"))
            print(f'   更新为 confirmed: {result.rowcount} 条')
            db.session.commit()

            # 5. 修改 status 列的 ENUM 类型为最终版本
            print('\n5. 修改 status 列为最终 ENUM 类型...')
            db.session.execute(text(
                "ALTER TABLE project_invoices MODIFY COLUMN status ENUM('confirmed', 'cancelled') DEFAULT 'confirmed' NOT NULL"
            ))
            db.session.commit()
            print('   -> status 列已更新')
        else:
            print('\n3. status 列已经是新格式，跳过迁移')

        # 6. 验证结果
        print('\n6. 验证结果...')
        result = db.session.execute(text('SELECT status, payment_status, COUNT(*) as cnt FROM project_invoices GROUP BY status, payment_status'))
        rows = result.fetchall()
        print('   当前状态分布:')
        for row in rows:
            print(f'     status={row[0]}, payment_status={row[1]}: {row[2]} 条')

        print('\n' + '=' * 50)
        print('迁移完成!')
        print('=' * 50)

    except Exception as e:
        print(f'\n错误: {e}')
        db.session.rollback()
        raise


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
