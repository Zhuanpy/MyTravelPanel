"""
创建/重建项目退款表（项目级退款凭证，按发票退款，含多条发票明细）
- project_refunds        退款主表（项目级）
- project_refund_items   退款明细表（一条退款下多张发票，含 invoice_id 与本次退款金额）

运行方式: python scripts/20260616_add_project_refunds.py

说明: 退款功能仍在迭代，明细结构从"按 REF"改为"按发票"，与旧表不兼容。
本脚本会先删除旧表（无正式业务数据），再按新模型重建。
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
