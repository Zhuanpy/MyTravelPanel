# -*- coding: utf-8 -*-
"""
检查预付账款和使用记录状态
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment, PrepaymentUsage

app = create_app()

def check_prepayments():
    """检查所有预付账款记录"""
    with app.app_context():
        prepayments = SupplierPrepayment.query.all()
        print(f"\n{'='*80}")
        print(f"预付账款记录 (共 {len(prepayments)} 条)")
        print(f"{'='*80}")

        for p in prepayments:
            print(f"\nID: {p.id}")
            print(f"  编号: {p.prepayment_number}")
            print(f"  供应商: {p.supplier.company_name if p.supplier else 'N/A'} (ID: {p.supplier_id})")
            print(f"  原始金额: {p.amount}")
            print(f"  当前余额: {p.balance_amount}")
            print(f"  已使用金额: {p.used_amount}")
            print(f"  状态: {p.status} ({p.status_display})")

            # 检查关联的使用记录
            usages = PrepaymentUsage.query.filter_by(prepayment_id=p.id).all()
            if usages:
                print(f"  使用记录 ({len(usages)} 条):")
                for u in usages:
                    print(f"    - ID: {u.id}, 金额: {u.amount}, 状态: {u.status}, EO: {u.eo_id}, 描述: {u.description}")
            else:
                print(f"  使用记录: 无")

def check_usages():
    """检查所有使用记录"""
    with app.app_context():
        usages = PrepaymentUsage.query.all()
        print(f"\n{'='*80}")
        print(f"预付账款使用记录 (共 {len(usages)} 条)")
        print(f"{'='*80}")

        for u in usages:
            print(f"ID: {u.id} | 预付ID: {u.prepayment_id} | EO: {u.eo_id} | 金额: {u.amount} | 状态: {u.status} | {u.description}")

if __name__ == '__main__':
    check_prepayments()
    check_usages()
