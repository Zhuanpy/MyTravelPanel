# -*- coding: utf-8 -*-
"""清理重复/错误的公司数据"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # 先检查这些公司是否有关联的项目
        result = db.session.execute(text("""
            SELECT id, company_id FROM project_headers
            WHERE company_id IN (196, 204)
        """))
        projects = result.fetchall()

        if projects:
            print(f"警告: 有 {len(projects)} 个项目关联到这些公司，将公司ID设为NULL")
            db.session.execute(text("""
                UPDATE project_headers SET company_id = NULL
                WHERE company_id IN (196, 204)
            """))

        # 删除公司记录
        print("删除 ID=196 (个人) ...")
        db.session.execute(text("DELETE FROM customer_companies WHERE id = 196"))

        print("删除 ID=204 (CA) ...")
        db.session.execute(text("DELETE FROM customer_companies WHERE id = 204"))

        db.session.commit()
        print("清理完成！")

    except Exception as e:
        db.session.rollback()
        print(f"清理失败: {e}")
