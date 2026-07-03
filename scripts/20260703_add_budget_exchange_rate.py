"""为 package_budget_header 表新增最终货币 + 固定汇率字段

背景：预算可能以人民币录入，最终需按固定汇率统一换算成新币（或反之）报价。
新增 target_currency（最终统一货币）、exchange_rate（固定汇率：1 SGD = ? CNY）两列。
兼容：两列为空时按原逻辑（不换算）显示，行为不变。

运行方式: python scripts/20260703_add_budget_exchange_rate.py
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
        table = 'package_budget_header'
        to_add = [
            ('target_currency', "ALTER TABLE package_budget_header ADD COLUMN target_currency VARCHAR(10) NULL COMMENT '最终统一货币'"),
            ('exchange_rate', "ALTER TABLE package_budget_header ADD COLUMN exchange_rate FLOAT NULL COMMENT '固定汇率:1 SGD=?CNY'"),
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


if __name__ == '__main__':
    main()
