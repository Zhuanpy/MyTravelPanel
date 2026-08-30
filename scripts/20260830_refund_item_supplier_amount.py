"""退款明细增加「本次预计供应商退回」金额

退款表格原来每张发票只有一个「本次退款」金额（面向客户那一侧）。
供应商实际退回多少往往和退给客户的不一样，中间差额就是手续费。
现在每张发票拆成两列：
- amount                    本次预计退回客户（原有列，决定发票的已退款/可退余额）
- supplier_expected_amount  本次预计供应商退回（新增）

跟踪区的「预计退回 / 预计退客户」改为由本表汇总得出，不再手填。

运行方式: python scripts/20260830_refund_item_supplier_amount.py

幂等：已存在的列会跳过，可重复执行。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db

app = create_app()


def main():
    with app.app_context():
        with db.engine.begin() as conn:
            if not inspect(conn).has_table('project_refund_items'):
                print('[SKIP] 表 project_refund_items 不存在')
                return

            existing = {c['name'] for c in inspect(conn).get_columns('project_refund_items')}
            if 'supplier_expected_amount' in existing:
                print('[SKIP] supplier_expected_amount 已存在')
                print('\n迁移完成。')
                return

            conn.execute(text(
                "ALTER TABLE project_refund_items "
                "ADD COLUMN supplier_expected_amount DECIMAL(10,2) NULL DEFAULT 0 "
                "COMMENT '本次预计供应商退回金额' AFTER amount"
            ))
            print('[OK] 已添加 project_refund_items.supplier_expected_amount')

            # 旧数据回填：此前只记了客户侧金额，供应商侧按退款单上已填的
            # supplier_expected_amount 按比例摊到各明细；单条明细的直接全额给它。
            updated = conn.execute(text("""
                UPDATE project_refund_items i
                JOIN project_refunds r ON r.id = i.refund_id
                JOIN (SELECT refund_id, SUM(amount) AS total_amount
                      FROM project_refund_items GROUP BY refund_id) t
                     ON t.refund_id = i.refund_id
                SET i.supplier_expected_amount = CASE
                        WHEN t.total_amount > 0
                            THEN ROUND(COALESCE(r.supplier_expected_amount, 0) * i.amount / t.total_amount, 2)
                        ELSE 0
                    END
                WHERE COALESCE(r.supplier_expected_amount, 0) > 0
            """)).rowcount
            print('[OK] 已回填 %d 条旧明细的供应商侧金额' % updated)

            print('\n迁移完成。')


if __name__ == '__main__':
    main()
