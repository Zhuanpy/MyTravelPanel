"""为 package_budget_items 表新增 is_enabled（是否计入费用计算）

背景：报价过程中经常需要临时把某条明细（如某个可选景点、某段用车）拿掉看总价，
过一会儿又要加回来。以前只能删掉重录，价格就丢了。
新增 is_enabled：关掉后该项不计入任何合计（人均、团总价、分类统计、报价单），
价格字段原样保留，随时可以开回来。

兼容：新列 NOT NULL DEFAULT 1，存量数据全部回填为 1（启用），行为不变。

运行方式: python scripts/20260803_add_budget_item_is_enabled.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from App_new import create_app
from App_new.exts import db


TABLE = 'package_budget_items'
COLUMN = 'is_enabled'


def column_exists(table_name, column_name):
    inspector = inspect(db.engine)
    return column_name in [col['name'] for col in inspector.get_columns(table_name)]


def main():
    app = create_app()
    with app.app_context():
        if column_exists(TABLE, COLUMN):
            print(f"跳过：{TABLE}.{COLUMN} 已存在")
        else:
            ddl = (
                f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} TINYINT(1) NOT NULL DEFAULT 1 "
                f"COMMENT '是否计入费用计算：0=临时禁用，价格保留但不计入任何合计'"
            )
            try:
                db.session.execute(text(ddl))
                db.session.commit()
                print(f"成功：已新增列 {TABLE}.{COLUMN}")
            except Exception as e:
                db.session.rollback()
                print(f"失败：新增列 {TABLE}.{COLUMN} 出错：{e}")
                return

        # 回填：历史数据一律按启用处理（DEFAULT 1 已覆盖新增场景，这里兜底 NULL）
        try:
            result = db.session.execute(
                text(f"UPDATE {TABLE} SET {COLUMN} = 1 WHERE {COLUMN} IS NULL")
            )
            db.session.commit()
            print(f"回填完成：{result.rowcount} 行 {COLUMN} 由 NULL 置为 1")
        except Exception as e:
            db.session.rollback()
            print(f"回填失败：{e}")
            return

        total = db.session.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar()
        disabled = db.session.execute(
            text(f"SELECT COUNT(*) FROM {TABLE} WHERE {COLUMN} = 0")
        ).scalar()
        print(f"当前：明细共 {total} 条，其中禁用 {disabled} 条")


if __name__ == '__main__':
    main()