"""
修改供应商名称
ZHANG ZHUAN UOB VISA → ZHANG ZHUAN UOB- 8317

运行方式: python scripts/20260123_rename_supplier.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()


def rename_supplier():
    """修改供应商名称"""
    from App_new.business.projects.models.project import CustomerCompany

    with app.app_context():
        old_name = 'ZHANG ZHUAN UOB VISA'
        new_name = 'ZHANG ZHUAN UOB- 8317'

        supplier = CustomerCompany.query.filter_by(company_name=old_name).first()
        if not supplier:
            print(f"未找到供应商: {old_name}")
            # 尝试模糊搜索
            similar = CustomerCompany.query.filter(
                CustomerCompany.company_name.ilike('%ZHANG ZHUAN UOB%')
            ).all()
            if similar:
                print("相似的供应商:")
                for s in similar:
                    print(f"  ID={s.id}, 名称={s.company_name}")
            return

        print(f"找到供应商: ID={supplier.id}, 当前名称={supplier.company_name}")
        print(f"将修改为: {new_name}")

        confirm = input("确认修改？(y/n): ")
        if confirm.lower() != 'y':
            print("已取消。")
            return

        supplier.company_name = new_name
        db.session.commit()
        print(f"修改成功！{old_name} → {new_name}")


if __name__ == '__main__':
    rename_supplier()
