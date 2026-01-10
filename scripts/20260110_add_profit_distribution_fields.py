# -*- coding: utf-8 -*-
"""
添加项目利润分配相关字段
- order_type: 订单类型
- operator_profit: 操作员利润
- sales_profit: 业务员利润
- company_profit: 公司利润
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

def run_migration():
    """执行迁移"""
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'project_headers'
                AND COLUMN_NAME = 'order_type'
            """))

            if result.fetchone():
                print("字段 order_type 已存在，跳过迁移")
                return

            # 添加 order_type 字段
            print("添加 order_type 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN order_type VARCHAR(20) NULL
                COMMENT '订单类型(小单/中单/大单等)'
            """))

            # 添加 operator_profit 字段
            print("添加 operator_profit 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN operator_profit DECIMAL(12, 2) NULL
                COMMENT '操作员利润'
            """))

            # 添加 sales_profit 字段
            print("添加 sales_profit 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN sales_profit DECIMAL(12, 2) NULL
                COMMENT '业务员利润'
            """))

            # 添加 company_profit 字段
            print("添加 company_profit 字段...")
            db.session.execute(text("""
                ALTER TABLE project_headers
                ADD COLUMN company_profit DECIMAL(12, 2) NULL
                COMMENT '公司利润'
            """))

            db.session.commit()
            print("迁移完成！")

        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {e}")
            raise

if __name__ == '__main__':
    run_migration()
