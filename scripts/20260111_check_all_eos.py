# -*- coding: utf-8 -*-
"""
检查所有有 cost_price 的 EO 及其供应商
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment

app = create_app()

def check_eos_with_suppliers():
    """检查有供应商的 EO"""
    with app.app_context():
        # 查找所有有 cost_price 的 REF 及其 EO
        refs = ProjectRef.query.filter(ProjectRef.cost_price > 0).all()

        print(f"\n{'='*80}")
        print(f"有成本价的 REF (共 {len(refs)} 条)")
        print(f"{'='*80}")

        for ref in refs[:20]:  # 只显示前20条
            supplier_name = ref.supplier.company_name if ref.supplier else 'N/A'
            print(f"\nREF ID: {ref.id}, 编号: {ref.ref_number}")
            print(f"  供应商: {supplier_name} (ID: {ref.supplier_id})")
            print(f"  成本价: {ref.cost_price}")

            # 检查该供应商是否有预付账款
            if ref.supplier_id:
                prepayments = SupplierPrepayment.query.filter(
                    SupplierPrepayment.supplier_id == ref.supplier_id,
                    SupplierPrepayment.status.in_(['confirmed', 'partial_used'])
                ).all()
                if prepayments:
                    print(f"  该供应商有 {len(prepayments)} 条预付账款")
                else:
                    print(f"  该供应商无预付账款")

            if ref.eos:
                eo = ref.eos
                print(f"  EO ID: {eo.id}, 编号: {eo.eo_number}, 状态: {eo.status}")
            else:
                print(f"  无 EO")

if __name__ == '__main__':
    check_eos_with_suppliers()
