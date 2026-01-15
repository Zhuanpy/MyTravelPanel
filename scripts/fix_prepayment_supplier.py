# -*- coding: utf-8 -*-
"""
修复预付款供应商错误

问题：部分预付款迁移时供应商设置错误
修复：根据 remarks 中的关键字匹配正确的供应商

运行方式: python scripts/fix_prepayment_supplier.py
确认执行: python scripts/fix_prepayment_supplier.py --confirm
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import CustomerCompany
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment


# 供应商关键字映射
SUPPLIER_KEYWORDS = {
    'SCOOT': 'SCOOT AIRLINE',
    'IndiGo': 'INDIGO AIRLINE SINGAPORE',
    'Indigo': 'INDIGO AIRLINE SINGAPORE',
    'INDIGO': 'INDIGO AIRLINE SINGAPORE',
    'US BANGLA': 'US-BANGLA AIRLINES LTD',
    'US-BANGLA': 'US-BANGLA AIRLINES LTD',
    'AIR INDIA EXPRESS': 'AIR INDIA EXPRESS',
}


def main():
    parser = argparse.ArgumentParser(description='修复预付款供应商错误')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    args = parser.parse_args()

    dry_run = not args.confirm

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("       修复预付款供应商错误")
        print("=" * 70)

        if dry_run:
            print("\n  [预览模式 - 数据不会实际修改]")

        # 缓存供应商
        suppliers = {}
        for keyword, supplier_name in SUPPLIER_KEYWORDS.items():
            if supplier_name not in suppliers:
                supplier = CustomerCompany.query.filter_by(company_name=supplier_name).first()
                if supplier:
                    suppliers[supplier_name] = supplier
                    print(f"\n供应商: {supplier_name} (ID: {supplier.id})")
                else:
                    print(f"\n警告: 找不到供应商 '{supplier_name}'")

        # 查找所有迁移的预付款
        prepayments = SupplierPrepayment.query.filter(
            SupplierPrepayment.remarks.like('%从项目迁移%')
        ).all()

        print(f"\n找到 {len(prepayments)} 条迁移的预付款")
        print("\n" + "-" * 70)
        print("检查供应商:")
        print("-" * 70)

        fixed_count = 0
        for prepayment in prepayments:
            remarks = prepayment.remarks or ''
            current_supplier = prepayment.supplier

            # 根据 remarks 确定正确的供应商
            correct_supplier = None
            matched_keyword = None
            for keyword, supplier_name in SUPPLIER_KEYWORDS.items():
                if keyword.upper() in remarks.upper():
                    if supplier_name in suppliers:
                        correct_supplier = suppliers[supplier_name]
                        matched_keyword = keyword
                        break

            if not correct_supplier:
                continue

            # 检查是否需要修复
            if current_supplier and current_supplier.id == correct_supplier.id:
                continue

            # 需要修复
            current_name = current_supplier.company_name if current_supplier else '无'
            print(f"\n  {prepayment.prepayment_number}:")
            print(f"    备注: {remarks[:60]}...")
            print(f"    当前供应商: {current_name}")
            print(f"    正确供应商: {correct_supplier.company_name}")

            if not dry_run:
                prepayment.supplier_id = correct_supplier.id

            fixed_count += 1

        print("\n" + "-" * 70)
        print(f"需要修复: {fixed_count} 条")

        if not dry_run and fixed_count > 0:
            try:
                db.session.commit()
                print("\n" + "=" * 70)
                print("  修复完成！数据已保存")
                print("=" * 70)
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return

        if dry_run and fixed_count > 0:
            print(f"\n预览完成。确认修复请添加 --confirm 参数:")
            print(f"  python scripts/fix_prepayment_supplier.py --confirm")


if __name__ == '__main__':
    main()
