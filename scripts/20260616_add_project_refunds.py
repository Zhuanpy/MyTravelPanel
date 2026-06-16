"""
创建/重建项目退款表（项目级退款凭证，含多条 REF 明细）
- project_refunds        退款主表（项目级）
- project_refund_items   退款明细表（一条退款下多个 REF）

运行方式: python scripts/20260616_add_project_refunds.py

说明: 旧版 project_refunds 为 REF 级单条结构（ref_id NOT NULL），与新结构不兼容。
本脚本会先删除旧表（退款功能刚上线、无业务数据），再按新模型重建。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db
# 导入模型以注册到 metadata
from App_new.business.projects.models.refund import ProjectRefund, ProjectRefundItem

app = create_app()


def main():
    with app.app_context():
        inspector = inspect(db.engine)

        # 先删子表再删主表（外键依赖）
        with db.engine.begin() as conn:
            if inspector.has_table('project_refund_items'):
                print('Dropping table project_refund_items ...')
                conn.execute(text('DROP TABLE project_refund_items'))
            if inspector.has_table('project_refunds'):
                print('Dropping old table project_refunds ...')
                conn.execute(text('DROP TABLE project_refunds'))

        print('Creating table project_refunds ...')
        ProjectRefund.__table__.create(bind=db.engine)
        print('Creating table project_refund_items ...')
        ProjectRefundItem.__table__.create(bind=db.engine)
        print('[OK] tables created: project_refunds, project_refund_items')


if __name__ == '__main__':
    main()
