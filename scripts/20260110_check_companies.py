# -*- coding: utf-8 -*-
"""检查公司数据"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # 查询所有公司
    result = db.session.execute(text("""
        SELECT id, company_name, status, created_at
        FROM customer_companies
        ORDER BY company_name
    """))

    print("所有公司列表:")
    print("-" * 80)
    for row in result:
        print(f"ID: {row[0]}, 名称: '{row[1]}', 状态: {row[2]}, 创建时间: {row[3]}")

    print("\n" + "-" * 80)
    print("检查 '个人' 或 'CA' 相关数据:")

    result2 = db.session.execute(text("""
        SELECT id, company_name, status
        FROM customer_companies
        WHERE company_name LIKE '%个人%' OR company_name LIKE '%CA%' OR company_name = 'CA'
    """))

    for row in result2:
        print(f"ID: {row[0]}, 名称: '{row[1]}', 状态: {row[2]}")
