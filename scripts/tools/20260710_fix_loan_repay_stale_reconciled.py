"""清除股东还款上"已核对但无匹配关系"的僵尸标记

背景:
  bank-eo 页面的「标记已核对」会给股东还款置 is_reconciled=True。
  但该页右侧列表当时不看这个字段，仍把记录显示成「待匹配」，
  而自动匹配候选池又排除 is_reconciled 为真的记录 ——
  结果是记录看起来待匹配、实际永远匹配不上，且界面上没有取消入口。

  本脚本只清理"被标记核对、却没有任何 BankTransactionMatch 匹配关系"的还款。
  真正已匹配的记录（标记是对的）不会被碰。

运行方式:
    # 只看不改（默认）
    python scripts/tools/20260710_fix_loan_repay_stale_reconciled.py

    # 确认无误后实际写库
    python scripts/tools/20260710_fix_loan_repay_stale_reconciled.py --apply

    # 只处理指定编号
    python scripts/tools/20260710_fix_loan_repay_stale_reconciled.py SR202607080001 --apply
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.shareholder_loan import ShareholderLoanRepayment
from App_new.finance.models.bank_transaction_match import BankTransactionMatch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repayment_number', nargs='?', default=None,
                    help='只处理这个编号；不填则扫描全部')
    ap.add_argument('--apply', action='store_true', help='实际写库；不加则只打印')
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        q = ShareholderLoanRepayment.query.filter(
            ShareholderLoanRepayment.is_reconciled == True
        )
        if args.repayment_number:
            q = q.filter(ShareholderLoanRepayment.repayment_number == args.repayment_number)
        reps = q.order_by(ShareholderLoanRepayment.repayment_date).all()

        print(f'is_reconciled=True 的还款: {len(reps)} 条\n')

        stale, legit = [], []
        for r in reps:
            matched = BankTransactionMatch.query.filter_by(
                match_type='loan_repay', match_id=r.id).first()
            (legit if matched else stale).append((r, matched))

        print('--- 有匹配关系，标记正确，不动 ---')
        for r, m in legit:
            print(f'  {r.repayment_number}  {r.repayment_date}  {r.total_amount}  '
                  f'-> 匹配 tx#{m.transaction_id}')
        if not legit:
            print('  (无)')

        print('\n--- 无匹配关系，僵尸标记，需清除 ---')
        for r, _ in stale:
            print(f'  {r.repayment_number}  {r.repayment_date}  {r.total_amount}  '
                  f'reconciled_at={r.reconciled_at} reconciled_by={r.reconciled_by!r}')
        if not stale:
            print('  (无)')
            return

        if not args.apply:
            print(f'\n[DRY RUN] 未写库。确认无误后加 --apply 执行，将清除 {len(stale)} 条标记。')
            return

        for r, _ in stale:
            r.is_reconciled = False
            r.reconciled_at = None
            r.reconciled_by = None
        db.session.commit()
        print(f'\n已清除 {len(stale)} 条僵尸标记。这些还款将重新进入自动匹配候选池。')


if __name__ == '__main__':
    main()
