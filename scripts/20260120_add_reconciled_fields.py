# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加已核对字段
- bank_transactions 表添加 is_reconciled, reconciled_at, reconciled_by 字段
- project_receipts 表添加 is_reconciled, reconciled_at, reconciled_by 字段

运行方式: python scripts/20260120_add_reconciled_fields.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def add_columns_if_not_exists(table_name, columns):
    """
    向表中添加列（如果不存在）

    Args:
        table_name: 表名
        columns: 列定义列表，每项为 (列名, 列定义SQL)
    """
    for col_name, col_definition in columns:
        # 检查列是否已存在
        check_sql = text(f"""
            SELECT COUNT(*) as cnt
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :col_name
        """)
        result = db.session.execute(check_sql, {'table_name': table_name, 'col_name': col_name}).fetchone()

        if result[0] == 0:
            # 列不存在，添加
            alter_sql = text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_definition}")
            db.session.execute(alter_sql)
            print(f"  + 添加列 {table_name}.{col_name}")
        else:
            print(f"  - 列 {table_name}.{col_name} 已存在，跳过")


def main():
    print("=" * 60)
    print("数据库迁移：添加已核对字段")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        try:
            # bank_transactions 表添加核对字段
            print("\n1. 处理 bank_transactions 表...")
            add_columns_if_not_exists('bank_transactions', [
                ('is_reconciled', "BOOLEAN NOT NULL DEFAULT FALSE COMMENT '已核对状态'"),
                ('reconciled_at', "DATETIME NULL COMMENT '核对时间'"),
                ('reconciled_by', "VARCHAR(50) NULL COMMENT '核对人'"),
            ])

            # project_receipts 表添加核对字段
            print("\n2. 处理 project_receipts 表...")
            add_columns_if_not_exists('project_receipts', [
                ('is_reconciled', "BOOLEAN NOT NULL DEFAULT FALSE COMMENT '已核对状态'"),
                ('reconciled_at', "DATETIME NULL COMMENT '核对时间'"),
                ('reconciled_by', "VARCHAR(50) NULL COMMENT '核对人'"),
            ])

            # project_eos 表添加核对字段
            print("\n3. 处理 project_eos 表...")
            add_columns_if_not_exists('project_eos', [
                ('is_reconciled', "BOOLEAN NOT NULL DEFAULT FALSE COMMENT '已核对状态'"),
                ('reconciled_at', "DATETIME NULL COMMENT '核对时间'"),
                ('reconciled_by', "VARCHAR(50) NULL COMMENT '核对人'"),
            ])

            # 提交事务
            db.session.commit()
            print("\n" + "=" * 60)
            print("迁移完成！")
            print("=" * 60)

        except Exception as e:
            db.session.rollback()
            print(f"\n错误：迁移失败 - {str(e)}")
            raise


if __name__ == '__main__':
    main()
