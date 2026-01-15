# -*- coding: utf-8 -*-
"""
迁移 Indigo Airline 预付款脚本

功能：
1. 查找包含 Indigo 充值 REF 的项目
2. 将预付款数据写入 SupplierPrepayment 表
3. 删除相关项目

运行方式: python scripts/migrate_indigo_prepayments.py
"""

import sys
import os
from datetime import date, datetime
from decimal import Decimal

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.project_member import ProjectMember
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment


# Indigo Airline 预付款 REF 数据
INDIGO_PREPAYMENTS = [
    {
        'ref_number': 'R608',
        'description': '22sep-Top up Indigo airline account',
        'eo_number': '567',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-09-22',
    },
    {
        'ref_number': 'R763',
        'description': '02NOV - Top up Indigo airline account',
        'eo_number': '717',
        'amount': Decimal('3000.00'),
        'balance': Decimal('1151.60'),
        'date_hint': '2025-11-02',
    },
    {
        'ref_number': 'R764',
        'description': '29NOV-Top up Indigo airline account',
        'eo_number': '862',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-11-29',
    },
    {
        'ref_number': 'R950',
        'description': 'INDIGO-REFUND',
        'eo_number': '895',
        'amount': Decimal('453.60'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-12-01',
        'is_refund': True,
    },
    {
        'ref_number': 'R1015',
        'description': '08DEC - Top up Indigo airline account',
        'eo_number': '957',
        'amount': Decimal('3000.00'),
        'balance': Decimal('3000.00'),
        'date_hint': '2025-12-08',
    },
    {
        'ref_number': 'R1034',
        'description': '10DEC - Top up Indigo airline account',
        'eo_number': '981',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-12-10',
    },
    {
        'ref_number': 'R1075',
        'description': '15DEC - Top up Indigo airline account',
        'eo_number': '1014',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-12-15',
    },
    {
        'ref_number': 'R1110',
        'description': '18DEC - Top up Indigo airline account',
        'eo_number': '1047',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-12-18',
    },
    {
        'ref_number': 'R1114',
        'description': '18DEC - Top up Indigo airline account',
        'eo_number': '1052',
        'amount': Decimal('2000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-12-18',
    },
    {
        'ref_number': 'R1164',
        'description': '18DEC - Top up Indigo airline account',
        'eo_number': '1099',
        'amount': Decimal('3000.00'),
        'balance': Decimal('1627.40'),
        'date_hint': '2025-12-18',
    },
]


def get_or_create_supplier(supplier_name):
    """获取或创建供应商"""
    supplier = CustomerCompany.query.filter_by(company_name=supplier_name).first()

    if not supplier:
        supplier = CustomerCompany(
            company_name=supplier_name,
            is_customer=False,
            is_supplier=True,
            status='active',
        )
        db.session.add(supplier)
        db.session.flush()
        print(f"  创建供应商: {supplier_name}")

    return supplier


def delete_project(project):
    """删除项目及其所有关联数据"""
    # 获取所有 REF
    refs = ProjectRef.query.filter_by(header_id=project.id).all()
    ref_ids = [ref.id for ref in refs]

    # 1. 删除 EO
    if ref_ids:
        ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).delete(synchronize_session=False)

    # 2. 删除 InvoiceItem
    if ref_ids:
        InvoiceItem.query.filter(InvoiceItem.ref_id.in_(ref_ids)).delete(synchronize_session=False)

    # 3. 删除 Invoice 及其 Items
    invoices = ProjectInvoice.query.filter_by(header_id=project.id).all()
    for invoice in invoices:
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete(synchronize_session=False)
        db.session.delete(invoice)

    # 4. 删除 Receipt
    ProjectReceipt.query.filter_by(header_id=project.id).delete(synchronize_session=False)

    # 5. 删除 ProjectMember
    ProjectMember.query.filter_by(header_id=project.id).delete(synchronize_session=False)

    # 6. 删除 REF
    ProjectRef.query.filter_by(header_id=project.id).delete(synchronize_session=False)

    # 7. 删除 ProjectHeader
    db.session.delete(project)


def main():
    """主函数"""
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("       Indigo Airline 预付款迁移脚本")
        print("=" * 70)

        # 获取或创建 Indigo 供应商
        supplier = get_or_create_supplier('INDIGO AIRLINE')
        print(f"\n供应商: {supplier.company_name} (ID: {supplier.id})")

        created_count = 0
        skipped_count = 0
        projects_to_delete = set()

        print("\n[1/3] 创建预付款记录...")
        print("-" * 70)

        for item in INDIGO_PREPAYMENTS:
            ref_number = item['ref_number']

            # 检查是否已存在
            existing = SupplierPrepayment.query.filter(
                SupplierPrepayment.remarks.like(f'%{ref_number}%')
            ).first()

            if existing:
                print(f"  跳过 {ref_number}: 已存在 ({existing.prepayment_number})")
                skipped_count += 1

                # 仍然查找项目以便删除
                ref = ProjectRef.query.filter_by(ref_number=ref_number).first()
                if ref and ref.header_id:
                    projects_to_delete.add(ref.header_id)
                continue

            # 查找 REF 记录
            ref = ProjectRef.query.filter_by(ref_number=ref_number).first()
            if ref:
                projects_to_delete.add(ref.header_id)
                payment_date = ref.created_at.date() if ref.created_at else date.today()
            else:
                # 从描述解析日期
                try:
                    payment_date = datetime.strptime(item['date_hint'], '%Y-%m-%d').date()
                except:
                    payment_date = date.today()

            # 确定状态
            balance = item['balance']
            amount = item['amount']

            if balance <= 0:
                status = 'consumed'
            elif balance < amount:
                status = 'partial_used'
            else:
                status = 'confirmed'

            # 跳过退款记录（负数处理或单独记录）
            is_refund = item.get('is_refund', False)
            remarks_prefix = "退款 - " if is_refund else ""

            # 生成预付编号
            prepayment_number = SupplierPrepayment.generate_prepayment_number()

            # 创建预付款记录
            prepayment = SupplierPrepayment(
                prepayment_number=prepayment_number,
                supplier_id=supplier.id,
                amount=amount,
                currency='SGD',
                payment_date=payment_date,
                payment_method='bank_transfer',
                balance_amount=balance,
                status=status,
                remarks=f"{remarks_prefix}从项目迁移: {ref_number} - {item['description']}",
                reference=f"EO{item['eo_number']}",
                created_by='system_migrate',
            )
            db.session.add(prepayment)
            created_count += 1

            print(f"  创建 {prepayment_number}: {item['description']}")
            print(f"         金额: SGD {amount:,.2f}, 余额: SGD {balance:,.2f}, 状态: {status}")

        print(f"\n  预付款创建完成: {created_count} 条, 跳过: {skipped_count} 条")

        # 查找并删除相关项目
        print("\n[2/3] 查找相关项目...")
        print("-" * 70)

        projects_found = []
        for header_id in projects_to_delete:
            project = ProjectHeader.query.get(header_id)
            if project:
                projects_found.append(project)
                print(f"  找到项目: {project.hid} - {project.desc}")

        print(f"\n  共找到 {len(projects_found)} 个项目")

        print("\n[3/3] 删除相关项目...")
        print("-" * 70)

        deleted_count = 0
        for project in projects_found:
            print(f"  删除: {project.hid} - {project.desc}")
            delete_project(project)
            deleted_count += 1

        # 提交更改
        try:
            db.session.commit()
            print("\n" + "=" * 70)
            print("  迁移完成！数据已保存")
            print("=" * 70)
        except Exception as e:
            db.session.rollback()
            print(f"\n保存失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return

        # 输出统计
        print(f"\n统计:")
        print(f"  创建预付款: {created_count} 条")
        print(f"  跳过: {skipped_count} 条")
        print(f"  删除项目: {deleted_count} 个")

        # 计算总金额
        total_amount = sum(item['amount'] for item in INDIGO_PREPAYMENTS)
        total_balance = sum(item['balance'] for item in INDIGO_PREPAYMENTS)
        print(f"\n  总充值金额: SGD {total_amount:,.2f}")
        print(f"  总剩余余额: SGD {total_balance:,.2f}")

        print(f"\n预付款列表: https://www.joyesc.com/projects/prepayment/")
        print(f"项目列表: https://www.joyesc.com/projects/list")


if __name__ == '__main__':
    main()
