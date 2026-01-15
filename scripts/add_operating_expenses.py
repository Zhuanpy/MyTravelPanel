# -*- coding: utf-8 -*-
"""
添加运营费用脚本

将 Athina 中的运营费用 REF 转移到 OperatingExpense 表

运行方式: python scripts/add_operating_expenses.py
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.finance.models.operating_expense import OperatingExpense
from App_new.finance.models.chart_of_account import ChartOfAccount

# 要导入的运营费用数据
OPERATING_EXPENSES = [
    {
        'ref_number': 'R1232',
        'description': 'Audit Fees',
        'invoice_no': '1168',
        'amount': Decimal('1090.00'),
        'currency': 'SGD',
        'payee_name': 'JOYFUL ESCAPES PTE. LTD',
    },
    {
        'ref_number': 'R1233',
        'description': 'ATHENA account fee',
        'invoice_no': '1169',
        'amount': Decimal('1046.40'),
        'currency': 'SGD',
        'payee_name': 'JOYFUL ESCAPES PTE. LTD',
    },
    {
        'ref_number': 'R1234',
        'description': 'Annual Secretarial Services fee',
        'invoice_no': '1170',
        'amount': Decimal('398.00'),
        'currency': 'SGD',
        'payee_name': 'JOYFUL ESCAPES PTE. LTD',
    },
    {
        'ref_number': 'R1253',
        'description': 'CORPORATE SECRETARIAL SERVICES',
        'invoice_no': '1189',
        'amount': Decimal('60.00'),
        'currency': 'SGD',
        'payee_name': 'JOYFUL ESCAPES PTE. LTD',
    },
]


def get_or_create_expense_account():
    """获取或创建运营费用科目"""
    # 先查找现有的费用科目
    expense_account = ChartOfAccount.query.filter(
        ChartOfAccount.account_type == 'expense',
        ChartOfAccount.is_active == True
    ).first()

    if expense_account:
        return expense_account

    # 如果没有，创建一个默认的费用科目
    expense_account = ChartOfAccount(
        code='6000',
        name='Operating Expenses',
        name_cn='运营费用',
        account_type='expense',
        level=1,
        is_active=True,
        is_system=False,
        allow_manual_entry=True,
        balance_direction='debit',
        currency='SGD',
    )
    db.session.add(expense_account)
    db.session.flush()
    print(f"创建费用科目: {expense_account.code} - {expense_account.name}")
    return expense_account


def add_operating_expenses():
    """添加运营费用"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("添加运营费用")
        print("=" * 60)

        # 获取费用科目
        expense_account = get_or_create_expense_account()
        print(f"\n使用费用科目: {expense_account.code} - {expense_account.name}")

        # 列出所有可用的费用科目供选择
        expense_accounts = ChartOfAccount.query.filter(
            ChartOfAccount.account_type == 'expense',
            ChartOfAccount.is_active == True
        ).all()

        if len(expense_accounts) > 1:
            print("\n可用的费用科目:")
            for acc in expense_accounts:
                print(f"  ID:{acc.id} - {acc.code} - {acc.name}")

        created_count = 0
        skipped_count = 0

        print("\n开始添加运营费用...")
        print("-" * 60)

        for item in OPERATING_EXPENSES:
            # 检查是否已存在（通过描述和金额）
            existing = OperatingExpense.query.filter(
                OperatingExpense.description == item['description'],
                OperatingExpense.amount == item['amount']
            ).first()

            if existing:
                print(f"  跳过 {item['description']}: 已存在 ({existing.expense_number})")
                skipped_count += 1
                continue

            # 生成费用单编号
            expense_number = OperatingExpense.generate_expense_number()

            # 创建运营费用记录
            expense = OperatingExpense(
                expense_number=expense_number,
                expense_date=datetime.now().date(),
                expense_account_id=expense_account.id,
                amount=item['amount'],
                currency=item['currency'],
                payment_method='bank_transfer',
                payee_name=item['payee_name'],
                description=item['description'],
                remarks=f"从 Athina 导入: REF {item['ref_number']}, Invoice {item['invoice_no']}",
                status='paid',  # 已付款状态
                created_by='system_import',
            )
            db.session.add(expense)
            created_count += 1
            print(f"  创建 {expense_number}: {item['description']} - {item['currency']} {item['amount']}")

        # 提交更改
        try:
            db.session.commit()
            print("\n数据已保存")
        except Exception as e:
            db.session.rollback()
            print(f"\n保存失败: {str(e)}")
            return

        # 输出统计
        print("\n" + "=" * 60)
        print(f"统计:")
        print(f"  创建: {created_count}")
        print(f"  跳过: {skipped_count}")
        print(f"\n运营费用列表: https://www.joyesc.com/ledger/operating-expenses")


if __name__ == '__main__':
    add_operating_expenses()
