# -*- coding: utf-8 -*-
"""结算单增加「公司结算」（分成发放）状态

结算单原本只有 status（confirmed/cancelled），表示这张单据算不算数，
不表示钱有没有发到员工手上。结算单确认后员工分成才算得出来，实际转账
通常晚几天，中间这段时间在系统里看不出区别，只能靠人记。

新增字段：
- payout_status  pending 待结算 / paid 已结算，默认 pending
- payout_date    标记为已结算的时间
- payout_by      标记人（改过日期后记的是最后一次操作人）
- payout_remarks 备注：实际转账日常常和标记那天不是同一天，日期可改，备注写清原因

已撤销的结算单不参与，保持 pending（页面显示「不适用」）。

运行方式: python scripts/20260830_settlement_batch_payout.py

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

NEW_COLUMNS = [
    ('payout_status', "VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '公司结算状态(pending待结算/paid已结算)'"),
    ('payout_date', "DATETIME NULL COMMENT '公司结算日期'"),
    ('payout_by', "VARCHAR(50) NULL COMMENT '公司结算操作人'"),
    ('payout_remarks', "TEXT NULL COMMENT '公司结算备注'"),
]


def main():
    with app.app_context():
        with db.engine.begin() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(TABLE):
                print(f'[跳过] 表 {TABLE} 不存在')
                return

            existing = {c['name'] for c in inspector.get_columns(TABLE)}

            for name, ddl in NEW_COLUMNS:
                if name in existing:
                    print(f'[已存在] {TABLE}.{name}')
                    continue
                conn.execute(text(f'ALTER TABLE {TABLE} ADD COLUMN {name} {ddl}'))
                print(f'[新增] {TABLE}.{name}')

            # 历史单据一律按「未结算」处理：无法回溯当初有没有发放，
            # 标成已结算会掩盖真实待办，宁可让人手工确认一遍
            filled = conn.execute(text(
                f"UPDATE {TABLE} SET payout_status = 'pending' WHERE payout_status IS NULL"
            )).rowcount
            if filled:
                print(f'[回填] {filled} 条历史记录置为 pending')

            total = conn.execute(text(f'SELECT COUNT(*) FROM {TABLE}')).scalar()
            pending = conn.execute(text(
                f"SELECT COUNT(*) FROM {TABLE} WHERE payout_status = 'pending'"
            )).scalar()
            print(f'[完成] 共 {total} 张结算单，其中 {pending} 张待公司结算')


if __name__ == '__main__':
    main()
