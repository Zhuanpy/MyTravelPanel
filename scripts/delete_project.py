# -*- coding: utf-8 -*-
"""
删除项目脚本

删除指定项目及其所有关联数据（REF、EO、Invoice、Receipt等）

运行方式:
  python scripts/delete_project.py --hid H899
  python scripts/delete_project.py --id 165
"""

import sys
import os
import argparse

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.project_member import ProjectMember


def delete_project(project):
    """删除项目及其所有关联数据"""
    print(f"\n删除项目: {project.hid} - {project.desc}")
    print("=" * 60)

    # 获取所有 REF
    refs = ProjectRef.query.filter_by(header_id=project.id).all()
    ref_ids = [ref.id for ref in refs]

    # 统计
    stats = {
        'refs': len(refs),
        'eos': 0,
        'invoices': 0,
        'invoice_items': 0,
        'receipts': 0,
        'members': 0,
    }

    # 1. 删除 EO
    if ref_ids:
        eos = ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).all()
        stats['eos'] = len(eos)
        for eo in eos:
            db.session.delete(eo)
        print(f"  删除 EO: {stats['eos']} 条")

    # 2. 删除 InvoiceItem
    if ref_ids:
        invoice_items = InvoiceItem.query.filter(InvoiceItem.ref_id.in_(ref_ids)).all()
        stats['invoice_items'] = len(invoice_items)
        for item in invoice_items:
            db.session.delete(item)
        print(f"  删除 InvoiceItem: {stats['invoice_items']} 条")

    # 3. 删除 Invoice
    invoices = ProjectInvoice.query.filter_by(header_id=project.id).all()
    stats['invoices'] = len(invoices)
    for invoice in invoices:
        # 先删除该 Invoice 下的所有 InvoiceItem
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        db.session.delete(invoice)
    print(f"  删除 Invoice: {stats['invoices']} 条")

    # 4. 删除 Receipt
    receipts = ProjectReceipt.query.filter_by(header_id=project.id).all()
    stats['receipts'] = len(receipts)
    for receipt in receipts:
        db.session.delete(receipt)
    print(f"  删除 Receipt: {stats['receipts']} 条")

    # 5. 删除 ProjectMember
    members = ProjectMember.query.filter_by(header_id=project.id).all()
    stats['members'] = len(members)
    for member in members:
        db.session.delete(member)
    print(f"  删除 Member: {stats['members']} 条")

    # 6. 删除 REF
    for ref in refs:
        db.session.delete(ref)
    print(f"  删除 REF: {stats['refs']} 条")

    # 7. 删除 ProjectHeader
    db.session.delete(project)
    print(f"  删除 ProjectHeader: 1 条")

    return stats


def main():
    parser = argparse.ArgumentParser(description='删除项目及其关联数据')
    parser.add_argument('--hid', type=str, help='项目编号 (如 H899)')
    parser.add_argument('--id', type=int, help='项目ID (如 165)')
    parser.add_argument('--confirm', action='store_true', help='确认删除（不加此参数只预览）')
    args = parser.parse_args()

    if not args.hid and not args.id:
        print("错误: 请指定 --hid 或 --id 参数")
        print("示例: python scripts/delete_project.py --hid H899")
        return

    app = create_app()

    with app.app_context():
        # 查找项目
        if args.hid:
            project = ProjectHeader.query.filter_by(hid=args.hid).first()
        else:
            project = ProjectHeader.query.get(args.id)

        if not project:
            print(f"错误: 找不到项目 {args.hid or args.id}")
            return

        # 显示项目信息
        print("\n" + "=" * 60)
        print("项目信息:")
        print("=" * 60)
        print(f"  ID: {project.id}")
        print(f"  HID: {project.hid}")
        print(f"  描述: {project.desc}")
        print(f"  公司: {project.company.company_name if project.company else '-'}")
        print(f"  状态: {project.status}")
        print(f"  创建时间: {project.created_at}")

        # 统计关联数据
        refs = ProjectRef.query.filter_by(header_id=project.id).all()
        ref_ids = [ref.id for ref in refs]

        print("\n关联数据统计:")
        print(f"  REF: {len(refs)} 条")
        if ref_ids:
            eo_count = ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).count()
            print(f"  EO: {eo_count} 条")
            invoice_item_count = InvoiceItem.query.filter(InvoiceItem.ref_id.in_(ref_ids)).count()
            print(f"  InvoiceItem: {invoice_item_count} 条")
        invoice_count = ProjectInvoice.query.filter_by(header_id=project.id).count()
        print(f"  Invoice: {invoice_count} 条")
        receipt_count = ProjectReceipt.query.filter_by(header_id=project.id).count()
        print(f"  Receipt: {receipt_count} 条")
        member_count = ProjectMember.query.filter_by(header_id=project.id).count()
        print(f"  Member: {member_count} 条")

        if not args.confirm:
            print("\n" + "=" * 60)
            print("预览模式 - 数据未删除")
            print("确认删除请添加 --confirm 参数:")
            print(f"  python scripts/delete_project.py --hid {project.hid} --confirm")
            return

        # 确认删除
        print("\n" + "=" * 60)
        print("开始删除...")

        try:
            stats = delete_project(project)
            db.session.commit()
            print("\n删除成功!")
        except Exception as e:
            db.session.rollback()
            print(f"\n删除失败: {str(e)}")
            return

        print("\n" + "=" * 60)
        print("删除完成")


if __name__ == '__main__':
    main()
