# -*- coding: utf-8 -*-
"""检查只有文本匹配但无实际关联ID的银行交易"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.statement import BankTransaction
from sqlalchemy import or_

app = create_app()

with app.app_context():
    print("=" * 70)
    print("检查文本级匹配但无实际关联ID的交易")
    print("=" * 70)

    # 查找 reconciliation_status='matched' 但无 matched_receipt_id 和 eo_id 的交易
    text_only = BankTransaction.query.filter(
        BankTransaction.reconciliation_status == 'matched',
        or_(BankTransaction.matched_receipt_id.is_(None), BankTransaction.matched_receipt_id == 0),
        or_(BankTransaction.eo_id.is_(None), BankTransaction.eo_id == 0)
    ).all()

    print(f"\n共 {len(text_only)} 条文本级匹配（无实际关联ID）:\n")
    for tx in text_only:
        print(f"  ID={tx.id}, 日期={tx.transaction_date}, "
              f"类型={'支出' if tx.transaction_type=='debit' else '收入'}, "
              f"金额={tx.amount}, REF={tx.accounting_ref}")

    print("\n" + "=" * 70)
