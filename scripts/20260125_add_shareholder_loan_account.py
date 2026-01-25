# -*- coding: utf-8 -*-
"""添加股东借款科目"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.chart_of_account import ChartOfAccount

app = create_app()

with app.app_context():
    print("=" * 60)
    print("添加股东借款科目")
    print("=" * 60)

    # 检查是否已存在
    existing = ChartOfAccount.query.filter_by(code='2400').first()
    if existing:
        print(f"科目 2400 已存在: {existing.name}")
        print("跳过创建")
    else:
        # 获取父级科目 (2000 Liabilities)
        parent = ChartOfAccount.query.filter_by(code='2000').first()
        parent_id = parent.id if parent else None

        # 创建股东借款科目
        shareholder_loan = ChartOfAccount(
            code='2400',
            name='Shareholder Loan',
            name_cn='股东借款',
            account_type='liability',
            parent_id=parent_id,
            level=2,
            is_active=True,
            is_system=False,
            allow_manual_entry=True,
            balance_direction='credit',  # 负债类科目贷方余额
            currency='SGD',
            description='股东/老板借给公司的款项，用于公司运营周转',
            sort_order=2400
        )
        db.session.add(shareholder_loan)
        db.session.commit()
        print(f"[OK] 成功添加科目: 2400 Shareholder Loan (股东借款)")

    print("\n" + "=" * 60)
    print("当前负债类科目：")
    print("=" * 60)
    liabilities = ChartOfAccount.query.filter(
        ChartOfAccount.code.like('2%')
    ).order_by(ChartOfAccount.code).all()
    for a in liabilities:
        cn_name = f" ({a.name_cn})" if a.name_cn else ""
        print(f"  {a.code} - {a.name}{cn_name}")

    print("\n" + "=" * 60)
    print("使用说明：")
    print("=" * 60)
    print("""
当股东将个人资金转入公司账户时，记账分录：

  借方 (Debit):  1002 Bank - SGD     +金额
  贷方 (Credit): 2400 Shareholder Loan  +金额

当公司还款给股东时，记账分录：

  借方 (Debit):  2400 Shareholder Loan  +金额
  贷方 (Credit): 1002 Bank - SGD     +金额
""")
