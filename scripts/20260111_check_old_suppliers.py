# -*- coding: utf-8 -*-
"""
检查旧的 suppliers 表是否存在，获取映射关系
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import CustomerCompany
from sqlalchemy import text

app = create_app()

def check_old_suppliers():
    """检查旧的 suppliers 表"""
    with app.app_context():
        # 检查 suppliers 表是否存在
        try:
            result = db.session.execute(text("SELECT * FROM suppliers LIMIT 5"))
            rows = result.fetchall()
            columns = result.keys()

            print(f"\n{'='*80}")
            print("旧 suppliers 表存在，前5条记录：")
            print(f"{'='*80}")
            print(f"列名: {list(columns)}")
            for row in rows:
                print(dict(zip(columns, row)))

            # 获取所有供应商
            all_suppliers = db.session.execute(text("SELECT supplier_id, name FROM suppliers")).fetchall()
            print(f"\n{'='*80}")
            print(f"所有供应商 (共 {len(all_suppliers)} 条):")
            print(f"{'='*80}")
            for s in all_suppliers:
                old_id = s[0]
                name = s[1]
                # 在 customer_companies 中查找同名公司
                company = CustomerCompany.query.filter(
                    CustomerCompany.company_name.ilike(f'%{name}%')
                ).first()
                new_id = company.id if company else None
                match_status = f"-> {new_id} ({company.company_name})" if company else "无匹配"
                print(f"旧ID: {old_id}, 名称: {name} {match_status}")

        except Exception as e:
            print(f"suppliers 表不存在或查询失败: {e}")

            # 尝试用其他方式获取映射
            print("\n尝试从 customer_companies 中查找可能的供应商...")
            suppliers = CustomerCompany.query.filter(
                CustomerCompany.is_supplier == True
            ).all()
            print(f"找到 {len(suppliers)} 个供应商:")
            for s in suppliers:
                print(f"ID: {s.id}, 名称: {s.company_name}")

if __name__ == '__main__':
    check_old_suppliers()
