# -*- coding: utf-8 -*-
"""
迁移 SCOOT AIRLINE 单条预付款 R482

运行方式: python scripts/migrate_scoot_prepayment_r482.py
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


# 预付款数据
PREPAYMENT_DATA = {
    'ref_number': 'R482',
    'description': 'Top up SCOOT AIRLINE account-20250919',
    'eo_number': '443',
    'amount': Decimal('2000.00'),
    'balance': Decimal('0.00'),
    'date_hint': '2025-09-19',
    'supplier_name': 'SCOOT AIRLINE',
}


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
        print("  迁移 SCOOT AIRLINE 预付款 R482")
        print("=" * 60)

        item = PREPAYMENT_DATA

        # 获取供应商
        supplier = CustomerCompany.query.filter_by(company_name=item['supplier_name']).first()
        if not supplier:
            print(f"错误: 找不到供应商 {item['supplier_name']}")
            return

        print(f"\n供应商: {supplier.company_name} (ID: {supplier.id})")

        # 检查是否已存在
        existing = SupplierPrepayment.query.filter(
            SupplierPrepayment.remarks.like(f"%{item['ref_number']}%")
        ).first()

        if existing:
            print(f"\n预付款已存在: {existing.prepayment_number}，跳过创建")
        else:
            # 查找 REF 获取日期
            ref = ProjectRef.query.filter_by(ref_number=item['ref_number']).first()
            if ref:
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
                remarks=f"从项目迁移: {item['ref_number']} - {item['description']}",
                reference=f"EO{item['eo_number']}",
                created_by='system_migrate',
            )
            db.session.add(prepayment)
            print(f"\n创建预付款: {prepayment_number}")
            print(f"  金额: SGD {item['amount']:,.2f}")
            print(f"  余额: SGD {item['balance']:,.2f}")
            print(f"  状态: {status}")

        # 查找并删除项目
        ref = ProjectRef.query.filter_by(ref_number=item['ref_number']).first()
        if ref:
            project = ProjectHeader.query.get(ref.header_id)
            if project:
                print(f"\n删除项目: {project.hid} - {project.desc}")
                delete_project(project)

        try:
            db.session.commit()
            print("\n迁移完成！")
        except Exception as e:
            db.session.rollback()
            print(f"\n保存失败: {str(e)}")
            import traceback
            traceback.print_exc()

        print(f"\n预付款列表: https://www.joyesc.com/projects/prepayment/")


if __name__ == '__main__':
    main()
