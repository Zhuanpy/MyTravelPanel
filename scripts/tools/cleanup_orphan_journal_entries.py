#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
清理无效的日记账分录

单据已作废或已删除，当初生成的分录却还挂在账上。这些分录不会再被任何
业务动作触及，只会一直虚增收入/成本/银行余额。

FY2026 实测存量：
    188 条 已作废发票的分录        虚增收入 32,355.00
     78 条 已删除发票的分录        虚增收入  2,990.00
      5 条 已删除 EO 的分录        虚增成本    977.23
     49 条 已删除收款的分录        虚增银行 20,278.50

产生原因是 cancel_invoice / delete_invoice 两条路径原来没有冲销分录，
代码已修（见 finance/services/journal_sync.py），这个脚本处理存量。

用冲销而不是删除：冲销留痕（原分录标 reversed + 生成借贷相反的新分录），
审计能追溯；删除就查无对证，也破坏分录编号的连续性。

用法:
    # 先看报告，不改任何数据
    venv/bin/python scripts/tools/cleanup_orphan_journal_entries.py

    # 确认无误后真执行
    venv/bin/python scripts/tools/cleanup_orphan_journal_entries.py --execute

    --from-date  只处理该日期及之后的分录。**已审计结算的期间不要动**——
                 期初余额是按当时账面数调到已审数字的，事后再冲销那段的
                 分录，期初调整就失效了，等于重复更正。
                 例：--from-date 2025-09-01 只清 FY2026
    --date       冲销分录的记账日期，默认今天。想让影响落在特定期间就指定，
                 比如 --date 2026-08-31 让它落在 FY2026 内
    --types      只处理指定类型，逗号分隔：invoice,receipt,eo,operating_expense
    --limit      只处理前 N 条，用于小批量试跑

典型用法（清理 FY2026，影响落在 FY2026 内）:
    ... cleanup_orphan_journal_entries.py --from-date 2025-09-01 --date 2026-08-31
    ... cleanup_orphan_journal_entries.py --from-date 2025-09-01 --date 2026-08-31 --execute

执行前务必先备份：
    venv/bin/python scripts/tools/db_backup.py --dir backups/db_before_cleanup --keep 3
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 单据类型 -> (模型, 表名, "无效"的判定)
# 无效 = 单据已删除（关联不上）或状态为作废
SPECS = {
    'invoice': {
        'label': '发票',
        'cancelled_status': ('cancelled',),
    },
    'receipt': {
        'label': '收款',
        'cancelled_status': ('cancelled',),
    },
    'eo': {
        'label': 'EO',
        'cancelled_status': ('void', 'cancelled'),
    },
    'operating_expense': {
        'label': '营业费用',
        'cancelled_status': ('cancelled',),
    },
}


def log(message):
    print(message, flush=True)


def load_models():
    from App_new.business.projects.models.invoice import ProjectInvoice
    from App_new.business.projects.models.receipt import ProjectReceipt
    from App_new.business.projects.models.eo import ProjectEO
    from App_new.finance.models.operating_expense import OperatingExpense
    return {
        'invoice': ProjectInvoice,
        'receipt': ProjectReceipt,
        'eo': ProjectEO,
        'operating_expense': OperatingExpense,
    }


def collect(source_type, model, from_date=None):
    """找出该类型下所有"单据已作废或已删除"的已过账分录

    from_date 限定只处理该日期及之后的分录。已审计结算的期间不能再动——
    期初余额是按当时的账面数调到已审数字的，事后再冲销那段的分录，期初
    调整就失效了，等于重复更正。
    """
    from App_new.exts import db
    from App_new.finance.models.journal_entry import JournalEntry

    query = JournalEntry.query.filter(
        JournalEntry.source_type == source_type,
        JournalEntry.status == 'posted',
        # 冲销分录本身不能再冲，否则无限套娃
        db.or_(JournalEntry.source_number.is_(None),
               ~JournalEntry.source_number.like('REV-%')),
    )
    if from_date:
        query = query.filter(JournalEntry.entry_date >= from_date)
    entries = query.all()
    if not entries:
        return []

    source_ids = {e.source_id for e in entries if e.source_id}
    existing = {}
    if source_ids:
        for row in model.query.filter(model.id.in_(source_ids)).all():
            existing[row.id] = getattr(row, 'status', None)

    bad_status = SPECS[source_type]['cancelled_status']
    result = []
    for entry in entries:
        if entry.source_id not in existing:
            result.append((entry, '单据已删除'))
        elif existing[entry.source_id] in bad_status:
            result.append((entry, f'单据已{existing[entry.source_id]}'))
    return result


def main():
    parser = argparse.ArgumentParser(description='清理无效的日记账分录')
    parser.add_argument('--execute', action='store_true',
                        help='真正执行；不加此参数只输出报告，不改数据')
    parser.add_argument('--date', help='冲销分录的记账日期，默认今天')
    parser.add_argument('--types', help='只处理指定类型，逗号分隔')
    parser.add_argument('--limit', type=int, help='只处理前 N 条')
    parser.add_argument('--from-date', dest='from_date',
                        help='只处理该日期及之后的分录。已审计结算的期间不要动——'
                             '期初余额已按已审数字调平，再冲销那段会重复更正')
    args = parser.parse_args()

    entry_date = None
    if args.date:
        try:
            entry_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            log(f'错误：日期格式应为 YYYY-MM-DD，收到 {args.date}')
            return 2
    else:
        entry_date = date.today()

    from_date = None
    if args.from_date:
        try:
            from_date = datetime.strptime(args.from_date, '%Y-%m-%d').date()
        except ValueError:
            log(f'错误：--from-date 格式应为 YYYY-MM-DD，收到 {args.from_date}')
            return 2

    types = [t.strip() for t in args.types.split(',')] if args.types else list(SPECS)
    for t in types:
        if t not in SPECS:
            log(f'错误：未知类型 {t}，可选 {", ".join(SPECS)}')
            return 2

    from App_new import create_app
    from App_new.exts import db

    app = create_app()
    with app.app_context():
        models = load_models()

        log('=' * 68)
        log('无效日记账分录清理' + ('（执行）' if args.execute else '（DRY RUN，不改数据）'))
        log(f'冲销分录记账日期：{entry_date}')
        if from_date:
            log(f'只处理 {from_date} 及之后的分录（更早的期间已结算，不动）')
        else:
            log('未指定 --from-date：将处理全部历史分录。'
                '若之前做过期初余额调整，请加 --from-date 避免重复更正')
        log('=' * 68)

        todo, summary = [], defaultdict(lambda: [0, 0.0])
        for source_type in types:
            found = collect(source_type, models[source_type], from_date)
            for entry, reason in found:
                todo.append((source_type, entry, reason))
                key = (source_type, reason)
                summary[key][0] += 1
                summary[key][1] += float(entry.total_amount or 0)

        if not todo:
            log('\n没有需要清理的分录。')
            return 0

        log('\n【汇总】')
        log(f"  {'类型':<14}{'原因':<14}{'条数':>8}{'金额':>16}")
        log('  ' + '-' * 52)
        total_count, total_amount = 0, 0.0
        for (source_type, reason), (n, amt) in sorted(summary.items()):
            log(f"  {SPECS[source_type]['label']:<14}{reason:<14}{n:>8}{amt:>16,.2f}")
            total_count += n
            total_amount += amt
        log('  ' + '-' * 52)
        log(f"  {'合计':<28}{total_count:>8}{total_amount:>16,.2f}")

        # 明细：按类型列前若干条，够核对但不刷屏
        log('\n【明细（每类最多 10 条）】')
        shown = defaultdict(int)
        for source_type, entry, reason in todo:
            if shown[source_type] >= 10:
                continue
            shown[source_type] += 1
            log(f'  {entry.entry_number}  {entry.entry_date}  '
                f'{SPECS[source_type]["label"]}#{entry.source_id} '
                f'{entry.source_number or "-":<16} {float(entry.total_amount or 0):>12,.2f}  {reason}')
        for source_type in types:
            n = sum(1 for t, _, _ in todo if t == source_type)
            if n > 10:
                log(f'  ... {SPECS[source_type]["label"]} 还有 {n - 10} 条未列出')

        if args.limit:
            todo = todo[:args.limit]
            log(f'\n--limit {args.limit}：本次只处理前 {len(todo)} 条')

        if not args.execute:
            log('\n' + '=' * 68)
            log('DRY RUN 结束，数据未改动。')
            log('确认无误后加 --execute 真正执行，执行前先备份：')
            log('  venv/bin/python scripts/tools/db_backup.py --dir backups/db_before_cleanup --keep 3')
            log('=' * 68)
            return 0

        # ---------- 真正执行 ----------
        log('\n开始冲销...')
        done, failed = 0, 0
        for source_type, entry, reason in todo:
            try:
                # 每条一个 SAVEPOINT：单条失败不拖垮整批
                with db.session.begin_nested():
                    reversal = entry.reverse(user='cleanup-script', entry_date=entry_date)
                    if reversal:
                        reversal.remarks = (f'清理无效分录：{reason}'
                                            f'（原分录 {entry.entry_number}）')
                        db.session.add(reversal)
                done += 1
            except Exception as exc:
                failed += 1
                log(f'  !! {entry.entry_number} 冲销失败: {exc}')

        db.session.commit()
        log(f'\n完成：冲销 {done} 条，失败 {failed} 条')

        # 复核：全库借贷仍应相等
        row = db.session.execute(db.text("""
            SELECT ROUND(SUM(l.debit),2), ROUND(SUM(l.credit),2)
            FROM project_journal_entry_lines l
            JOIN project_journal_entries e ON e.id = l.entry_id
            WHERE e.status IN ('posted','reversed')
        """)).first()
        log(f'复核：全库借方 {row[0]:,.2f}  贷方 {row[1]:,.2f}  '
            f'{"平衡 OK" if abs(float(row[0]) - float(row[1])) < 0.01 else "!! 不平，请检查"}')
        return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
