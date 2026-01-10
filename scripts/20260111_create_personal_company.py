# -*- coding: utf-8 -*-
"""
创建"个人"客户公司记录
用于机票订单等场景下的默认客户公司
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import CustomerCompany

app = create_app()

with app.app_context():
    # 检查是否已存在
    existing = CustomerCompany.query.filter(
        (CustomerCompany.company_code == 'PERSONAL') |
        (CustomerCompany.company_name == '个人')
    ).first()

    if existing:
        print(f'已存在"个人"客户公司记录:')
        print(f'  ID: {existing.id}')
        print(f'  名称: {existing.company_name}')
        print(f'  代码: {existing.company_code}')
    else:
        # 创建新记录
        personal_company = CustomerCompany(
            company_name='个人',
            company_code='PERSONAL',
            contact_person='系统',
            status='active',
            created_by='系统'
        )
        db.session.add(personal_company)
        db.session.commit()
        print(f'成功创建"个人"客户公司记录:')
        print(f'  ID: {personal_company.id}')
        print(f'  名称: {personal_company.company_name}')
        print(f'  代码: {personal_company.company_code}')
