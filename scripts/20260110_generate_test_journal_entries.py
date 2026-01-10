# -*- coding: utf-8 -*-
"""
生成测试日记账分录数据
用于测试 Trial Balance 报表的 Opening Balance 列
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
from decimal import Decimal
from App_new import create_app
from App_new.exts import db
from App_new.finance.models.journal_entry import JournalEntry, JournalEntryLine
from App_new.finance.models.chart_of_account import ChartOfAccount

def generate_test_entries():
    """生成测试日记账分录"""

    # 获取科目
    bank_account = ChartOfAccount.query.filter_by(code='1002').first()  # Bank - SGD
    ar_account = ChartOfAccount.query.filter_by(code='1100').first()    # Accounts Receivable
    sales_account = ChartOfAccount.query.filter_by(code='4100').first() # Sales Revenue
    cost_account = ChartOfAccount.query.filter_by(code='5100').first()  # Direct Costs

    if not all([bank_account, ar_account, sales_account, cost_account]):
        print("错误: 缺少必要的科目，请先创建科目表")
        print(f"  Bank (1002): {bank_account}")
        print(f"  AR (1100): {ar_account}")
        print(f"  Sales (4100): {sales_account}")
        print(f"  Cost (5100): {cost_account}")
        return

    # 获取或创建权益科目
    equity_account = ChartOfAccount.query.filter_by(code='3100').first()
    if not equity_account:
        # 如果没有权益科目，创建一个
        equity_account = ChartOfAccount(
            code='3100',
            name='Owners Equity',
            name_cn='所有者权益',
            account_type='equity',
            balance_direction='credit',
            is_active=True,
            level=1
        )
        db.session.add(equity_account)
        db.session.flush()
        print(f"创建科目: 3100 - Owners Equity")

    # 定义测试数据 - 2025年上半年的交易
    test_data = [
        # 2025年1月 - 初始资本投入
        {
            'entry_date': date(2025, 1, 15),
            'description': 'Initial Capital Investment 初始资本投入',
            'lines': [
                {'account_id': bank_account.id, 'debit': Decimal('50000.00'), 'credit': Decimal('0'), 'memo': 'Capital injection'},
                {'account_id': equity_account.id, 'debit': Decimal('0'), 'credit': Decimal('50000.00'), 'memo': 'Owners equity'},
            ]
        },
        # 2025年3月 - 销售收入
        {
            'entry_date': date(2025, 3, 10),
            'description': 'Sales Invoice INV-2025-001',
            'lines': [
                {'account_id': ar_account.id, 'debit': Decimal('15000.00'), 'credit': Decimal('0'), 'memo': 'AR for Invoice'},
                {'account_id': sales_account.id, 'debit': Decimal('0'), 'credit': Decimal('15000.00'), 'memo': 'Sales Revenue'},
            ]
        },
        # 2025年3月 - 收款
        {
            'entry_date': date(2025, 3, 25),
            'description': 'Receipt RCP-2025-001',
            'lines': [
                {'account_id': bank_account.id, 'debit': Decimal('15000.00'), 'credit': Decimal('0'), 'memo': 'Bank deposit'},
                {'account_id': ar_account.id, 'debit': Decimal('0'), 'credit': Decimal('15000.00'), 'memo': 'AR reduction'},
            ]
        },
        # 2025年5月 - 销售收入
        {
            'entry_date': date(2025, 5, 8),
            'description': 'Sales Invoice INV-2025-002',
            'lines': [
                {'account_id': ar_account.id, 'debit': Decimal('28000.00'), 'credit': Decimal('0'), 'memo': 'AR for Invoice'},
                {'account_id': sales_account.id, 'debit': Decimal('0'), 'credit': Decimal('28000.00'), 'memo': 'Sales Revenue'},
            ]
        },
        # 2025年5月 - 付款成本
        {
            'entry_date': date(2025, 5, 15),
            'description': 'Cost Payment EO-2025-001',
            'lines': [
                {'account_id': cost_account.id, 'debit': Decimal('8500.00'), 'credit': Decimal('0'), 'memo': 'Direct cost'},
                {'account_id': bank_account.id, 'debit': Decimal('0'), 'credit': Decimal('8500.00'), 'memo': 'Bank payment'},
            ]
        },
        # 2025年6月 - 收款
        {
            'entry_date': date(2025, 6, 5),
            'description': 'Receipt RCP-2025-002',
            'lines': [
                {'account_id': bank_account.id, 'debit': Decimal('20000.00'), 'credit': Decimal('0'), 'memo': 'Bank deposit'},
                {'account_id': ar_account.id, 'debit': Decimal('0'), 'credit': Decimal('20000.00'), 'memo': 'AR reduction'},
            ]
        },
        # 2025年7月 - 销售收入
        {
            'entry_date': date(2025, 7, 12),
            'description': 'Sales Invoice INV-2025-003',
            'lines': [
                {'account_id': ar_account.id, 'debit': Decimal('35000.00'), 'credit': Decimal('0'), 'memo': 'AR for Invoice'},
                {'account_id': sales_account.id, 'debit': Decimal('0'), 'credit': Decimal('35000.00'), 'memo': 'Sales Revenue'},
            ]
        },
        # 2025年8月 - 付款成本
        {
            'entry_date': date(2025, 8, 20),
            'description': 'Cost Payment EO-2025-002',
            'lines': [
                {'account_id': cost_account.id, 'debit': Decimal('12000.00'), 'credit': Decimal('0'), 'memo': 'Direct cost'},
                {'account_id': bank_account.id, 'debit': Decimal('0'), 'credit': Decimal('12000.00'), 'memo': 'Bank payment'},
            ]
        },
        # 2025年9月 - 收款
        {
            'entry_date': date(2025, 9, 10),
            'description': 'Receipt RCP-2025-003',
            'lines': [
                {'account_id': bank_account.id, 'debit': Decimal('40000.00'), 'credit': Decimal('0'), 'memo': 'Bank deposit'},
                {'account_id': ar_account.id, 'debit': Decimal('0'), 'credit': Decimal('40000.00'), 'memo': 'AR reduction'},
            ]
        },
    ]

    created_count = 0

    for i, data in enumerate(test_data):
        # 生成分录编号
        entry_date = data['entry_date']
        prefix = f"JE{entry_date.strftime('%Y%m%d')}"
        entry_number = f"{prefix}{(i+1):04d}"

        # 检查是否已存在
        existing = JournalEntry.query.filter_by(entry_number=entry_number).first()
        if existing:
            print(f"跳过: {entry_number} 已存在")
            continue

        # 创建分录
        entry = JournalEntry(
            entry_number=entry_number,
            entry_date=entry_date,
            source_type='manual',
            description=data['description'],
            currency='SGD',
            status='posted',
            posted_at=datetime.utcnow(),
            posted_by='system',
            created_by='system'
        )

        # 添加分录行
        for line_no, line_data in enumerate(data['lines'], 1):
            line = JournalEntryLine(
                line_no=line_no,
                account_id=line_data['account_id'],
                debit=line_data['debit'],
                credit=line_data['credit'],
                memo=line_data['memo']
            )
            entry.lines.append(line)

        # 计算总金额
        entry.total_amount = sum(line.debit for line in entry.lines)

        db.session.add(entry)
        created_count += 1
        print(f"创建: {entry_number} - {data['description']} - {entry.total_amount}")

    db.session.commit()
    print(f"\n完成! 共创建 {created_count} 条测试分录")

    # 显示汇总
    print("\n=== 期初余额汇总 (2025-10-01 之前) ===")
    print(f"Bank (1002): 借方累计")
    print(f"AR (1100): 借方累计")
    print(f"Sales (4100): 贷方累计")
    print(f"Cost (5100): 借方累计")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("生成测试日记账分录")
        print("=" * 50)
        generate_test_entries()
