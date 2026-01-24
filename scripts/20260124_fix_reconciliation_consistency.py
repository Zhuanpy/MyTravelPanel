# -*- coding: utf-8 -*-
"""修复银行交易与收据/EO之间核对状态的一致性"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.statement import BankTransaction
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.eo import ProjectEO
from datetime import datetime

app = create_app()

with app.app_context():
    print("=" * 70)
    print("修复银行交易与收据/EO核对状态一致性")
    print("=" * 70)

    fixed_count = 0

    # 修复1: 收据 is_reconciled=True 但无银行交易匹配 -> 清除核对状态
    print("\n【修复1】清除孤立的收据核对状态...")
    reconciled_receipts = ProjectReceipt.query.filter_by(is_reconciled=True).all()
    for r in reconciled_receipts:
        tx = BankTransaction.query.filter_by(matched_receipt_id=r.id).first()
        if not tx:
            r.is_reconciled = False
            r.reconciled_at = None
            r.reconciled_by = None
            fixed_count += 1
            print(f"  清除: 收据 ID={r.id}, 号码={r.receipt_number}")

    # 修复2: EO is_reconciled=True 但无银行交易匹配 -> 清除核对状态
    print("\n【修复2】清除孤立的EO核对状态...")
    reconciled_eos = ProjectEO.query.filter_by(is_reconciled=True).all()
    for eo in reconciled_eos:
        tx = BankTransaction.query.filter_by(eo_id=eo.id).first()
        if not tx:
            eo.is_reconciled = False
            eo.reconciled_at = None
            eo.reconciled_by = None
            fixed_count += 1
            print(f"  清除: EO ID={eo.id}, 号码={eo.eo_number}")

    # 修复3: 银行交易已匹配收据但收据 is_reconciled=False -> 设置收据核对状态
    print("\n【修复3】同步收据核对状态...")
    matched_txs = BankTransaction.query.filter(
        BankTransaction.matched_receipt_id.isnot(None)
    ).all()
    fix3_count = 0
    for tx in matched_txs:
        receipt = db.session.get(ProjectReceipt, tx.matched_receipt_id)
        if receipt and not receipt.is_reconciled:
            receipt.is_reconciled = True
            receipt.reconciled_at = datetime.utcnow()
            receipt.reconciled_by = 'system_fix'
            fix3_count += 1
    fixed_count += fix3_count
    print(f"  已修复 {fix3_count} 条收据")

    # 修复4: 银行交易已匹配EO但EO is_reconciled=False -> 设置EO核对状态
    print("\n【修复4】同步EO核对状态...")
    matched_eo_txs = BankTransaction.query.filter(
        BankTransaction.eo_id.isnot(None),
        BankTransaction.eo_id != 0
    ).all()
    fix4_count = 0
    seen_eo_ids = set()
    for tx in matched_eo_txs:
        if tx.eo_id in seen_eo_ids:
            continue
        seen_eo_ids.add(tx.eo_id)
        eo = db.session.get(ProjectEO, tx.eo_id)
        if eo and not eo.is_reconciled:
            eo.is_reconciled = True
            eo.reconciled_at = datetime.utcnow()
            eo.reconciled_by = 'system_fix'
            fix4_count += 1
    fixed_count += fix4_count
    print(f"  已修复 {fix4_count} 条EO")

    # 提交修复
    db.session.commit()

    print("\n" + "=" * 70)
    print(f"修复完成，共修复 {fixed_count} 条记录")
    print("=" * 70)
