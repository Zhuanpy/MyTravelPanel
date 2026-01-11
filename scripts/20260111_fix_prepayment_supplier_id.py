# -*- coding: utf-8 -*-
"""
修复预付账款表中的 supplier_id 映射
将旧的 supplier_id 更新为 customer_companies 表中对应的公司ID
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment
from App_new.business.projects.models.project import CustomerCompany

app = create_app()

def fix_prepayment_supplier_ids():
    """修复预付账款的 supplier_id"""
    with app.app_context():
        # 获取所有预付记录
        prepayments = SupplierPrepayment.query.all()
        print(f"找到 {len(prepayments)} 条预付记录")

        for p in prepayments:
            print(f"\n预付记录 ID: {p.id}, 编号: {p.prepayment_number}")
            print(f"  当前 supplier_id: {p.supplier_id}")

            # 检查当前 supplier_id 是否能找到公司
            if p.supplier_id:
                company = CustomerCompany.query.get(p.supplier_id)
                if company:
                    print(f"  对应公司: {company.company_name} (ID: {company.id})")
                else:
                    print(f"  警告: supplier_id {p.supplier_id} 在 customer_companies 表中不存在!")

                    # 尝试通过公司名称查找
                    # 需要手动指定映射关系
                    print("  请手动检查并更新此记录")

def show_all_prepayments():
    """显示所有预付记录及其供应商信息"""
    with app.app_context():
        prepayments = SupplierPrepayment.query.all()
        print("\n" + "=" * 80)
        print("所有预付记录:")
        print("=" * 80)

        for p in prepayments:
            company_name = "未知"
            if p.supplier:
                company_name = p.supplier.company_name
            elif p.supplier_id:
                company = CustomerCompany.query.get(p.supplier_id)
                if company:
                    company_name = company.company_name
                else:
                    company_name = f"ID {p.supplier_id} 不存在"

            print(f"ID: {p.id} | 编号: {p.prepayment_number} | supplier_id: {p.supplier_id} | 公司: {company_name} | 金额: {p.amount} | 状态: {p.status}")

def find_company_by_name(name):
    """通过名称查找公司"""
    with app.app_context():
        companies = CustomerCompany.query.filter(
            CustomerCompany.company_name.ilike(f'%{name}%')
        ).all()

        print(f"\n搜索 '{name}' 的结果:")
        for c in companies:
            print(f"  ID: {c.id} | 名称: {c.company_name} | is_supplier: {c.is_supplier}")

def update_supplier_id(prepayment_id, new_supplier_id):
    """更新预付记录的 supplier_id"""
    with app.app_context():
        p = SupplierPrepayment.query.get(prepayment_id)
        if not p:
            print(f"预付记录 {prepayment_id} 不存在")
            return

        old_id = p.supplier_id
        p.supplier_id = new_supplier_id
        db.session.commit()
        print(f"已更新预付记录 {prepayment_id} 的 supplier_id: {old_id} -> {new_supplier_id}")

if __name__ == '__main__':
    print("预付账款 supplier_id 检查工具")
    print("=" * 60)

    # 显示所有预付记录
    show_all_prepayments()

    # 检查 SCOOT
    print("\n" + "=" * 60)
    find_company_by_name("SCOOT")

    # 修复：将 supplier_id 20 更新为 224 (SCOOT AIRLINE)
    print("\n" + "=" * 60)
    print("执行修复...")
    update_supplier_id(prepayment_id=1, new_supplier_id=224)
    update_supplier_id(prepayment_id=2, new_supplier_id=224)

    # 验证修复结果
    print("\n修复后的预付记录:")
    show_all_prepayments()
