# -*- coding: utf-8 -*-
"""
从现有业务数据生成日记账分录
创建日期: 2026-01-10
说明: 为已存在的 Invoice/Receipt/EO 补充生成日记账
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_journal_entries():
    """从现有业务数据生成日记账"""
    from App_new.exts import db
    from App_new.finance.models.chart_of_account import ChartOfAccount
    from App_new.finance.models.journal_entry import JournalEntry, JournalEntryLine
    from App_new.business.projects.models.invoice import ProjectInvoice
    from App_new.business.projects.models.receipt import ProjectReceipt
    from App_new.business.projects.models.eo import ProjectEO

    print("=" * 60)
    print("从现有业务数据生成日记账分录")
    print("=" * 60)

    # 1. 先确保会计科目已初始化
    account_count = ChartOfAccount.query.count()
    if account_count == 0:
        print("\n1. 初始化会计科目...")
        ChartOfAccount.init_default_accounts()
        print(f"   已创建 {ChartOfAccount.query.count()} 个科目")
    else:
        print(f"\n1. 会计科目已存在 ({account_count} 个)")

    # 检查关键科目
    required_accounts = {
        '1002': 'Bank',
        '1100': 'Accounts Receivable',
        '4100': 'Sales Revenue',
        '5100': 'Cost of Sales'
    }
    missing_accounts = []
    for code, name in required_accounts.items():
        if not ChartOfAccount.get_by_code(code):
            missing_accounts.append(code)

    if missing_accounts:
        print(f"   警告: 缺少关键科目 {missing_accounts}")
        print("   正在重新初始化...")
        ChartOfAccount.init_default_accounts()

    # 统计
    invoice_created = 0
    receipt_created = 0
    eo_created = 0
    skipped = 0
    errors = []

    # 2. 处理已发送/已付款的 Invoice
    print("\n2. 处理 Invoice（sent/paid/partial_paid/overdue）...")
    invoices = ProjectInvoice.query.filter(
        ProjectInvoice.status.in_(['sent', 'paid', 'partial_paid', 'overdue'])
    ).all()
    print(f"   找到 {len(invoices)} 张发票")

    for invoice in invoices:
        # 检查是否已有日记账
        existing = JournalEntry.query.filter_by(
            source_type='invoice',
            source_id=invoice.id
        ).first()

        if existing:
            skipped += 1
            continue

        try:
            entry = JournalEntry.create_from_invoice(invoice, user='system')
            if entry and entry.lines:
                db.session.add(entry)
                db.session.flush()
                entry.post(user='system')
                invoice_created += 1
        except Exception as e:
            errors.append(f"Invoice {invoice.invoice_number}: {str(e)}")

    print(f"   创建 {invoice_created} 条日记账")

    # 3. 处理已确认的 Receipt
    print("\n3. 处理 Receipt（已确认状态）...")
    receipts = ProjectReceipt.query.filter_by(status='confirmed').all()
    print(f"   找到 {len(receipts)} 条已确认收款")

    for receipt in receipts:
        existing = JournalEntry.query.filter_by(
            source_type='receipt',
            source_id=receipt.id
        ).first()

        if existing:
            skipped += 1
            continue

        try:
            entry = JournalEntry.create_from_receipt(receipt, user='system')
            if entry and entry.lines:
                db.session.add(entry)
                db.session.flush()
                entry.post(user='system')
                receipt_created += 1
        except Exception as e:
            errors.append(f"Receipt {receipt.receipt_number}: {str(e)}")

    print(f"   创建 {receipt_created} 条日记账")

    # 4. 处理已付款的 EO
    print("\n4. 处理 EO（已付款状态）...")
    eos = ProjectEO.query.filter_by(status='paid').all()
    print(f"   找到 {len(eos)} 条已付款EO")

    for eo in eos:
        existing = JournalEntry.query.filter_by(
            source_type='eo',
            source_id=eo.id
        ).first()

        if existing:
            skipped += 1
            continue

        try:
            entry = JournalEntry.create_from_eo(eo, user='system')
            if entry and entry.lines:
                db.session.add(entry)
                db.session.flush()
                entry.post(user='system')
                eo_created += 1
        except Exception as e:
            errors.append(f"EO {eo.eo_number}: {str(e)}")

    print(f"   创建 {eo_created} 条日记账")

    # 提交
    db.session.commit()

    # 汇总
    print("\n" + "=" * 60)
    print("生成完成！")
    print("=" * 60)
    print(f"  Invoice 日记账: {invoice_created} 条")
    print(f"  Receipt 日记账: {receipt_created} 条")
    print(f"  EO 日记账: {eo_created} 条")
    print(f"  跳过（已存在）: {skipped} 条")
    print(f"  总计新建: {invoice_created + receipt_created + eo_created} 条")

    if errors:
        print(f"\n错误 ({len(errors)}):")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 个错误")

    # 验证
    total_posted = JournalEntry.query.filter_by(status='posted').count()
    print(f"\n当前已过账日记账总数: {total_posted}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='从现有业务数据生成日记账分录')
    parser.add_argument('--execute', action='store_true', help='执行生成')
    args = parser.parse_args()

    if not args.execute:
        print("此脚本将从现有的 Invoice/Receipt/EO 数据生成日记账分录")
        print()
        print("处理规则:")
        print("  - Invoice: 状态为 'sent' 的发票")
        print("  - Receipt: 状态为 'confirmed' 的收款")
        print("  - EO: 状态为 'paid' 的付款单")
        print()
        print("使用 --execute 参数执行生成")
        print("示例: python scripts/20260110_generate_journal_entries.py --execute")
        return

    from App_new import create_app
    app = create_app()
    with app.app_context():
        generate_journal_entries()


if __name__ == '__main__':
    main()
