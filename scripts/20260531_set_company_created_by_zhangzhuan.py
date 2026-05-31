# -*- coding: utf-8 -*-
"""
数据脚本：把客户公司的创建人(created_by)统一设置为 'STAFF ZHANG ZHUAN'。

运行方式:
  python scripts/20260531_set_company_created_by_zhangzhuan.py          # 执行(写库)
  python scripts/20260531_set_company_created_by_zhangzhuan.py --dry    # 预览(不写库)
提示：若控制台报 UnicodeEncodeError，先执行 $env:PYTHONIOENCODING='utf-8'
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from App_new import create_app
from App_new.exts import db

CREATED_BY = 'STAFF ZHANG ZHUAN'

app = create_app()

with app.app_context():
    from App_new.business.projects.models.project import CustomerCompany

    dry = '--dry' in sys.argv[1:]

    total = CustomerCompany.query.count()
    # 只更新与目标值不同的记录
    to_update = CustomerCompany.query.filter(
        db.or_(
            CustomerCompany.created_by.is_(None),
            CustomerCompany.created_by != CREATED_BY
        )
    ).all()

    print(f"客户公司总数: {total}")
    print(f"将更新创建人的记录数: {len(to_update)}  ->  '{CREATED_BY}'")

    if dry:
        print("\n[预览模式] 未写库。去掉 --dry 执行更新。")
    else:
        for c in to_update:
            c.created_by = CREATED_BY
        db.session.commit()
        print(f"\n完成：已将 {len(to_update)} 个客户公司的创建人统一设为 '{CREATED_BY}'。")
