# -*- coding: utf-8 -*-
"""
迁移 US-BANGLA AIRLINES 预付款脚本

运行方式: python scripts/migrate_usbangla_prepayments.py
"""

import sys
import os
from datetime import date, datetime
from decimal import Decimal

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
from App_new.business.visa.models.Visamodels import VisaProject, VisaProjectDocumentStatus, VisaProjectFile


# US-BANGLA AIRLINES 预付款数据
USBANGLA_PREPAYMENTS = [
    {
        'ref_number': 'R519',
        'description': '24sep-Top up US BANGLA AIRLINES account',
        'eo_number': '480',
        'amount': Decimal('2000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-09-24',
    },
    {
        'ref_number': 'R543',
        'description': '29sep-Top up US BANGLA AIRLINES account',
        'eo_number': '505',
        'amount': Decimal('2500.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-09-29',
    },
    {
        'ref_number': 'R609',
        'description': '07oct-Top up US BANGLA AIRLINES account',
        'eo_number': '570',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-10-07',
    },
    {
        'ref_number': 'R663',
        'description': '14oct-Top up US BANGLA AIRLINES account',
        'eo_number': '623',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-10-14',
    },
    {
        'ref_number': 'R757',
        'description': '08nov - Top up US BANGLA AIRLINES account',
        'eo_number': '743',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-11-08',
    },
    {
        'ref_number': 'R758',
        'description': '01nov - Top up US BANGLA AIRLINES account',
        'eo_number': '712',
        'amount': Decimal('3000.00'),
        'balance': Decimal('3000.00'),
        'date_hint': '2025-11-01',
    },
    {
        'ref_number': 'R824',
        'description': '12nov - Top up US BANGLA AIRLINES account',
        'eo_number': '772',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-11-12',
    },
    {
        'ref_number': 'R869',
        'description': '18nov - Top up US BANGLA AIRLINES account',
        'eo_number': '812',
        'amount': Decimal('3000.00'),
        'balance': Decimal('0.00'),
        'date_hint': '2025-11-18',
    },
    {
        'ref_number': 'R914',
        'description': '24nov - Top up US BANGLA AIRLINES account',
        'eo_number': '861',
        'amount': Decimal('3000.00'),
        'balance': Decimal('1241.37'),
        'date_hint': '2025-11-24',
    },
    {
        'ref_number': 'R943',
        'description': '24nov - Top up US BANGLA AIRLINES account',
        'eo_number': '890',
        'amount': Decimal('356.71'),
        'balance': Decimal('356.71'),
        'date_hint': '2025-11-24',
    },
    {
        'ref_number': 'R1212',
        'description': '02jan - Top up US BANGLA AIRLINES account',
        'eo_number': '1146',
        'amount': Decimal('50.00'),
        'balance': Decimal('50.00'),
        'date_hint': '2026-01-02',
    },
    {
        'ref_number': 'R1238',
        'description': '06jan - Top up US BANGLA AIRLINES account',
        'eo_number': '1173',
        'amount': Decimal('3000.00'),
        'balance': Decimal('3000.00'),
        'date_hint': '2026-01-06',
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
    refs = ProjectRef.query.filter_by(header_id=project.id).all()
    ref_ids = [ref.id for ref in refs]

    if ref_ids:
        ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).delete(synchronize_session=False)
        InvoiceItem.query.filter(InvoiceItem.ref_id.in_(ref_ids)).delete(synchronize_session=False)

        # 删除 VisaProject 及其关联数据
        visa_projects = VisaProject.query.filter(VisaProject.ref_id.in_(ref_ids)).all()
        for vp in visa_projects:
            VisaProjectDocumentStatus.query.filter_by(project_id=vp.id).delete(synchronize_session=False)
            VisaProjectFile.query.filter_by(project_id=vp.id).delete(synchronize_session=False)
            db.session.delete(vp)

    invoices = ProjectInvoice.query.filter_by(header_id=project.id).all()
    for invoice in invoices:
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete(synchronize_session=False)
        db.session.delete(invoice)

    # 也删除通过 header_id 关联的 VisaProject
    visa_projects_by_header = VisaProject.query.filter_by(header_id=project.id).all()
    for vp in visa_projects_by_header:
        VisaProjectDocumentStatus.query.filter_by(project_id=vp.id).delete(synchronize_session=False)
        VisaProjectFile.query.filter_by(project_id=vp.id).delete(synchronize_session=False)
        db.session.delete(vp)

    ProjectReceipt.query.filter_by(header_id=project.id).delete(synchronize_session=False)
    ProjectMember.query.filter_by(header_id=project.id).delete(synchronize_session=False)
    ProjectRef.query.filter_by(header_id=project.id).delete(synchronize_session=False)
    db.session.delete(project)


def main():
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("       US-BANGLA AIRLINES 预付款迁移脚本")
        print("=" * 70)

        supplier = get_or_create_supplier('US-BANGLA AIRLINES LTD')
        print(f"\n供应商: {supplier.company_name} (ID: {supplier.id})")

        created_count = 0
        skipped_count = 0
        projects_to_delete = set()

        print("\n[1/3] 创建预付款记录...")
        print("-" * 70)

        for item in USBANGLA_PREPAYMENTS:
            ref_number = item['ref_number']

            # 检查是否已存在
            existing = SupplierPrepayment.query.filter(
                SupplierPrepayment.remarks.like(f'%{ref_number}%')
            ).first()

            if existing:
                print(f"  跳过 {ref_number}: 已存在 ({existing.prepayment_number})")
                skipped_count += 1
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

            prepayment_number = SupplierPrepayment.generate_prepayment_number()

            prepayment = SupplierPrepayment(
                prepayment_number=prepayment_number,
                supplier_id=supplier.id,
                amount=amount,
                currency='SGD',
                payment_date=payment_date,
                payment_method='bank_transfer',
                balance_amount=balance,
                status=status,
                remarks=f"从项目迁移: {ref_number} - {item['description']}",
                reference=f"EO{item['eo_number']}",
                created_by='system_migrate',
            )
            db.session.add(prepayment)
            created_count += 1

            print(f"  创建 {prepayment_number}: {item['description']}")
            print(f"         金额: SGD {amount:,.2f}, 余额: SGD {balance:,.2f}, 状态: {status}")

        print(f"\n  预付款创建完成: {created_count} 条, 跳过: {skipped_count} 条")

        # 删除相关项目
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

        total_amount = sum(item['amount'] for item in USBANGLA_PREPAYMENTS)
        total_balance = sum(item['balance'] for item in USBANGLA_PREPAYMENTS)

        print(f"\n统计:")
        print(f"  创建预付款: {created_count} 条")
        print(f"  跳过: {skipped_count} 条")
        print(f"  删除项目: {deleted_count} 个")
        print(f"\n  总充值金额: SGD {total_amount:,.2f}")
        print(f"  总剩余余额: SGD {total_balance:,.2f}")

        print(f"\n预付款列表: https://www.joyesc.com/projects/prepayment/")


if __name__ == '__main__':
    main()
