# -*- coding: utf-8 -*-
"""清掉没有任何依据的 supplier_payments.is_reconciled

is_reconciled 的字段注释是「是否已核对」，指的是跟银行流水对过账。但付款列表页
的「确认」按钮（和「一键确认」全选）一直是无条件置位的，于是线上几乎每条付款
都显示「已核对」，这个状态就没有意义了 —— 做银行调节的时候完全不能用它筛。

代码侧已经修好（App_new/business/projects/routes/project_payment.py）：
    - 单条确认：没有 bank_transaction_matches 记录时回 need_force，
      操作人在弹窗里坚持才置位，并在 reconciled_by 留「(手工)」
    - 批量确认：不给强行确认的口子，没匹配银行流水的一律跳过

这个脚本清历史数据，只清「什么依据都没有」的那些：

    没有 bank_transaction_matches 匹配记录   AND   reconciled_at IS NULL

reconciled_at 有值说明是人点出来的，哪怕没有银行流水也默认保留 —— 那是人的判断，
不是脚本该推翻的。但线上那批「已核对」多半是「一键确认」全选点出来的，也带
reconciled_at；确认过确实是这种情况的话，加 --include-manual 一起清掉。

清掉的行不影响任何金额和分录，只是把「已核对」标记归位。

运行方式:
    python scripts/tools/20260906_reset_unmatched_reconciled.py                     # 只看不改
    python scripts/tools/20260906_reset_unmatched_reconciled.py --apply             # 清「无任何依据」的
    python scripts/tools/20260906_reset_unmatched_reconciled.py --include-manual --apply
                                                                                    # 连一键确认点出来的一起清

放在 scripts/tools/ 而不是 scripts/：部署脚本会自动跑 scripts/ 下所有日期开头的
文件，这个要人看过报告再决定。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from App_new import create_app
from App_new.exts import db

app = create_app()

# 标了「已核对」但银行流水里没有对应匹配的付款
# {evidence} 处按参数换成「只要没核对时间的」还是「有没有核对时间都要」
TARGET_SQL = """
SELECT sp.id, sp.payment_no, sp.payment_date, sp.total_amount,
       sp.reconciled_at, sp.reconciled_by, sp.payment_voucher_no
FROM supplier_payments sp
LEFT JOIN bank_transaction_matches m
       ON m.match_type = 'payment' AND m.match_id = sp.id
WHERE sp.is_reconciled = 1
  {evidence}
  AND m.id IS NULL
ORDER BY sp.payment_date, sp.id
"""

SUMMARY_SQL = """
SELECT
    SUM(sp.is_reconciled = 1)                                   AS reconciled,
    SUM(sp.is_reconciled = 1 AND m.id IS NOT NULL)              AS with_bank_match,
    SUM(sp.is_reconciled = 1 AND m.id IS NULL
        AND sp.reconciled_at IS NOT NULL)                       AS manual_only,
    SUM(sp.is_reconciled = 1 AND m.id IS NULL
        AND sp.reconciled_at IS NULL)                           AS no_evidence,
    COUNT(*)                                                    AS total
FROM supplier_payments sp
LEFT JOIN bank_transaction_matches m
       ON m.match_type = 'payment' AND m.match_id = sp.id
"""


def main(apply_changes, include_manual):
    with app.app_context():
        summary = db.session.execute(text(SUMMARY_SQL)).fetchone()
        print('付款记录合计 %s 条，其中标记已核对 %s 条：' % (summary.total, summary.reconciled or 0))
        print('    有银行流水匹配        %s 条  <- 真的对过账，保留' % (summary.with_bank_match or 0))
        print('    无匹配但有核对时间    %s 条  <- 人手工点的，保留' % (summary.manual_only or 0))
        print('    无匹配也无核对时间    %s 条  <- 没有任何依据，本脚本处理' % (summary.no_evidence or 0))
        print()

        sql = TARGET_SQL.format(evidence='' if include_manual else 'AND sp.reconciled_at IS NULL')
        rows = db.session.execute(text(sql)).fetchall()
        print('本次处理范围：%s' % ('无银行流水的全部（含手工确认）' if include_manual
                                   else '仅「无匹配也无核对时间」的'))
        if not rows:
            print('[完成] 没有需要清理的记录')
            return

        print('明细（最多列 30 条）：')
        print('  %-6s %-18s %-12s %12s  %-20s %s' % (
            'id', '付款编号', '付款日期', '金额', '核对人', '凭证号'))
        for row in rows[:30]:
            print('  %-6s %-18s %-12s %12s  %-20s %s' % (
                row.id, row.payment_no, row.payment_date, row.total_amount,
                row.reconciled_by or '-', row.payment_voucher_no or '-'))
        if len(rows) > 30:
            print('  ... 共 %s 条' % len(rows))
        print()

        if not apply_changes:
            print('[试运行] 以上 %s 条会被置为「未核对」。加 --apply 才真的执行。' % len(rows))
            return

        ids = [row.id for row in rows]
        updated = db.session.execute(
            text('UPDATE supplier_payments SET is_reconciled = 0, '
                 'reconciled_at = NULL, reconciled_by = NULL WHERE id IN :ids'),
            {'ids': tuple(ids)}
        ).rowcount
        db.session.commit()
        print('[完成] %s 条已置为未核对' % updated)


if __name__ == '__main__':
    main('--apply' in sys.argv, '--include-manual' in sys.argv)
