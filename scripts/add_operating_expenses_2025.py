# -*- coding: utf-8 -*-
"""
添加2025年运营费用脚本

运行方式: python scripts/add_operating_expenses_2025.py
"""

import sys
import os
from datetime import date
from decimal import Decimal

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.finance.models.operating_expense import OperatingExpense
from App_new.finance.models.chart_of_account import ChartOfAccount

# 2025年运营费用数据 - 日期: 2025-01-15
EXPENSE_DATE = date(2025, 1, 15)

OPERATING_EXPENSES = [
    {
        'ref_number': 'R236',
        'description': "Directors' fees for 2024",
        'eo_number': '220',
        'amount': Decimal('7500.00'),
        'currency': 'SGD',
        'payee_name': 'JOYFUL ESCAPES PTE. LTD',
    },
    {
        'ref_number': 'R237',
        'description': "Directors' fees for 2024",
        'eo_number': '221',
        'amount': Decimal('7500.00'),
        'currency': 'SGD',
        'payee_name': 'JOYFUL ESCAPES PTE. LTD',
    },
    {
        'ref_number': 'R238',
        'description': 'CORPORATE SECRETARIAL SERVICES',
        'eo_number': '222',
        'amount': Decimal('448.00'),
        'currency': 'SGD',
        'payee_name': 'Richmond Corporate Advisory Pte Ltd',
    },
    {
        'ref_number': 'R240',
        'description': 'CORPORATE SECRETARIAL SERVICES',
        'eo_number': '223',
        'amount': Decimal('60.00'),
        'currency': 'SGD',
        'payee_name': 'JOYFUL ESCAPES PTE. LTD',
    },
    {
        'ref_number': 'R241',
        'description': 'Audit fee for financial year ended 31 August 2024',
        'eo_number': '224',
        'amount': Decimal('4200.00'),
        'currency': 'SGD',
        'payee_name': 'JOYFUL ESCAPES PTE. LTD',
    },
    {
        'ref_number': 'R246',
        'description': 'athena client license for 2 users',
        'eo_number': '233',
        'amount': Decimal('1883.52'),
        'currency': 'SGD',
        'payee_name': 'ZHANG ZHUAN OCBC',
    },
]


def get_expense_account():
    """获取费用科目"""
    expense_account = ChartOfAccount.query.filter(
        ChartOfAccount.account_type == 'expense',
        ChartOfAccount.is_active == True
    ).first()

    if not expense_account:
        print("错误: 找不到费用科目，请先创建")
        return None

    return expense_account


def add_operating_expenses():
    """添加运营费用"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("添加2025年运营费用")
        print(f"费用日期: {EXPENSE_DATE}")
        print("=" * 60)

        # 获取费用科目
        expense_account = get_expense_account()
        if not expense_account:
            return

        print(f"\n使用费用科目: {expense_account.code} - {expense_account.name}")

        created_count = 0
        skipped_count = 0
        total_amount = Decimal('0')

        print("\n开始添加运营费用...")
        print("-" * 60)

        for item in OPERATING_EXPENSES:
            # 检查是否已存在（通过描述、金额和收款方）
            existing = OperatingExpense.query.filter(
                OperatingExpense.description == item['description'],
                OperatingExpense.amount == item['amount'],
                OperatingExpense.payee_name == item['payee_name']
            ).first()

            if existing:
                print(f"  跳过 {item['ref_number']}: {item['description']} - 已存在 ({existing.expense_number})")
                skipped_count += 1
                continue

            # 生成费用单编号
            expense_number = OperatingExpense.generate_expense_number()

            # 创建运营费用记录
            expense = OperatingExpense(
                expense_number=expense_number,
                expense_date=EXPENSE_DATE,
                expense_account_id=expense_account.id,
                amount=item['amount'],
                currency=item['currency'],
                payment_method='bank_transfer',
                payee_name=item['payee_name'],
                description=item['description'],
                remarks=f"从 Athina 导入: REF {item['ref_number']}, EO {item['eo_number']}",
                status='paid',
                created_by='system_import',
            )
            db.session.add(expense)
            created_count += 1
            total_amount += item['amount']
            print(f"  创建 {expense_number}: {item['description']} - {item['currency']} {item['amount']} ({item['payee_name']})")

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
        print(f"  创建: {created_count} 条")
        print(f"  跳过: {skipped_count} 条")
        print(f"  总金额: SGD {total_amount:,.2f}")
        print(f"\n运营费用列表: https://www.joyesc.com/ledger/operating-expenses")


if __name__ == '__main__':
    add_operating_expenses()
