"""为 tour_group 表新增大人价格 / 小孩价格字段

背景：编辑团队信息中需要区分大人和小孩的价格，原来只有单一的 budget_per_person（人均预算）。
新增 adult_price（大人价格）、child_price（小孩价格）两列。

运行方式: python scripts/20260703_add_group_adult_child_price.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from App_new import create_app
from App_new.exts import db


def column_exists(table_name, column_name):
    """检查指定表是否已存在某列"""
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def main():
    app = create_app()
    with app.app_context():
        table = 'tour_group'
        to_add = [
            ('adult_price', "ALTER TABLE tour_group ADD COLUMN adult_price FLOAT NULL COMMENT '大人价格'"),
            ('child_price', "ALTER TABLE tour_group ADD COLUMN child_price FLOAT NULL COMMENT '小孩价格'"),
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
