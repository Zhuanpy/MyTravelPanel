"""为 project_refunds 表新增两条收退款跟踪线的字段

背景：退款列表需要分别管理两个场景——
1) 供应商（航司/地接/酒店）有没有把钱退给我们；
2) 我们有没有把钱退给客户。

新增列：
- supplier_name / supplier_refund_status / supplier_refund_amount /
  supplier_refund_date / supplier_refund_remarks
- customer_refund_status / customer_refund_amount /
  customer_refund_date / customer_refund_remarks

兼容：已有退款记录状态默认 pending（未收到 / 未退款），不影响原有打印与统计逻辑。

运行方式: python scripts/20260726_add_refund_tracking_fields.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from App_new import create_app
from App_new.exts import db


def column_exists(table_name, column_name):
    inspector = inspect(db.engine)
    return column_name in [col['name'] for col in inspector.get_columns(table_name)]


def main():
    app = create_app()
    with app.app_context():
        table = 'project_refunds'

        inspector = inspect(db.engine)
        if not inspector.has_table(table):
            print(f"跳过：表 {table} 不存在，请先运行 scripts/20260616_add_project_refunds.py")
            return

        to_add = [
            # 跟踪线1：供应商退款（收）
            ('supplier_name',
             f"ALTER TABLE {table} ADD COLUMN supplier_name VARCHAR(100) NULL COMMENT '供应商名称'"),
            ('supplier_refund_status',
             f"ALTER TABLE {table} ADD COLUMN supplier_refund_status "
             f"ENUM('pending','partial','received','na') NOT NULL DEFAULT 'pending' "
             f"COMMENT '供应商退款状态: 未收到/部分收到/已收到/不涉及'"),
            ('supplier_refund_amount',
             f"ALTER TABLE {table} ADD COLUMN supplier_refund_amount DECIMAL(10,2) NULL DEFAULT 0 "
             f"COMMENT '已收到的供应商退款金额'"),
            ('supplier_refund_date',
             f"ALTER TABLE {table} ADD COLUMN supplier_refund_date DATE NULL COMMENT '收到供应商退款日期'"),
            ('supplier_refund_remarks',
             f"ALTER TABLE {table} ADD COLUMN supplier_refund_remarks VARCHAR(255) NULL COMMENT '供应商退款备注'"),
            # 跟踪线2：退给客户（付）
            ('customer_refund_status',
             f"ALTER TABLE {table} ADD COLUMN customer_refund_status "
             f"ENUM('pending','partial','paid') NOT NULL DEFAULT 'pending' "
             f"COMMENT '退客户状态: 未退款/部分退款/已退款'"),
            ('customer_refund_amount',
             f"ALTER TABLE {table} ADD COLUMN customer_refund_amount DECIMAL(10,2) NULL DEFAULT 0 "
             f"COMMENT '已退给客户的金额'"),
            ('customer_refund_date',
             f"ALTER TABLE {table} ADD COLUMN customer_refund_date DATE NULL COMMENT '退给客户日期'"),
            ('customer_refund_remarks',
             f"ALTER TABLE {table} ADD COLUMN customer_refund_remarks VARCHAR(255) NULL COMMENT '退客户备注'"),
        ]

        for column_name, ddl in to_add:
            if column_exists(table, column_name):
                print(f"跳过：{table}.{column_name} 已存在")
                continue
            try:
                db.session.execute(text(ddl))
                db.session.commit()
                print(f"成功：已新增列 {table}.{column_name}")
            except Exception as e:
                db.session.rollback()
                print(f"失败：新增列 {table}.{column_name} 出错：{e}")

        print('[OK] project_refunds 收退款跟踪字段处理完成')


if __name__ == '__main__':
    main()
