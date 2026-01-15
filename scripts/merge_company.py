# -*- coding: utf-8 -*-
"""
合并重复公司脚本

功能：
1. 将重复的公司合并为一个
2. 更新所有关联数据：EO供应商、预付款供应商、项目客户公司等

运行方式:
  python scripts/merge_company.py --keep "US-BANGLA AIRLINES LTD" --merge "US Bangla Airlines"
  python scripts/merge_company.py --keep-id 123 --merge-id 456
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment
from App_new.business.projects.models.supplier_payment import SupplierPayment


def find_company(name=None, company_id=None):
    """查找公司"""
    if company_id:
        return CustomerCompany.query.get(company_id)
    if name:
        return CustomerCompany.query.filter_by(company_name=name).first()
    return None


def merge_companies(keep_company, merge_company, dry_run=True):
    """合并公司"""
    print(f"\n{'='*70}")
    print(f"合并公司")
    print(f"{'='*70}")
    print(f"\n保留公司: {keep_company.company_name} (ID: {keep_company.id})")
    print(f"合并公司: {merge_company.company_name} (ID: {merge_company.id})")

    stats = {
        'projects': 0,
        'refs': 0,
        'eos': 0,
        'prepayments': 0,
        'payments': 0,
    }

    # 1. 更新 ProjectHeader 的 company_id
    print(f"\n[1/5] 更新项目客户公司...")
    projects = ProjectHeader.query.filter_by(company_id=merge_company.id).all()
    stats['projects'] = len(projects)
    for project in projects:
        print(f"  项目 {project.hid}: {merge_company.company_name} -> {keep_company.company_name}")
        if not dry_run:
            project.company_id = keep_company.id

    # 2. 更新 ProjectRef 的 supplier_id（如果有这个字段）
    print(f"\n[2/5] 更新 REF 供应商...")
    try:
        refs = ProjectRef.query.filter_by(supplier_id=merge_company.id).all()
        stats['refs'] = len(refs)
        for ref in refs:
            print(f"  REF {ref.ref_number}: {merge_company.company_name} -> {keep_company.company_name}")
            if not dry_run:
                ref.supplier_id = keep_company.id
    except Exception as e:
        print(f"  REF 没有 supplier_id 字段或查询失败: {e}")

    # 3. 更新 ProjectEO（通过 REF 关联的供应商）
    # EO 没有直接的 supplier_id，供应商信息可能在 REF 或其他地方
    print(f"\n[3/5] 检查 EO 供应商...")
    # EO 的供应商可能通过 payment_record 关联
    try:
        # 检查 SupplierPayment 表
        payments = SupplierPayment.query.filter_by(supplier_id=merge_company.id).all()
        stats['payments'] = len(payments)
        for payment in payments:
            print(f"  付款记录 {payment.id}: {merge_company.company_name} -> {keep_company.company_name}")
            if not dry_run:
                payment.supplier_id = keep_company.id
    except Exception as e:
        print(f"  SupplierPayment 查询失败: {e}")

    # 4. 更新 SupplierPrepayment 的 supplier_id
    print(f"\n[4/5] 更新预付款供应商...")
    prepayments = SupplierPrepayment.query.filter_by(supplier_id=merge_company.id).all()
    stats['prepayments'] = len(prepayments)
    for prepayment in prepayments:
        print(f"  预付款 {prepayment.prepayment_number}: {merge_company.company_name} -> {keep_company.company_name}")
        if not dry_run:
            prepayment.supplier_id = keep_company.id

    # 5. 删除被合并的公司
    print(f"\n[5/5] 删除被合并的公司...")
    if not dry_run:
        # 先检查是否还有其他关联
        remaining_projects = ProjectHeader.query.filter_by(company_id=merge_company.id).count()
        remaining_prepayments = SupplierPrepayment.query.filter_by(supplier_id=merge_company.id).count()

        if remaining_projects > 0 or remaining_prepayments > 0:
            print(f"  警告: 仍有关联数据，无法删除")
            print(f"    项目: {remaining_projects}")
            print(f"    预付款: {remaining_prepayments}")
        else:
            print(f"  删除公司: {merge_company.company_name}")
            db.session.delete(merge_company)
    else:
        print(f"  将删除: {merge_company.company_name}")

    # 输出统计
    print(f"\n{'='*70}")
    print(f"统计:")
    print(f"  项目: {stats['projects']} 条")
    print(f"  REF: {stats['refs']} 条")
    print(f"  预付款: {stats['prepayments']} 条")
    print(f"  付款记录: {stats['payments']} 条")

    return stats


def main():
    parser = argparse.ArgumentParser(description='合并重复公司')
    parser.add_argument('--keep', type=str, help='保留的公司名称')
    parser.add_argument('--keep-id', type=int, help='保留的公司ID')
    parser.add_argument('--merge', type=str, help='要合并(删除)的公司名称')
    parser.add_argument('--merge-id', type=int, help='要合并(删除)的公司ID')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    args = parser.parse_args()

    if not (args.keep or args.keep_id):
        print("错误: 请指定要保留的公司 (--keep 或 --keep-id)")
        return

    if not (args.merge or args.merge_id):
        print("错误: 请指定要合并的公司 (--merge 或 --merge-id)")
        return

    app = create_app()

    with app.app_context():
        # 查找公司
        keep_company = find_company(name=args.keep, company_id=args.keep_id)
        merge_company = find_company(name=args.merge, company_id=args.merge_id)

        if not keep_company:
            print(f"错误: 找不到要保留的公司")
            return

        if not merge_company:
            print(f"错误: 找不到要合并的公司")
            return

        if keep_company.id == merge_company.id:
            print(f"错误: 两个公司相同")
            return

        dry_run = not args.confirm

        if dry_run:
            print("\n" + "="*70)
            print("  预览模式 - 数据不会实际修改")
            print("="*70)

        merge_companies(keep_company, merge_company, dry_run=dry_run)

        if not dry_run:
            try:
                db.session.commit()
                print(f"\n合并完成！数据已保存")
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(f"\n预览完成。确认合并请添加 --confirm 参数:")
            keep_param = f'--keep "{args.keep}"' if args.keep else f'--keep-id {args.keep_id}'
            merge_param = f'--merge "{args.merge}"' if args.merge else f'--merge-id {args.merge_id}'
            print(f'  python scripts/merge_company.py {keep_param} {merge_param} --confirm')


if __name__ == '__main__':
    main()
