# -*- coding: utf-8 -*-
"""
迁移预付款脚本

功能：
1. 将 Projects 中的预付款项目数据写入 SupplierPrepayment 表
2. 删除 Projects 中的预付款项目

运行方式: python scripts/migrate_prepayments.py
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


# 需要迁移的预付款项目
PREPAYMENT_PROJECTS = ['H902', 'H764', 'H723', 'H630', 'H492', 'H363']


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
        print(f"    创建供应商: {supplier_name}")

    return supplier


def migrate_project_to_prepayment(project):
    """将项目迁移为预付款记录"""
    print(f"\n  处理项目: {project.hid} - {project.desc}")

    # 获取项目的所有 REF
    refs = ProjectRef.query.filter_by(header_id=project.id).all()

    if not refs:
        print(f"    警告: 项目没有 REF 记录，跳过")
        return None

    # 获取供应商（从第一个 REF 或描述中提取）
    supplier_name = 'SCOOT AIRLINE'  # 默认供应商
    for ref in refs:
        if ref.supplier_name:
            supplier_name = ref.supplier_name
            break

    supplier = get_or_create_supplier(supplier_name)

    # 计算总金额（从所有 REF 汇总）
    total_amount = sum(Decimal(str(ref.cost_price or 0)) for ref in refs)

    # 计算已使用金额（总金额 - 未付款）
    total_selling = sum(Decimal(str(ref.selling_price or 0)) for ref in refs)

    # 获取收款记录计算已使用金额
    receipts = ProjectReceipt.query.filter(
        ProjectReceipt.header_id == project.id,
        ProjectReceipt.status == 'confirmed'
    ).all()
    total_received = sum(Decimal(str(r.amount or 0)) for r in receipts)

    # 余额 = 总金额 - 已收款（已使用部分）
    balance = total_amount - total_received
    if balance < 0:
        balance = Decimal('0')  # 余额不能为负

    # 获取付款日期（从项目创建时间）
    payment_date = project.created_at.date() if project.created_at else date.today()

    # 提取参考号（从描述中）
    reference = None
    desc = project.desc or ''
    if '-' in desc:
        parts = desc.split('-')
        for part in parts:
            if part.strip().startswith('A') or part.strip().startswith('2025') or part.strip().startswith('2024'):
                reference = part.strip()
                break

    # 生成预付编号
    prepayment_number = SupplierPrepayment.generate_prepayment_number()

    # 确定状态
    if balance <= 0:
        status = 'consumed'
    elif balance < total_amount:
        status = 'partial_used'
    else:
        status = 'confirmed'

    # 创建预付款记录
    prepayment = SupplierPrepayment(
        prepayment_number=prepayment_number,
        supplier_id=supplier.id,
        amount=total_amount,
        currency='SGD',
        payment_date=payment_date,
        payment_method='bank_transfer',
        balance_amount=balance,
        status=status,
        remarks=f"从项目迁移: {project.hid} - {project.desc}",
        reference=reference,
        created_by='system_migrate',
    )
    db.session.add(prepayment)

    print(f"    创建预付款: {prepayment_number}")
    print(f"      供应商: {supplier_name}")
    print(f"      金额: SGD {total_amount:,.2f}")
    print(f"      余额: SGD {balance:,.2f}")
    print(f"      日期: {payment_date}")
    print(f"      状态: {status}")
    print(f"      REF数量: {len(refs)}")

    return prepayment


def delete_project(project):
    """删除项目及其所有关联数据"""
    # 获取所有 REF
    refs = ProjectRef.query.filter_by(header_id=project.id).all()
    ref_ids = [ref.id for ref in refs]

    deleted = {'eos': 0, 'invoice_items': 0, 'invoices': 0, 'receipts': 0, 'members': 0, 'refs': 0}

    # 1. 删除 EO
    if ref_ids:
        eos = ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).all()
        deleted['eos'] = len(eos)
        for eo in eos:
            db.session.delete(eo)

    # 2. 删除 InvoiceItem
    if ref_ids:
        invoice_items = InvoiceItem.query.filter(InvoiceItem.ref_id.in_(ref_ids)).all()
        deleted['invoice_items'] = len(invoice_items)
        for item in invoice_items:
            db.session.delete(item)

    # 3. 删除 Invoice
    invoices = ProjectInvoice.query.filter_by(header_id=project.id).all()
    deleted['invoices'] = len(invoices)
    for invoice in invoices:
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        db.session.delete(invoice)

    # 4. 删除 Receipt
    receipts = ProjectReceipt.query.filter_by(header_id=project.id).all()
    deleted['receipts'] = len(receipts)
    for receipt in receipts:
        db.session.delete(receipt)

    # 5. 删除 ProjectMember
    members = ProjectMember.query.filter_by(header_id=project.id).all()
    deleted['members'] = len(members)
    for member in members:
        db.session.delete(member)

    # 6. 删除 REF
    deleted['refs'] = len(refs)
    for ref in refs:
        db.session.delete(ref)

    # 7. 删除 ProjectHeader
    db.session.delete(project)

    print(f"    删除关联数据: REF={deleted['refs']}, EO={deleted['eos']}, Invoice={deleted['invoices']}, Receipt={deleted['receipts']}")


def main():
    """主函数"""
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("       预付款迁移脚本")
        print("=" * 70)

        created_count = 0
        deleted_count = 0
        skipped_count = 0

        print("\n[1/2] 迁移预付款项目...")

        for hid in PREPAYMENT_PROJECTS:
            project = ProjectHeader.query.filter_by(hid=hid).first()

            if not project:
                print(f"\n  项目 {hid} 不存在，跳过")
                skipped_count += 1
                continue

            # 检查是否已迁移
            existing = SupplierPrepayment.query.filter(
                SupplierPrepayment.remarks.like(f'%{hid}%')
            ).first()

            if existing:
                print(f"\n  项目 {hid} 已迁移 ({existing.prepayment_number})，跳过")
                skipped_count += 1
                continue

            # 迁移项目为预付款
            prepayment = migrate_project_to_prepayment(project)
            if prepayment:
                created_count += 1

        print("\n[2/2] 删除已迁移的项目...")

        for hid in PREPAYMENT_PROJECTS:
            project = ProjectHeader.query.filter_by(hid=hid).first()

            if not project:
                continue

            print(f"\n  删除项目: {hid} - {project.desc}")
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
        print(f"  删除项目: {deleted_count} 个")
        print(f"  跳过: {skipped_count} 个")

        print(f"\n预付款列表: https://www.joyesc.com/projects/prepayment/")
        print(f"项目列表: https://www.joyesc.com/projects/list")


if __name__ == '__main__':
    main()
