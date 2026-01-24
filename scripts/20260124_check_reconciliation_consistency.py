# -*- coding: utf-8 -*-
"""检查银行交易与收据/EO之间核对状态的一致性"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.statement import BankTransaction
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.eo import ProjectEO

app = create_app()

with app.app_context():
    print("=" * 70)
    print("检查银行交易与收据/EO核对状态一致性")
    print("=" * 70)

    # 1. 收据已核对，但没有银行交易指向它
    print("\n【问题1】收据 is_reconciled=True，但无银行交易匹配:")
    reconciled_receipts = ProjectReceipt.query.filter_by(is_reconciled=True).all()
    orphan_receipts = []
    for r in reconciled_receipts:
        tx = BankTransaction.query.filter_by(matched_receipt_id=r.id).first()
        if not tx:
            orphan_receipts.append(r)
    if orphan_receipts:
        for r in orphan_receipts:
            print(f"  收据 ID={r.id}, 号码={r.receipt_number}, 金额={r.amount}")
    else:
        print("  无")

    # 2. EO已核对，但没有银行交易指向它
    print("\n【问题2】EO is_reconciled=True，但无银行交易匹配:")
    reconciled_eos = ProjectEO.query.filter_by(is_reconciled=True).all()
    orphan_eos = []
    for eo in reconciled_eos:
        tx = BankTransaction.query.filter_by(eo_id=eo.id).first()
        if not tx:
            orphan_eos.append(eo)
    if orphan_eos:
        for eo in orphan_eos:
            print(f"  EO ID={eo.id}, 号码={eo.eo_number}, 金额={eo.pay_amount}")
    else:
        print("  无")

    # 3. 银行交易有 matched_receipt_id，但收据 is_reconciled=False
    print("\n【问题3】银行交易已匹配收据，但收据 is_reconciled=False:")
    matched_txs = BankTransaction.query.filter(
        BankTransaction.matched_receipt_id.isnot(None)
    ).all()
    inconsistent_receipts = []
    for tx in matched_txs:
        receipt = ProjectReceipt.query.get(tx.matched_receipt_id)
        if receipt and not receipt.is_reconciled:
            inconsistent_receipts.append((tx, receipt))
    if inconsistent_receipts:
        for tx, r in inconsistent_receipts:
            print(f"  交易 ID={tx.id}, 日期={tx.transaction_date}, 金额={tx.amount} -> 收据 {r.receipt_number} (is_reconciled=False)")
    else:
        print("  无")

    # 4. 银行交易有 eo_id，但EO is_reconciled=False
    print("\n【问题4】银行交易已匹配EO，但EO is_reconciled=False:")
    matched_eo_txs = BankTransaction.query.filter(
        BankTransaction.eo_id.isnot(None),
        BankTransaction.eo_id != 0
    ).all()
    inconsistent_eos = []
    for tx in matched_eo_txs:
        eo = ProjectEO.query.get(tx.eo_id)
        if eo and not eo.is_reconciled:
            inconsistent_eos.append((tx, eo))
    if inconsistent_eos:
        for tx, eo in inconsistent_eos:
            print(f"  交易 ID={tx.id}, 日期={tx.transaction_date}, 金额={tx.amount} -> EO {eo.eo_number} (is_reconciled=False)")
    else:
        print("  无")

    # 5. 银行交易 matched_receipt_id 指向不存在的收据
    print("\n【问题5】银行交易 matched_receipt_id 指向不存在的收据:")
    missing_receipts = []
    for tx in matched_txs:
        receipt = ProjectReceipt.query.get(tx.matched_receipt_id)
        if not receipt:
            missing_receipts.append(tx)
    if missing_receipts:
        for tx in missing_receipts:
            print(f"  交易 ID={tx.id}, 日期={tx.transaction_date}, matched_receipt_id={tx.matched_receipt_id} (不存在)")
    else:
        print("  无")

    # 6. 银行交易 eo_id 指向不存在的EO
    print("\n【问题6】银行交易 eo_id 指向不存在的EO:")
    missing_eos = []
    for tx in matched_eo_txs:
        eo = ProjectEO.query.get(tx.eo_id)
        if not eo:
            missing_eos.append(tx)
    if missing_eos:
        for tx in missing_eos:
            print(f"  交易 ID={tx.id}, 日期={tx.transaction_date}, eo_id={tx.eo_id} (不存在)")
    else:
        print("  无")

    # 汇总
    print("\n" + "=" * 70)
    total_issues = len(orphan_receipts) + len(orphan_eos) + len(inconsistent_receipts) + len(inconsistent_eos) + len(missing_receipts) + len(missing_eos)
    print(f"共发现 {total_issues} 条不一致数据")
    print("=" * 70)
