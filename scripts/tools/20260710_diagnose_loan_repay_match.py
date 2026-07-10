"""股东还款自动匹配诊断（只读，不修改任何数据）

用途: 排查"银行支出和股东还款金额日期都对得上，却不出现在自动匹配建议里"。
逐条打印 eo_auto_match_suggestions 的每个排除条件，指出到底是哪一条把记录筛掉了。

运行方式:
    python scripts/tools/20260710_diagnose_loan_repay_match.py SR202607080001
    python scripts/tools/20260710_diagnose_loan_repay_match.py SR202607080001 --bank OCBC --account 595677931001
"""
import sys
import os
import argparse
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import or_, and_

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.shareholder_loan import ShareholderLoanRepayment
from App_new.finance.models.statement import BankStatement, BankTransaction
from App_new.finance.models.bank_transaction_match import BankTransactionMatch
from App_new.finance.routes import reconciliation_routes as rr


def yes(b):
    return '是' if b else '否'


def _fmt(ts):
    from datetime import datetime as _dt
    return _dt.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def _gunicorn_start_times():
    """返回 [(pid, 启动时间戳)]，非 Linux 或找不到进程时返回 []"""
    result = []
    if not os.path.isdir('/proc'):
        return result
    try:
        btime = 0
        with open('/proc/stat') as f:
            for line in f:
                if line.startswith('btime'):
                    btime = int(line.split()[1])
                    break
        clk = os.sysconf('SC_CLK_TCK')
        for pid in os.listdir('/proc'):
            if not pid.isdigit():
                continue
            try:
                with open(f'/proc/{pid}/cmdline', 'rb') as f:
                    cmd = f.read().decode('utf-8', 'ignore')
                if 'gunicorn' not in cmd:
                    continue
                with open(f'/proc/{pid}/stat') as f:
                    fields = f.read().rsplit(') ', 1)[1].split()
                starttime_ticks = int(fields[19])  # 第22个字段(0基索引19)
                result.append((int(pid), btime + starttime_ticks / clk))
            except (OSError, IndexError, ValueError):
                continue
    except OSError:
        pass
    return sorted(result)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repayment_number', help='还款编号，如 SR202607080001')
    ap.add_argument('--bank', default=None)
    ap.add_argument('--account', default=None)
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        print('=' * 70)
        print('0. 磁盘代码 vs gunicorn 进程（判断重启有没有真的生效）')
        print('=' * 70)
        # 注意：本脚本是独立进程，import 读的永远是磁盘上的当前代码，
        # 不能用 hasattr 判断 gunicorn 进程里跑的是什么。只能比时间。
        import inspect
        body = inspect.getsource(rr.eo_auto_match_suggestions)
        disk_ok = 'unmatched_loan_repayments' in body and 'repay_by_number' in body
        print(f'  磁盘上的 {os.path.basename(rr.__file__)} 含股东还款匹配逻辑: {yes(disk_ok)}')
        if not disk_ok:
            print('\n  >>> 结论: 服务器上的代码根本没更新（git pull 没成功？）。诊断到此为止。')
            return

        mtime = os.path.getmtime(rr.__file__)
        print(f'  文件最后修改时间: {_fmt(mtime)}')

        starts = _gunicorn_start_times()
        if not starts:
            print('  (未找到 gunicorn 进程，可能不在服务器上跑，跳过此项)')
        else:
            for pid, st in starts:
                stale = st < mtime
                print(f'  gunicorn pid={pid} 启动于 {_fmt(st)}  '
                      f'{"<<< 早于文件修改时间，跑的是旧代码!" if stale else "(晚于文件修改，OK)"}')
            if any(st < mtime for _, st in starts):
                print('\n  >>> 结论: 有进程仍在跑旧代码。用 scripts/restart_mytravelpanel.sh 彻底重启。')
                print('      （systemctl restart 遇到手动 --daemon 起的孤儿进程会静默失败）')

        print()
        print('=' * 70)
        print(f'1. 还款记录 {args.repayment_number}')
        print('=' * 70)
        rep = ShareholderLoanRepayment.query.filter_by(
            repayment_number=args.repayment_number).first()
        if not rep:
            print('  !! 找不到这条还款记录')
            return
        print(f'  id={rep.id}  金额={rep.total_amount}  日期={rep.repayment_date}')
        print(f'  status={rep.status!r}')
        print(f'  is_reconciled={rep.is_reconciled!r}')
        print(f'  description={rep.description!r}')

        matched = BankTransactionMatch.query.filter_by(
            match_type='loan_repay', match_id=rep.id).first()
        print(f'  已存在 loan_repay 匹配关系: {yes(matched is not None)}')

        print()
        print('  ---- 逐条检查自动匹配的还款侧过滤条件 ----')
        c1 = rep.status != 'cancelled'
        c2 = matched is None
        c3 = (not rep.is_reconciled)
        print(f'  [{ "通过" if c1 else "拦截" }] status != cancelled')
        print(f'  [{ "通过" if c2 else "拦截" }] 未被 BankTransactionMatch 占用')
        print(f'  [{ "通过" if c3 else "拦截" }] is_reconciled 为假  (当前值 {rep.is_reconciled!r})')
        if not c3:
            print('       >>> 注意: 右侧「支出记录」列表不看 is_reconciled，所以它仍显示「待匹配」，')
            print('           但自动匹配候选池会跳过它。界面与引擎口径不一致。')

        print()
        print('=' * 70)
        print('2. 候选银行支出（按 eo_auto_match_suggestions 的真实排除条件重建）')
        print('=' * 70)
        already_matched_tx_ids = db.session.query(BankTransactionMatch.transaction_id).subquery()
        q = BankTransaction.query.join(BankStatement).filter(
            BankTransaction.transaction_type == 'debit',
            or_(BankTransaction.eo_id.is_(None), BankTransaction.eo_id == 0),
            ~BankTransaction.id.in_(already_matched_tx_ids),
        ).filter(
            or_(BankTransaction.is_reconciled == False,
                BankTransaction.is_reconciled.is_(None))
        ).filter(
            ~and_(BankTransaction.owner_label.in_(['个人消费', '个人商用', 'personal']),
                  BankTransaction.is_confirmed == True)
        )
        if args.bank:
            q = q.filter(BankStatement.bank_name == args.bank)
        if args.account:
            q = q.filter(BankStatement.account_name == args.account)
        pool = q.all()
        print(f'  候选池大小: {len(pool)}')

        print()
        print('=' * 70)
        print('3. 描述/摘要里含该还款编号的银行支出，逐条看为什么进不了候选池')
        print('=' * 70)
        sr = args.repayment_number
        hits = BankTransaction.query.join(BankStatement).filter(
            BankTransaction.transaction_type == 'debit',
            or_(BankTransaction.description.like(f'%{sr}%'),
                BankTransaction.accounting_ref.like(f'%{sr}%'),
                BankTransaction.counterparty_name.like(f'%{sr}%'))
        ).all()
        if not hits:
            print(f'  !! 没有任何银行支出的 描述/accounting_ref/对方 含 {sr}')
        for tx in hits:
            print(f'\n  tx#{tx.id}  {tx.transaction_date}  {tx.amount}  bank={tx.statement.bank_name} acct={tx.statement.account_name}')
            print(f'    description       = {(tx.description or "")[:70]!r}')
            print(f'    accounting_ref    = {tx.accounting_ref!r}')
            print(f'    counterparty_name = {tx.counterparty_name!r}')
            print(f'    eo_id={tx.eo_id!r}  is_reconciled={tx.is_reconciled!r}  is_confirmed={tx.is_confirmed!r}')
            print(f'    owner_label={tx.owner_label!r}  reconciliation_status={tx.reconciliation_status!r}')
            m = BankTransactionMatch.query.filter_by(transaction_id=tx.id).all()
            print(f'    BankTransactionMatch: {[(x.match_type, x.match_id) for x in m] or "无"}')

            reasons = []
            if tx.transaction_type != 'debit':
                reasons.append('不是 debit')
            if tx.eo_id:
                reasons.append(f'eo_id={tx.eo_id} 非空 -> 被 eo_id is null 条件排除')
            if m:
                reasons.append('已在 BankTransactionMatch 中 -> 被排除')
            if tx.is_reconciled:
                reasons.append('is_reconciled=True -> 被排除')
            if tx.owner_label in ('个人消费', '个人商用', 'personal') and tx.is_confirmed:
                reasons.append(f'owner_label={tx.owner_label} 且已确认 -> 被排除')
            if args.bank and tx.statement.bank_name != args.bank:
                reasons.append(f'bank_name != {args.bank}')
            if args.account and tx.statement.account_name != args.account:
                reasons.append(f'account_name != {args.account}')

            in_pool = tx.id in {t.id for t in pool}
            print(f'    >>> 在候选池中: {yes(in_pool)}')
            if reasons:
                print('    >>> 排除原因: ' + '; '.join(reasons))

            if in_pool and rep:
                score = rr.calculate_loan_repay_match_score(tx, rep)
                print(f'    >>> 金额+日期评分 = {score}')
                texts = [t for t in [tx.accounting_ref, tx.description] if t]
                print(f'    >>> 编号出现在 accounting_ref/description 中: '
                      f'{yes(any(sr in t for t in texts))}  (只有这两个字段参与编号匹配)')
                if not any(sr in t for t in texts):
                    print('         >>> 注意: 编号只出现在 counterparty_name 里的话，编号精确匹配不会命中！')

        print()
        print('=' * 70)
        print('4. 还款侧候选池（自动匹配实际会遍历的集合）')
        print('=' * 70)
        matched_repay_ids = db.session.query(BankTransactionMatch.match_id).filter(
            BankTransactionMatch.match_type == 'loan_repay').subquery()
        rq = ShareholderLoanRepayment.query.filter(
            ShareholderLoanRepayment.status != 'cancelled',
            ~ShareholderLoanRepayment.id.in_(matched_repay_ids),
            or_(ShareholderLoanRepayment.is_reconciled == False,
                ShareholderLoanRepayment.is_reconciled.is_(None))
        )
        cands = rq.all()
        print(f'  还款候选数(未加日期窗口): {len(cands)}')
        print(f'  目标还款在候选池中: {yes(any(x.id == rep.id for x in cands))}')


if __name__ == '__main__':
    main()
