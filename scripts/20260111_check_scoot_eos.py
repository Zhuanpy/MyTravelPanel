# -*- coding: utf-8 -*-
"""
检查 SCOOT AIRLINE 相关的 EO
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.ref import ProjectRef

app = create_app()

SCOOT_SUPPLIER_ID = 224

def check_scoot_eos():
    """检查 SCOOT AIRLINE 的 EO"""
    with app.app_context():
        # 查找 SCOOT 供应商的 REF
        refs = ProjectRef.query.filter_by(supplier_id=SCOOT_SUPPLIER_ID).all()
        print(f"\n{'='*80}")
        print(f"SCOOT AIRLINE (ID: {SCOOT_SUPPLIER_ID}) 的 REF 和 EO")
        print(f"{'='*80}")

        for ref in refs:
            print(f"\nREF ID: {ref.id}, 编号: {ref.ref_number}")
            print(f"  成本价: {ref.cost_price}")
            print(f"  状态: {ref.status}")

            if ref.eos:
                eo = ref.eos  # uselist=False, 所以直接是单个对象
                print(f"  EO ID: {eo.id}, 编号: {eo.eo_number}")
                print(f"  EO 状态: {eo.status}")
                print(f"  付款金额: {eo.pay_amount}")
                print(f"  付款日期: {eo.paid_date}")
            else:
                print(f"  无 EO")

if __name__ == '__main__':
    check_scoot_eos()
