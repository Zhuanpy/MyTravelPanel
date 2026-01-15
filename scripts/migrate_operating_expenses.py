# -*- coding: utf-8 -*-
"""
迁移运营费用脚本

功能：
1. 将运营费用数据写入 OperatingExpense 表
2. 删除 Projects 中的运营费用项目

运行方式: python scripts/migrate_operating_expenses.py
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
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.project_member import ProjectMember


# ============================================================
# 运营费用数据配置
# ============================================================

# 2025年运营费用 - 日期: 2025-01-15
EXPENSES_2025 = {
    'date': date(2025, 1, 15),
    'items': [
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
}

# 2026年运营费用 - 日期: 今天
EXPENSES_2026 = {
    'date': date(2026, 1, 15),
    'items': [
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
}

# 需要删除的项目
PROJECTS_TO_DELETE = ['H152', 'H899']


# ============================================================
# 功能函数
# ============================================================

def get_expense_account():
    """获取费用科目"""
    expense_account = ChartOfAccount.query.filter(
        ChartOfAccount.account_type == 'expense',
        ChartOfAccount.is_active == True
    ).first()

    if not expense_account:
        # 创建默认费用科目
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
        print(f"  创建费用科目: {expense_account.code} - {expense_account.name}")

    return expense_account


def add_operating_expenses(expense_data, expense_account):
    """添加运营费用"""
    expense_date = expense_data['date']
    items = expense_data['items']

    created_count = 0
    skipped_count = 0
    total_amount = Decimal('0')

    for item in items:
        # 检查是否已存在
        existing = OperatingExpense.query.filter(
            OperatingExpense.description == item['description'],
            OperatingExpense.amount == item['amount'],
            OperatingExpense.payee_name == item['payee_name']
        ).first()

        if existing:
            print(f"    跳过 {item['ref_number']}: {item['description']} - 已存在")
            skipped_count += 1
            continue

        # 生成费用单编号
        expense_number = OperatingExpense.generate_expense_number()

        # 备注信息
        remarks_parts = [f"从 Athina 导入: REF {item['ref_number']}"]
        if item.get('eo_number'):
            remarks_parts.append(f"EO {item['eo_number']}")
        if item.get('invoice_no'):
            remarks_parts.append(f"Invoice {item['invoice_no']}")

        # 创建运营费用记录
        expense = OperatingExpense(
            expense_number=expense_number,
            expense_date=expense_date,
            expense_account_id=expense_account.id,
            amount=item['amount'],
            currency=item['currency'],
            payment_method='bank_transfer',
            payee_name=item['payee_name'],
            description=item['description'],
            remarks=', '.join(remarks_parts),
            status='paid',
            created_by='system_import',
        )
        db.session.add(expense)
        created_count += 1
        total_amount += item['amount']
        print(f"    创建 {expense_number}: {item['description']} - {item['currency']} {item['amount']}")

    return created_count, skipped_count, total_amount


def delete_project(hid):
    """删除项目及其所有关联数据"""
    project = ProjectHeader.query.filter_by(hid=hid).first()

    if not project:
        print(f"    项目 {hid} 不存在，跳过")
        return False

    print(f"    删除项目: {project.hid} - {project.desc}")

    # 获取所有 REF
    refs = ProjectRef.query.filter_by(header_id=project.id).all()
    ref_ids = [ref.id for ref in refs]

    # 1. 删除 EO
    if ref_ids:
        eos = ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).all()
        for eo in eos:
            db.session.delete(eo)
        if eos:
            print(f"      - EO: {len(eos)} 条")

    # 2. 删除 InvoiceItem
    if ref_ids:
        invoice_items = InvoiceItem.query.filter(InvoiceItem.ref_id.in_(ref_ids)).all()
        for item in invoice_items:
            db.session.delete(item)
        if invoice_items:
            print(f"      - InvoiceItem: {len(invoice_items)} 条")

    # 3. 删除 Invoice
    invoices = ProjectInvoice.query.filter_by(header_id=project.id).all()
    for invoice in invoices:
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        db.session.delete(invoice)
    if invoices:
        print(f"      - Invoice: {len(invoices)} 条")

    # 4. 删除 Receipt
    receipts = ProjectReceipt.query.filter_by(header_id=project.id).all()
    for receipt in receipts:
        db.session.delete(receipt)
    if receipts:
        print(f"      - Receipt: {len(receipts)} 条")

    # 5. 删除 ProjectMember
    members = ProjectMember.query.filter_by(header_id=project.id).all()
    for member in members:
        db.session.delete(member)
    if members:
        print(f"      - Member: {len(members)} 条")

    # 6. 删除 REF
    for ref in refs:
        db.session.delete(ref)
    if refs:
        print(f"      - REF: {len(refs)} 条")

    # 7. 删除 ProjectHeader
    db.session.delete(project)
    print(f"      - ProjectHeader: 1 条")

    return True


def main():
    """主函数"""
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("       运营费用迁移脚本")
        print("=" * 70)

        # 获取费用科目
        print("\n[1/3] 获取费用科目...")
        expense_account = get_expense_account()
        print(f"  使用费用科目: {expense_account.code} - {expense_account.name}")

        # 添加运营费用
        print("\n[2/3] 添加运营费用...")

        total_created = 0
        total_skipped = 0
        grand_total = Decimal('0')

        # 2025年费用
        print(f"\n  >> 2025年运营费用 (日期: {EXPENSES_2025['date']})")
        created, skipped, amount = add_operating_expenses(EXPENSES_2025, expense_account)
        total_created += created
        total_skipped += skipped
        grand_total += amount

        # 2026年费用
        print(f"\n  >> 2026年运营费用 (日期: {EXPENSES_2026['date']})")
        created, skipped, amount = add_operating_expenses(EXPENSES_2026, expense_account)
        total_created += created
        total_skipped += skipped
        grand_total += amount

        print(f"\n  运营费用添加完成: 创建 {total_created} 条, 跳过 {total_skipped} 条, 总金额 SGD {grand_total:,.2f}")

        # 删除项目
        print("\n[3/3] 删除运营费用项目...")
        deleted_count = 0
        for hid in PROJECTS_TO_DELETE:
            if delete_project(hid):
                deleted_count += 1

        print(f"\n  项目删除完成: {deleted_count} 个")

        # 提交更改
        try:
            db.session.commit()
            print("\n" + "=" * 70)
            print("  迁移完成！数据已保存")
            print("=" * 70)
        except Exception as e:
            db.session.rollback()
            print(f"\n保存失败: {str(e)}")
            return

        # 输出访问链接
        print(f"\n运营费用列表: https://www.joyesc.com/ledger/operating-expenses")
        print(f"项目列表: https://www.joyesc.com/projects/list")


if __name__ == '__main__':
    main()
