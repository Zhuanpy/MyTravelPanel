# -*- coding: utf-8 -*-
"""结算单公司结算：增加备注字段 payout_remarks

公司结算日期改成可编辑后，需要一个地方写清楚为什么改
（比如「8/25 银行转账，8/30 才补录」）。

单独成一个脚本，而不是加进 20260830_settlement_batch_payout.py：
那个脚本线上已经执行过，名字记在 .migration_history 里，部署时会被跳过，
往里面加新列不会生效——线上就是这么炸出 1054 Unknown column 的。
教训：已经跑过的迁移脚本不要再改，要加东西就新开一个。

运行方式: python scripts/20260830_settlement_batch_payout_remarks.py

幂等，可重复执行。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db

app = create_app()

TABLE = 'settlement_batches'
COLUMN = 'payout_remarks'
DDL = "TEXT NULL COMMENT '公司结算备注'"


def main():
    with app.app_context():
        with db.engine.begin() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(TABLE):
                print(f'[跳过] 表 {TABLE} 不存在')
                return

            existing = {c['name'] for c in inspector.get_columns(TABLE)}
            if COLUMN in existing:
                print(f'[已存在] {TABLE}.{COLUMN}')
            else:
                conn.execute(text(f'ALTER TABLE {TABLE} ADD COLUMN {COLUMN} {DDL}'))
                print(f'[新增] {TABLE}.{COLUMN}')

            total = conn.execute(text(f'SELECT COUNT(*) FROM {TABLE}')).scalar()
            print(f'[完成] {TABLE} 共 {total} 条记录')


if __name__ == '__main__':
    main()
