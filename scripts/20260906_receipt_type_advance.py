# -*- coding: utf-8 -*-
"""客户预收款：project_receipts 增加 receipt_type 字段

业务流程是「先收钱、后开票」：客户对某个项目先付一笔钱，那时还没有发票；
后续项目开出发票，再从这笔预收里抵扣。

原来所有收款一律记「借银行 / 贷应收账款」，未开票就收的钱会把应收冲成负数，
而不是记成预收负债（科目表里的 2200 预收账款一直是空的）。加这个字段区分：

    payment  发票回款 —— 贷 1100 应收账款（默认，行为跟以前完全一样）
    advance  预收款   —— 贷 2200 预收账款

为什么用显式字段而不是「有没有关联发票」自动判断：本系统的收款分配表
（receipt_invoice_allocations）本身就不完整，按有无分配去猜，会把「还没来得及
关联发票」和「真的是预收」混成一堆，预收账款会变成未关联收款的垃圾桶。
性质由录入的人指定，才靠得住。

存量数据一律置 payment —— 用户确认现有业务没有预收款，历史分录也都是贷 1100，
保持一致，不回溯改账。

运行方式: python scripts/20260906_receipt_type_advance.py

幂等，可重复执行。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db

app = create_app()

TABLE = 'project_receipts'
COLUMN = 'receipt_type'
DDL = ("ENUM('payment','advance') NOT NULL DEFAULT 'payment' "
       "COMMENT '收款性质：payment=发票回款 / advance=预收款'")


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

            # 存量补齐（新增列已带 DEFAULT，这里只是防御性兜底）
            filled = conn.execute(text(
                f"UPDATE {TABLE} SET {COLUMN} = 'payment' WHERE {COLUMN} IS NULL"
            )).rowcount
            if filled:
                print(f'[回填] {filled} 条置为 payment')

            total = conn.execute(text(f'SELECT COUNT(*) FROM {TABLE}')).scalar()
            adv = conn.execute(text(
                f"SELECT COUNT(*) FROM {TABLE} WHERE {COLUMN} = 'advance'"
            )).scalar()
            print(f'[完成] {TABLE} 共 {total} 条，其中预收款 {adv} 条')


if __name__ == '__main__':
    main()
