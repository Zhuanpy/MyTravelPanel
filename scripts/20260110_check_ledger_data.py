# -*- coding: utf-8 -*-
"""
检查并初始化 Ledger 数据
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    from App_new.finance.models.chart_of_account import ChartOfAccount
    from App_new.finance.models.journal_entry import JournalEntry, JournalEntryLine

    print("=" * 60)
    print("Ledger 数据检查")
    print("=" * 60)

    # 1. 检查会计科目
    account_count = ChartOfAccount.query.count()
    print(f"\n1. 会计科目数量: {account_count}")

    if account_count == 0:
        print("   -> 正在初始化会计科目...")
        ChartOfAccount.init_default_accounts()
        account_count = ChartOfAccount.query.count()
        print(f"   -> 初始化完成，现有 {account_count} 个科目")
    else:
        # 显示关键科目
        key_codes = ['1002', '1100', '4100', '5100']
        print("   关键科目检查:")
        for code in key_codes:
            acc = ChartOfAccount.get_by_code(code)
            if acc:
                print(f"   ✓ {code} - {acc.name} ({acc.name_cn})")
            else:
                print(f"   ✗ {code} - 缺失!")

    # 2. 检查日记账分录
    print(f"\n2. 日记账分录:")
    total_entries = JournalEntry.query.count()
    posted_entries = JournalEntry.query.filter_by(status='posted').count()
    draft_entries = JournalEntry.query.filter_by(status='draft').count()
    print(f"   总数: {total_entries}")
    print(f"   已过账: {posted_entries}")
    print(f"   草稿: {draft_entries}")

    # 按类型统计
    print("\n   按来源类型:")
    for source_type in ['invoice', 'receipt', 'eo', 'manual']:
        count = JournalEntry.query.filter_by(source_type=source_type).count()
        print(f"   - {source_type}: {count}")

    # 3. 检查业务数据
    print(f"\n3. 业务数据统计:")

    from App_new.business.projects.models.invoice import ProjectInvoice
    from App_new.business.projects.models.receipt import ProjectReceipt
    from App_new.business.projects.models.eo import ProjectEO

    invoice_count = ProjectInvoice.query.count()
    invoice_sent = ProjectInvoice.query.filter_by(status='sent').count()
    print(f"   Invoice 总数: {invoice_count}, 已发送: {invoice_sent}")

    receipt_count = ProjectReceipt.query.count()
    receipt_confirmed = ProjectReceipt.query.filter_by(status='confirmed').count()
    print(f"   Receipt 总数: {receipt_count}, 已确认: {receipt_confirmed}")

    eo_count = ProjectEO.query.count()
    eo_paid = ProjectEO.query.filter_by(status='paid').count()
    print(f"   EO 总数: {eo_count}, 已付款: {eo_paid}")

    print("\n" + "=" * 60)
    print("建议操作:")
    print("=" * 60)

    if account_count == 0:
        print("1. 会计科目已自动初始化")

    if total_entries == 0:
        print("2. 没有日记账分录，需要从现有业务数据生成")
        print("   运行: python scripts/20260110_generate_journal_entries.py --execute")
    elif posted_entries == 0 and draft_entries > 0:
        print("2. 有草稿分录但没有过账，需要过账才能在报表显示")
    else:
        print("2. 日记账数据正常")

    print()
