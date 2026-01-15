# -*- coding: utf-8 -*-
"""
迁移 IndiGo 预付款 R479, R480, R497

运行方式: python scripts/migrate_indigo_prepayments_r479.py
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


# IndiGo 预付款数据
INDIGO_PREPAYMENTS = [
    {
        'ref_number': 'R479',
        'description': 'Top up Indigo airline account',
        'eo_number': '441',
        'amount': Decimal('2000.00'),
        'balance': Decimal('2000.00'),
        'date_hint': '2025-09-19',
    },
    {
        'ref_number': 'R480',
        'description': 'Top up Indigo airline account',
        'eo_number': '442',
        'amount': Decimal('2000.00'),
        'balance': Decimal('2000.00'),
        'date_hint': '2025-09-19',
    },
    {
        'ref_number': 'R497',
        'description': '22sep-Top up Indigo airline account',
        'eo_number': '459',
        'amount': Decimal('2000.00'),
        'balance': Decimal('311.50'),
        'date_hint': '2025-09-22',
    },
]

SUPPLIER_NAME = 'IndiGo in Singapore'


def delete_project(project):
    """删除项目及其所有关联数据"""
    refs = ProjectRef.query.filter_by(header_id=project.id).all()
    ref_ids = [ref.id for ref in refs]

    if ref_ids:
        ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).delete(synchronize_session=False)
        InvoiceItem.query.filter(InvoiceItem.ref_id.in_(ref_ids)).delete(synchronize_session=False)

        visa_projects = VisaProject.query.filter(VisaProject.ref_id.in_(ref_ids)).all()
        for vp in visa_projects:
            VisaProjectDocumentStatus.query.filter_by(project_id=vp.id).delete(synchronize_session=False)
            VisaProjectFile.query.filter_by(project_id=vp.id).delete(synchronize_session=False)
            db.session.delete(vp)

    invoices = ProjectInvoice.query.filter_by(header_id=project.id).all()
    for invoice in invoices:
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete(synchronize_session=False)
        db.session.delete(invoice)

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
        print("=" * 60)
        print("  迁移 IndiGo 预付款 R479, R480, R497")
        print("=" * 60)

        # 获取供应商
        supplier = CustomerCompany.query.filter_by(company_name=SUPPLIER_NAME).first()
        if not supplier:
            print(f"错误: 找不到供应商 {SUPPLIER_NAME}")
            return

        print(f"\n供应商: {supplier.company_name} (ID: {supplier.id})")

        created_count = 0
        skipped_count = 0
        projects_to_delete = set()

        print("\n[1/2] 创建预付款记录...")
        print("-" * 60)

        for item in INDIGO_PREPAYMENTS:
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

            # 查找 REF 获取日期
            ref = ProjectRef.query.filter_by(ref_number=ref_number).first()
            if ref:
                projects_to_delete.add(ref.header_id)
                payment_date = ref.created_at.date() if ref.created_at else date.today()
            else:
                payment_date = datetime.strptime(item['date_hint'], '%Y-%m-%d').date()

            # 确定状态
            if item['balance'] <= 0:
                status = 'consumed'
            elif item['balance'] < item['amount']:
                status = 'partial_used'
            else:
                status = 'confirmed'

            prepayment_number = SupplierPrepayment.generate_prepayment_number()

            prepayment = SupplierPrepayment(
                prepayment_number=prepayment_number,
                supplier_id=supplier.id,
                amount=item['amount'],
                currency='SGD',
                payment_date=payment_date,
                payment_method='bank_transfer',
                balance_amount=item['balance'],
                status=status,
                remarks=f"从项目迁移: {ref_number} - {item['description']}",
                reference=f"EO{item['eo_number']}",
                created_by='system_migrate',
            )
            db.session.add(prepayment)
            created_count += 1

            print(f"  创建 {prepayment_number}: {item['description']}")
            print(f"         金额: SGD {item['amount']:,.2f}, 余额: SGD {item['balance']:,.2f}, 状态: {status}")

        print(f"\n  创建: {created_count} 条, 跳过: {skipped_count} 条")

        # 删除相关项目
        print("\n[2/2] 删除相关项目...")
        print("-" * 60)

        deleted_count = 0
        for header_id in projects_to_delete:
            project = ProjectHeader.query.get(header_id)
            if project:
                print(f"  删除: {project.hid} - {project.desc}")
                delete_project(project)
                deleted_count += 1

        try:
            db.session.commit()
            print(f"\n迁移完成！删除 {deleted_count} 个项目")
        except Exception as e:
            db.session.rollback()
            print(f"\n保存失败: {str(e)}")
            import traceback
            traceback.print_exc()

        print(f"\n预付款列表: https://www.joyesc.com/projects/prepayment/")


if __name__ == '__main__':
    main()
