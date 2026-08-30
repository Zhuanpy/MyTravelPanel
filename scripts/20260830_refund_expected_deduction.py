"""退款单增加「预计金额 / 扣款」四个字段

退款几乎不会原额退回：航司/供应商先扣一笔手续费，我们再扣一笔，
剩下的才退给客户。中间的差额就是这笔退款留在公司的收入，
原先没有字段承载，只能写在备注里，也解释不了「退款单总额」和「实收」为什么对不上。

新增字段（均为 DECIMAL(10,2)，默认 0）：
- supplier_expected_amount   预计供应商退回金额
- supplier_deduction_amount  供应商扣款(航司手续费等)
- customer_expected_amount   预计退给客户金额
- customer_deduction_amount  我方扣款(手续费收入)

运行方式: python scripts/20260830_refund_expected_deduction.py

幂等：已存在的列会跳过，可重复执行。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db

app = create_app()

NEW_COLUMNS = [
    ('supplier_expected_amount', '预计供应商退回金额', 'supplier_refund_status'),
    ('supplier_deduction_amount', '供应商扣款(航司手续费等)', 'supplier_expected_amount'),
    ('customer_expected_amount', '预计退给客户金额', 'customer_refund_status'),
    ('customer_deduction_amount', '我方扣款(手续费收入)', 'customer_expected_amount'),
]


def main():
    with app.app_context():
        with db.engine.begin() as conn:
            if not inspect(conn).has_table('project_refunds'):
                print('[SKIP] 表 project_refunds 不存在')
                return

            existing = {c['name'] for c in inspect(conn).get_columns('project_refunds')}
            added = 0
            for name, comment, after in NEW_COLUMNS:
                if name in existing:
                    print('[SKIP] %s 已存在' % name)
                    continue
                # AFTER 只影响列顺序，目标列不存在时退化为追加到表尾
                after_sql = ' AFTER `%s`' % after if after in existing else ''
                conn.execute(text(
                    "ALTER TABLE project_refunds ADD COLUMN `%s` DECIMAL(10,2) NULL DEFAULT 0 "
                    "COMMENT '%s'%s" % (name, comment, after_sql)
                ))
                existing.add(name)
                added += 1
                print('[OK] 已添加 %s' % name)

            print('\n新增 %d 列，迁移完成。' % added)


if __name__ == '__main__':
    main()
