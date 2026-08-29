"""退款打通对账/分成所需的结构调整

改动内容：
1. project_headers 增加 related_header_id —— 退款/调整单指回被调整的原始订单。
   结算时用主单的利润决定分成档位（这套规则按总利润分档，不是按增量分档：
   10 块单独成单落到小单档 40/30/30，并进 2000 的大单则是 20/40/40，
   同一笔钱分成差一倍）。
2. supplier_prepayments.payment_method 枚举增加 'refund' —— 供应商把钱退回到
   预付余额（钱没实际动，只是额度挂回来）。这类记录不参与银行对账，
   统计"本期充值现金"时也应排除。
3. supplier_prepayments 增加 source_refund_id —— 指回是哪张退款单退回来的。
4. business_types 增加 'refund/退款调整' —— 退款调整用的 REF 类型，
   便于报表统计营业额时排除（sell/cost 记的是退回额与退客户额，不是真实销售）。

运行方式: python scripts/20260829_refund_settlement_support.py

幂等：重复执行安全，已存在的列/枚举值/字典行会跳过。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db

app = create_app()


def _columns(conn, table):
    return {c['name'] for c in inspect(conn).get_columns(table)}


def main():
    with app.app_context():
        with db.engine.begin() as conn:
            inspector = inspect(conn)

            # ---------- 1. project_headers.related_header_id ----------
            if not inspector.has_table('project_headers'):
                print('[SKIP] 表 project_headers 不存在')
            elif 'related_header_id' in _columns(conn, 'project_headers'):
                print('[SKIP] project_headers.related_header_id 已存在')
            else:
                print('添加 project_headers.related_header_id ...')
                conn.execute(text(
                    "ALTER TABLE project_headers "
                    "ADD COLUMN related_header_id INT NULL "
                    "COMMENT '关联主单ID(退款/调整单指回原订单)'"
                ))
                conn.execute(text(
                    "ALTER TABLE project_headers "
                    "ADD CONSTRAINT fk_project_headers_related "
                    "FOREIGN KEY (related_header_id) REFERENCES project_headers(id)"
                ))
                print('[OK] project_headers.related_header_id')

            # ---------- 2. supplier_prepayments.payment_method 枚举 ----------
            if not inspector.has_table('supplier_prepayments'):
                print('[SKIP] 表 supplier_prepayments 不存在')
            else:
                current = conn.execute(text(
                    "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'supplier_prepayments' "
                    "AND COLUMN_NAME = 'payment_method'"
                )).scalar()
                if current and "'refund'" in current:
                    print('[SKIP] payment_method 已包含 refund')
                else:
                    print('扩展 supplier_prepayments.payment_method 枚举 ...')
                    conn.execute(text(
                        "ALTER TABLE supplier_prepayments MODIFY COLUMN payment_method "
                        "ENUM('bank_transfer','credit_card','cash','paynow','refund','other') "
                        "NOT NULL DEFAULT 'bank_transfer' COMMENT '支付方式'"
                    ))
                    print('[OK] payment_method 枚举已扩展')

                # ---------- 3. supplier_prepayments.source_refund_id ----------
                if 'source_refund_id' in _columns(conn, 'supplier_prepayments'):
                    print('[SKIP] supplier_prepayments.source_refund_id 已存在')
                else:
                    print('添加 supplier_prepayments.source_refund_id ...')
                    conn.execute(text(
                        "ALTER TABLE supplier_prepayments "
                        "ADD COLUMN source_refund_id INT NULL "
                        "COMMENT '来源退款单ID(payment_method=refund 时)'"
                    ))
                    if inspect(conn).has_table('project_refunds'):
                        conn.execute(text(
                            "ALTER TABLE supplier_prepayments "
                            "ADD CONSTRAINT fk_prepayment_source_refund "
                            "FOREIGN KEY (source_refund_id) REFERENCES project_refunds(id)"
                        ))
                    print('[OK] supplier_prepayments.source_refund_id')

            # ---------- 4. business_types 增加退款调整类型 ----------
            if not inspector.has_table('business_types'):
                print('[SKIP] 表 business_types 不存在')
            else:
                exists = conn.execute(text(
                    "SELECT id FROM business_types WHERE code = 'refund'"
                )).scalar()
                if exists:
                    print('[SKIP] business_types 已有 refund (id=%s)' % exists)
                else:
                    cols = _columns(conn, 'business_types')
                    fields = ['code', 'name']
                    values = {'code': 'refund', 'name': '退款调整'}
                    # 兼容表上可能存在的可选列
                    if 'description' in cols:
                        fields.append('description')
                        values['description'] = '退款调整专用：sell=供应商退回额，cost=退客户额，差额为手续费收入'
                    if 'is_active' in cols:
                        fields.append('is_active')
                        values['is_active'] = 1
                    col_sql = ', '.join(fields)
                    val_sql = ', '.join(':' + f for f in fields)
                    conn.execute(text(
                        f"INSERT INTO business_types ({col_sql}) VALUES ({val_sql})"
                    ), values)
                    print('[OK] business_types 新增 refund/退款调整')

        print('\n迁移完成。')


if __name__ == '__main__':
    main()
