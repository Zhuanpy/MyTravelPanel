# -*- coding: utf-8 -*-
"""
迁移脚本：为 OCBC 建立「银行费用」关键字，并回填历史上未确认的同类流水

背景：手续费、TRANS CHARGE、CASH REBATE 这类流水是银行自身产生的，没有对手方，
永远匹配不到 REF/EO/收款单。它们会一直挂着 is_confirmed=0，把对账单摁在「进行中」，
每期都要人工排查一遍。

本脚本做两件事：
1. 种入 bank_charge 类型关键字（幂等，已存在则跳过）。之后导入新流水时
   statement_utils.process_monthly_transactions 会自动确认命中的交易。
2. 回填：把历史上描述命中这些关键字、且仍未确认的 OCBC 交易一次性确认掉。
   逐条打印，便于在部署日志里复核；确认动作可在页面上用「批量解锁」撤销。

运行方式: python scripts/20260814_seed_ocbc_bank_charge_keywords.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from datetime import datetime

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.bank_keywords import BankStatementKeyword
from App_new.finance.models.statement import BankStatement, BankTransaction

BANK = 'OCBC'
KEYWORD_TYPE = 'bank_charge'

# 关键字按「出现在交易描述里的原文」写，匹配时不区分大小写（见 apply_keyword_matching）
KEYWORDS = [
    ('Txn Charges Billing', '交易手续费月结账单'),
    ('TRANS CHARGE', '单笔交易费'),
    ('CASH REBATE', '银行返现'),
    ('SERVICE CHARGE', '账户服务费'),
    ('MONTHLY ACCOUNT FEE', '账户月费'),
    ('FALL BELOW FEE', '余额不足月费'),
    ('INTEREST EARNED', '存款利息'),
]

app = create_app()

with app.app_context():
    # ---------- 1. 种入关键字 ----------
    added, skipped = 0, 0
    for kw, desc in KEYWORDS:
        exists = BankStatementKeyword.query.filter_by(bank_name=BANK, keyword=kw).first()
        if exists:
            # 已存在但类型不对（比如早先手工加成了 other），纠正过来
            if exists.keyword_type != KEYWORD_TYPE:
                print(f"  修正类型: {kw}  {exists.keyword_type} -> {KEYWORD_TYPE}")
                exists.keyword_type = KEYWORD_TYPE
                exists.is_active = True
                added += 1
            else:
                skipped += 1
            continue
        db.session.add(BankStatementKeyword(
            bank_name=BANK,
            keyword_type=KEYWORD_TYPE,
            keyword=kw,
            description=desc,
            is_active=True,
        ))
        print(f"  新增关键字: {kw}  ({desc})")
        added += 1

    db.session.commit()
    print(f"关键字种入完成：新增/修正 {added} 条，已存在跳过 {skipped} 条。")

    # ---------- 2. 回填历史未确认流水 ----------
    active_keywords = BankStatementKeyword.query.filter_by(
        bank_name=BANK, keyword_type=KEYWORD_TYPE, is_active=True
    ).all()

    if not active_keywords:
        print("没有启用的银行费用关键字，跳过回填。")
        sys.exit(0)

    pending = BankTransaction.query.join(BankStatement).filter(
        BankStatement.bank_name == BANK,
        BankTransaction.is_confirmed == False,
    ).all()

    now = datetime.utcnow()
    hit_count = 0
    try:
        for tx in pending:
            desc_lower = (tx.description or '').lower()
            hits = [k.keyword for k in active_keywords if k.keyword.lower() in desc_lower]
            if not hits:
                continue

            joined = ','.join(hits)
            print(f"  确认 tx#{tx.id} {tx.transaction_date} {tx.transaction_type} "
                  f"{tx.amount} | 命中[{joined}] | {(tx.description or '')[:60]}")
            tx.is_confirmed = True
            tx.confirmed_at = now
            tx.confirmed_by = 'auto'
            tx.is_reconciled = True
            tx.reconciled_at = now
            tx.reconciled_by = 'auto'
            note = f'银行费用自动确认（{joined}）'
            tx.remarks = (tx.remarks.rstrip() + ' ' + note) if (tx.remarks or '').strip() else note
            hit_count += 1

        db.session.commit()
        print(f"回填完成：确认 {hit_count} 条（扫描未确认流水 {len(pending)} 条）。")
        print("对账单状态无需手动更新，打开 OCBC 页面时会自动重算。")
    except Exception as e:
        db.session.rollback()
        print(f"回填失败，已回滚：{e}")
        raise
