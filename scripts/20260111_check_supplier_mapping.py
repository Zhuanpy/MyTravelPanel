# -*- coding: utf-8 -*-
"""
检查供应商 ID 映射情况
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.project import CustomerCompany
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment

app = create_app()

def check_supplier_mapping():
    """检查供应商映射"""
    with app.app_context():
        # 查看预付账款的供应商
        prepayments = SupplierPrepayment.query.all()
        print(f"\n{'='*80}")
        print("预付账款的供应商:")
        print(f"{'='*80}")
        for p in prepayments:
            company = CustomerCompany.query.get(p.supplier_id) if p.supplier_id else None
            print(f"预付 {p.prepayment_number}: supplier_id={p.supplier_id}, 公司名={company.company_name if company else 'N/A'}")

        # 查看 REF 中使用的供应商 ID
        print(f"\n{'='*80}")
        print("REF 使用的 supplier_id 统计:")
        print(f"{'='*80}")

        from sqlalchemy import func
        supplier_stats = db.session.query(
            ProjectRef.supplier_id,
            func.count(ProjectRef.id).label('count')
        ).group_by(ProjectRef.supplier_id).all()

        for supplier_id, count in supplier_stats[:30]:
            if supplier_id:
                company = CustomerCompany.query.get(supplier_id)
                company_name = company.company_name if company else f"(ID {supplier_id} 不存在)"
            else:
                company_name = "无供应商"
            print(f"supplier_id={supplier_id}: {count} 条 REF - {company_name}")

        # 专门查找 SCOOT 相关
        print(f"\n{'='*80}")
        print("查找 SCOOT 相关公司:")
        print(f"{'='*80}")
        scoot_companies = CustomerCompany.query.filter(
            CustomerCompany.company_name.ilike('%scoot%')
        ).all()
        for c in scoot_companies:
            print(f"ID: {c.id}, 名称: {c.company_name}, is_supplier: {c.is_supplier}")

            # 检查是否有 REF 使用这个 supplier_id
            ref_count = ProjectRef.query.filter_by(supplier_id=c.id).count()
            print(f"  REF 数量: {ref_count}")

if __name__ == '__main__':
    check_supplier_mapping()
