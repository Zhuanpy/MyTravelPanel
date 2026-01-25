# -*- coding: utf-8 -*-
"""
Migrate existing matched bank transactions to BankTransactionMatch table
Add match_type for all existing matches
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.statement import BankTransaction
from App_new.finance.models.bank_transaction_match import BankTransactionMatch
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.eo import ProjectEO

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Migrating existing matches to BankTransactionMatch table")
    print("=" * 60)

    # Step 1: Alter match_type enum to include new types
    print("\n[Step 1] Updating match_type enum...")
    try:
        # MySQL: Modify the enum to include new values
        sql = """
        ALTER TABLE bank_transaction_matches
        MODIFY COLUMN match_type ENUM('receipt', 'eo', 'payment', 'prepayment', 'loan_borrow', 'loan_repay')
        NOT NULL DEFAULT 'eo'
        """
        db.session.execute(db.text(sql))
        db.session.commit()
        print("[OK] match_type enum updated")
    except Exception as e:
        print(f"[WARN] Could not update enum (may already be updated): {e}")
        db.session.rollback()

    # Step 2: Migrate receipt matches
    print("\n[Step 2] Migrating receipt matches...")
    receipt_count = 0
    receipt_skip = 0

    transactions_with_receipt = BankTransaction.query.filter(
        BankTransaction.matched_receipt_id.isnot(None)
    ).all()

    for tx in transactions_with_receipt:
        # Check if already exists in BankTransactionMatch
        existing = BankTransactionMatch.query.filter_by(
            transaction_id=tx.id,
            match_type='receipt'
        ).first()

        if existing:
            receipt_skip += 1
            continue

        # Get receipt for amount
        receipt = ProjectReceipt.query.get(tx.matched_receipt_id)
        if not receipt:
            print(f"  [WARN] Receipt {tx.matched_receipt_id} not found for tx {tx.id}")
            continue

        # Create new match record
        new_match = BankTransactionMatch(
            transaction_id=tx.id,
            match_type='receipt',
            match_id=tx.matched_receipt_id,
            allocated_amount=receipt.amount,
            created_by='migration_script'
        )
        db.session.add(new_match)
        receipt_count += 1

    db.session.commit()
    print(f"[OK] Receipt matches: {receipt_count} created, {receipt_skip} skipped (already exist)")

    # Step 3: Migrate EO matches
    print("\n[Step 3] Migrating EO matches...")
    eo_count = 0
    eo_skip = 0

    transactions_with_eo = BankTransaction.query.filter(
        BankTransaction.eo_id.isnot(None)
    ).all()

    for tx in transactions_with_eo:
        # Check if already exists in BankTransactionMatch
        existing = BankTransactionMatch.query.filter_by(
            transaction_id=tx.id,
            match_type='eo'
        ).first()

        if existing:
            eo_skip += 1
            continue

        # Get EO for amount
        eo = ProjectEO.query.get(tx.eo_id)
        if not eo:
            print(f"  [WARN] EO {tx.eo_id} not found for tx {tx.id}")
            continue

        # Calculate amount
        amount = eo.pay_amount if eo.pay_amount else (eo.ref.cost_price if eo.ref and eo.ref.cost_price else 0)

        # Create new match record
        new_match = BankTransactionMatch(
            transaction_id=tx.id,
            match_type='eo',
            match_id=tx.eo_id,
            allocated_amount=amount,
            created_by='migration_script'
        )
        db.session.add(new_match)
        eo_count += 1

    db.session.commit()
    print(f"[OK] EO matches: {eo_count} created, {eo_skip} skipped (already exist)")

    # Step 4: Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)

    total_matches = BankTransactionMatch.query.count()
    receipt_matches = BankTransactionMatch.query.filter_by(match_type='receipt').count()
    eo_matches = BankTransactionMatch.query.filter_by(match_type='eo').count()
    payment_matches = BankTransactionMatch.query.filter_by(match_type='payment').count()
    prepayment_matches = BankTransactionMatch.query.filter_by(match_type='prepayment').count()

    print(f"Total matches in BankTransactionMatch: {total_matches}")
    print(f"  - Receipt: {receipt_matches}")
    print(f"  - EO: {eo_matches}")
    print(f"  - Payment: {payment_matches}")
    print(f"  - Prepayment: {prepayment_matches}")

    print("\n[DONE] Migration completed successfully")
