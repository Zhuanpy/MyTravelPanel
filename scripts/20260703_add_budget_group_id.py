"""为 package_budget_header 表新增 group_id，用于多团组时按团组精确同步人数

背景：预算单人数与团队人数需要双向同步。原来只按 project_id 匹配，项目有多个团组时
会把所有团组/预算单拉平成同一人数。新增 group_id 后可精确对应到某个团组。

同时做一次回填：项目只有一个团组的预算单，group_id 直接指向该团组。

运行方式: python scripts/20260703_add_budget_group_id.py
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

        # 1) 新增列
        if column_exists(table, 'group_id'):
            print(f"跳过：{table}.group_id 已存在")
        else:
            try:
                db.session.execute(text(
                    "ALTER TABLE package_budget_header "
                    "ADD COLUMN group_id INT NULL COMMENT '关联团组ID'"))
                db.session.commit()
                print(f"成功：已新增列 {table}.group_id")
            except Exception as e:
                db.session.rollback()
                print(f"失败：新增列出错：{e}")
                return

        # 2) 回填：项目仅一个团组的预算单，group_id 指向该团组
        from App_new.business.tour.models.PackageBudget import BudgetHeader
        from App_new.business.tour.models.TourProject import TourGroup

        backfilled = 0
        budgets = BudgetHeader.query.filter(
            BudgetHeader.project_id.isnot(None),
            BudgetHeader.group_id.is_(None)).all()
        for b in budgets:
            groups = TourGroup.query.filter_by(project_id=b.project_id).all()
            if len(groups) == 1:
                b.group_id = groups[0].id
                backfilled += 1
        if backfilled:
            db.session.commit()
        print(f"回填完成：{backfilled} 个预算单已绑定唯一团组")


if __name__ == '__main__':
    main()
