# -*- coding: utf-8 -*-
"""下线「结算凭证」(PaymentVoucher)，统一到结算单 (SettlementBatch)

原来有两套并行的结算记录：
- 项目结算页「批量结算」→ 生成凭证，写 project_headers.payment_voucher_id
- 业绩结算页「结算」    → 生成结算单，写 project_headers.settlement_batch_id

同一件事两种记录，结果是从项目结算页结算的项目在结算单列表里看不到，
而且旧的「取消结算」只清项目上的关联、不更新凭证自身的 project_count，
凭证数字会越来越假（下线时 5 张凭证里有 3 张的项目数已经对不上）。

本脚本分两阶段，默认只做第一阶段：

阶段一（默认）：为每张仍有关联项目的凭证补建一张结算单，把项目挂过去。
    不这么做的话，这批历史项目下线后就查不到结算来源了。
    结算单号沿用凭证的结算日期生成，备注注明来源凭证号。

阶段二（--drop）：确认没有项目再依赖凭证后，删除 payment_vouchers 表
    和 project_headers.payment_voucher_id 列。**不可逆**，请先跑完阶段一
    并在页面上核对无误再执行。

运行方式:
    python scripts/20260830_retire_payment_voucher.py           # 阶段一：迁移
    python scripts/20260830_retire_payment_voucher.py --drop    # 阶段二：删表删列

前置：需先执行 20260830_settlement_batch_payout.py。阶段一幂等，可重复执行。
"""

import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db

app = create_app()


def _batch_number_for(conn, settle_date):
    """按凭证的结算日期生成结算单号，序号接着当天已有的往下排"""
    prefix = 'SB-%s' % settle_date.strftime('%Y%m%d')
    last = conn.execute(text(
        "SELECT batch_number FROM settlement_batches "
        "WHERE batch_number LIKE :p ORDER BY batch_number DESC LIMIT 1"
    ), {'p': prefix + '%'}).scalar()
    seq = int(last.split('-')[-1]) + 1 if last else 1
    return '%s-%03d' % (prefix, seq)


def migrate():
    with app.app_context():
        with db.engine.begin() as conn:
            inspector = inspect(conn)
            if not inspector.has_table('payment_vouchers'):
                print('[跳过] payment_vouchers 表不存在，可能已完成下线')
                return

            vouchers = conn.execute(text("""
                SELECT v.id, v.voucher_no, v.settle_date, v.settled_by, v.remarks,
                       (SELECT COUNT(*) FROM project_headers p
                         WHERE p.payment_voucher_id = v.id) AS linked
                FROM payment_vouchers v ORDER BY v.id
            """)).mappings().all()

            if not vouchers:
                print('[跳过] 没有凭证记录')
                return

            migrated = skipped_empty = skipped_done = 0

            for v in vouchers:
                if not v['linked']:
                    # 项目早就被取消结算了，凭证只剩一条空壳，没有迁移价值
                    print('[空凭证] %s 无关联项目，阶段二会一并删除' % v['voucher_no'])
                    skipped_empty += 1
                    continue

                projects = conn.execute(text("""
                    SELECT id, hid, settlement_batch_id,
                           operator_profit, sales_profit, company_profit
                    FROM project_headers WHERE payment_voucher_id = :vid
                """), {'vid': v['id']}).mappings().all()

                todo = [p for p in projects if not p['settlement_batch_id']]
                if not todo:
                    print('[已迁移] %s 的 %d 个项目都已有结算单' % (v['voucher_no'], len(projects)))
                    skipped_done += 1
                    continue

                op = sum(Decimal(str(p['operator_profit'] or 0)) for p in todo)
                sa = sum(Decimal(str(p['sales_profit'] or 0)) for p in todo)
                co = sum(Decimal(str(p['company_profit'] or 0)) for p in todo)

                batch_number = _batch_number_for(conn, v['settle_date'])
                remarks = '由结算凭证 %s 迁移' % v['voucher_no']
                if v['remarks']:
                    remarks = '%s / %s' % (v['remarks'], remarks)

                conn.execute(text("""
                    INSERT INTO settlement_batches
                        (batch_number, settlement_date, settled_by, project_count,
                         total_profit, total_operator_profit, total_sales_profit,
                         total_company_profit, status, payout_status, remarks, created_at)
                    VALUES
                        (:bn, :sd, :sb, :pc, :tp, :op, :sa, :co,
                         'confirmed', 'pending', :rm, NOW())
                """), {
                    'bn': batch_number, 'sd': v['settle_date'],
                    'sb': v['settled_by'] or 'migrated', 'pc': len(todo),
                    'tp': op + sa + co, 'op': op, 'sa': sa, 'co': co, 'rm': remarks,
                })
                batch_id = conn.execute(text('SELECT LAST_INSERT_ID()')).scalar()

                conn.execute(text("""
                    UPDATE project_headers SET settlement_batch_id = :bid
                    WHERE payment_voucher_id = :vid AND settlement_batch_id IS NULL
                """), {'bid': batch_id, 'vid': v['id']})

                print('[迁移] %s -> %s（%d 个项目，利润 %s）'
                      % (v['voucher_no'], batch_number, len(todo), op + sa + co))
                migrated += 1

            remaining = conn.execute(text("""
                SELECT COUNT(*) FROM project_headers
                WHERE payment_voucher_id IS NOT NULL AND settlement_batch_id IS NULL
            """)).scalar()

            print('[完成] 迁移 %d 张，空凭证 %d 张，已迁移过 %d 张'
                  % (migrated, skipped_empty, skipped_done))
            print('[校验] 仍只有凭证、没有结算单的项目：%d（应为 0）' % remaining)


def drop():
    with app.app_context():
        with db.engine.begin() as conn:
            inspector = inspect(conn)
            if not inspector.has_table('payment_vouchers'):
                print('[跳过] payment_vouchers 表已不存在')
            else:
                blocking = conn.execute(text("""
                    SELECT COUNT(*) FROM project_headers
                    WHERE payment_voucher_id IS NOT NULL AND settlement_batch_id IS NULL
                """)).scalar()
                if blocking:
                    print('[中止] 还有 %d 个项目只有凭证没有结算单，请先跑阶段一' % blocking)
                    return

            cols = {c['name'] for c in inspector.get_columns('project_headers')}
            if 'payment_voucher_id' in cols:
                # 外键不先删掉，DROP COLUMN 会因为约束存在而失败
                for fk in inspector.get_foreign_keys('project_headers'):
                    if fk['constrained_columns'] == ['payment_voucher_id']:
                        conn.execute(text('ALTER TABLE project_headers DROP FOREIGN KEY %s' % fk['name']))
                        print('[删除外键] %s' % fk['name'])
                conn.execute(text('ALTER TABLE project_headers DROP COLUMN payment_voucher_id'))
                print('[删除列] project_headers.payment_voucher_id')
            else:
                print('[跳过] project_headers.payment_voucher_id 已不存在')

            conn.execute(text('DROP TABLE IF EXISTS payment_vouchers'))
            print('[删除表] payment_vouchers')
            print('[完成] 结算凭证已下线')


if __name__ == '__main__':
    if '--drop' in sys.argv:
        drop()
    else:
        migrate()
