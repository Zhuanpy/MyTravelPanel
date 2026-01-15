# -*- coding: utf-8 -*-
"""
合并 IndiGo 重复公司

保留: INDIGO AIRLINE SINGAPORE
合并: IndiGo in Singapore, INDIGO AIRLINE

运行方式: python scripts/merge_indigo_companies.py
确认执行: python scripts/merge_indigo_companies.py --confirm
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


# 保留的公司名称
KEEP_COMPANY = 'INDIGO AIRLINE SINGAPORE'

# 要合并的公司名称
MERGE_COMPANIES = [
    'IndiGo in Singapore',
    'INDIGO AIRLINE',
]


def merge_company(keep_company, merge_company, dry_run=True):
    """合并单个公司"""
    print(f"\n  合并: {merge_company.company_name} (ID: {merge_company.id})")

    stats = {
        'projects': 0,
        'refs': 0,
        'prepayments': 0,
        'payments': 0,
    }

    # 1. 更新 ProjectHeader 的 company_id
    projects = ProjectHeader.query.filter_by(company_id=merge_company.id).all()
    stats['projects'] = len(projects)
    for project in projects:
        print(f"    项目 {project.hid}: {project.desc}")
        if not dry_run:
            project.company_id = keep_company.id

    # 2. 更新 ProjectRef 的 supplier_id（供应商在REF上，不在EO上）
    refs = ProjectRef.query.filter_by(supplier_id=merge_company.id).all()
    stats['refs'] = len(refs)
    for ref in refs:
        print(f"    REF {ref.ref_number}: {ref.description}")
        if not dry_run:
            ref.supplier_id = keep_company.id

    # 3. 更新 SupplierPrepayment 的 supplier_id
    prepayments = SupplierPrepayment.query.filter_by(supplier_id=merge_company.id).all()
    stats['prepayments'] = len(prepayments)
    for prepayment in prepayments:
        print(f"    预付款 {prepayment.prepayment_number}: {prepayment.remarks}")
        if not dry_run:
            prepayment.supplier_id = keep_company.id

    # 4. 更新 SupplierPayment 的 supplier_id
    try:
        payments = SupplierPayment.query.filter_by(supplier_id=merge_company.id).all()
        stats['payments'] = len(payments)
        for payment in payments:
            print(f"    付款记录 ID: {payment.id}")
            if not dry_run:
                payment.supplier_id = keep_company.id
    except Exception as e:
        print(f"    SupplierPayment 查询失败: {e}")

    # 5. 删除被合并的公司
    if not dry_run:
        # 检查是否还有关联
        remaining = (
            ProjectHeader.query.filter_by(company_id=merge_company.id).count() +
            ProjectRef.query.filter_by(supplier_id=merge_company.id).count() +
            SupplierPrepayment.query.filter_by(supplier_id=merge_company.id).count()
        )
        if remaining == 0:
            print(f"    删除公司: {merge_company.company_name}")
            db.session.delete(merge_company)
        else:
            print(f"    警告: 仍有 {remaining} 条关联数据，无法删除")

    return stats


def main():
    parser = argparse.ArgumentParser(description='合并 IndiGo 重复公司')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    args = parser.parse_args()
    
    dry_run = not args.confirm
    
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("       合并 IndiGo 重复公司")
        print("=" * 70)
        
        if dry_run:
            print("\n  [预览模式 - 数据不会实际修改]")
        
        # 查找保留的公司
        keep_company = CustomerCompany.query.filter_by(company_name=KEEP_COMPANY).first()
        if not keep_company:
            print(f"\n错误: 找不到要保留的公司 '{KEEP_COMPANY}'")
            return
        
        print(f"\n保留公司: {keep_company.company_name} (ID: {keep_company.id})")
        
        total_stats = {
            'projects': 0,
            'refs': 0,
            'prepayments': 0,
            'payments': 0,
            'companies_merged': 0,
        }

        print("\n" + "-" * 70)
        print("合并公司:")
        print("-" * 70)

        for company_name in MERGE_COMPANIES:
            merge_company_obj = CustomerCompany.query.filter_by(company_name=company_name).first()
            if not merge_company_obj:
                print(f"\n  跳过: 找不到公司 '{company_name}'")
                continue

            if merge_company_obj.id == keep_company.id:
                print(f"\n  跳过: '{company_name}' 与保留公司相同")
                continue

            stats = merge_company(keep_company, merge_company_obj, dry_run)

            total_stats['projects'] += stats['projects']
            total_stats['refs'] += stats['refs']
            total_stats['prepayments'] += stats['prepayments']
            total_stats['payments'] += stats['payments']
            total_stats['companies_merged'] += 1
        
        # 提交或提示
        if not dry_run:
            try:
                db.session.commit()
                print("\n" + "=" * 70)
                print("  合并完成！数据已保存")
                print("=" * 70)
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return
        
        # 输出统计
        print("\n" + "-" * 70)
        print("统计:")
        print("-" * 70)
        print(f"  合并公司数: {total_stats['companies_merged']}")
        print(f"  更新项目: {total_stats['projects']} 条")
        print(f"  更新 REF: {total_stats['refs']} 条")
        print(f"  更新预付款: {total_stats['prepayments']} 条")
        print(f"  更新付款记录: {total_stats['payments']} 条")
        
        if dry_run:
            print(f"\n预览完成。确认合并请添加 --confirm 参数:")
            print(f"  python scripts/merge_indigo_companies.py --confirm")


if __name__ == '__main__':
    main()
