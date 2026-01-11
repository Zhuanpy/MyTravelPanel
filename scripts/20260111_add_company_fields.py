# -*- coding: utf-8 -*-
"""
添加 customer_companies 表的新字段
解决服务器报错: Unknown column 'customer_companies.is_customer'
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

def add_columns():
    """添加缺失的列"""
    with app.app_context():
        # 检查并添加缺失的列
        columns_to_add = [
            ("is_customer", "TINYINT(1) DEFAULT 1 COMMENT '是否为客户'"),
            ("is_supplier", "TINYINT(1) DEFAULT 0 COMMENT '是否为供应商'"),
            ("supplier_type_id", "INT DEFAULT NULL COMMENT '供应商类型ID'"),
            ("country", "VARCHAR(100) DEFAULT NULL COMMENT '国家'"),
            ("city", "VARCHAR(100) DEFAULT NULL COMMENT '城市'"),
            ("region", "VARCHAR(100) DEFAULT NULL COMMENT '地区'"),
        ]

        for col_name, col_def in columns_to_add:
            try:
                # 检查列是否存在
                check_sql = f"""
                SELECT COUNT(*) as cnt FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'customer_companies'
                AND COLUMN_NAME = '{col_name}'
                """
                result = db.session.execute(db.text(check_sql)).fetchone()

                if result[0] == 0:
                    # 列不存在，添加它
                    alter_sql = f"ALTER TABLE customer_companies ADD COLUMN {col_name} {col_def}"
                    db.session.execute(db.text(alter_sql))
                    db.session.commit()
                    print(f"✓ 已添加列: {col_name}")
                else:
                    print(f"- 列已存在: {col_name}")

            except Exception as e:
                print(f"✗ 添加列 {col_name} 失败: {e}")
                db.session.rollback()

        print("\n完成！")

if __name__ == '__main__':
    add_columns()
