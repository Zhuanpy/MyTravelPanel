# -*- coding: utf-8 -*-
"""
将所有 draft 状态的日记账分录更新为 posted 状态
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from App_new import create_app
from App_new.exts import db
from App_new.finance.models.journal_entry import JournalEntry

app = create_app()

with app.app_context():
    # 查询所有 draft 状态的分录
    draft_entries = JournalEntry.query.filter_by(status='draft').all()

    print(f"找到 {len(draft_entries)} 条草稿状态的日记账分录")

    if not draft_entries:
        print("没有需要更新的分录")
        sys.exit(0)

    # 显示待更新的分录
    print("\n待更新的分录:")
    for entry in draft_entries:
        print(f"  - {entry.entry_number}: {entry.description} ({entry.currency} {entry.total_amount})")

    # 确认更新
    confirm = input("\n是否将这些分录更新为 posted 状态? (y/n): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        sys.exit(0)

    # 更新状态
    updated_count = 0
    for entry in draft_entries:
        entry.status = 'posted'
        entry.posted_at = datetime.utcnow()
        entry.posted_by = 'system'
        updated_count += 1

    db.session.commit()
    print(f"\n成功更新 {updated_count} 条分录为 posted 状态")
