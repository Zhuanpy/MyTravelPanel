"""
合并供应商：将 ZHANG ZHUAN UOB VISA 合并到 ZHANG ZHUAN UOB- 8317
将旧供应商关联的所有REF转移到目标供应商，然后删除旧记录

运行方式: python scripts/20260123_rename_supplier.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()


def merge_supplier():
    """合并供应商记录"""
    from App_new.business.projects.models.project import CustomerCompany
    from App_new.business.projects.models.ref import ProjectRef

    with app.app_context():
        old_name = 'ZHANG ZHUAN UOB VISA'
        target_name = 'ZHANG ZHUAN UOB- 8317'

        old_supplier = CustomerCompany.query.filter_by(company_name=old_name).first()
        target_supplier = CustomerCompany.query.filter_by(company_name=target_name).first()

        if not old_supplier:
            print(f"未找到旧供应商: {old_name}")
            return

        if not target_supplier:
            print(f"未找到目标供应商: {target_name}，将直接重命名")
            old_supplier.company_name = target_name
            db.session.commit()
            print(f"重命名成功！{old_name} → {target_name}")
            return

        print(f"旧供应商: ID={old_supplier.id}, 名称={old_supplier.company_name}")
        print(f"目标供应商: ID={target_supplier.id}, 名称={target_supplier.company_name}")

        # 查找旧供应商关联的REF
        refs = ProjectRef.query.filter_by(supplier_id=old_supplier.id).all()
        print(f"旧供应商关联的REF数量: {len(refs)}")
        for ref in refs:
            print(f"  REF ID={ref.id}, ref_number={ref.ref_number}, header_id={ref.header_id}")

        confirm = input(f"\n确认将 {len(refs)} 条REF从 [{old_name}] 转移到 [{target_name}]，并删除旧供应商？(y/n): ")
        if confirm.lower() != 'y':
            print("已取消。")
            return

        # 转移REF关联
        for ref in refs:
            ref.supplier_id = target_supplier.id

        # 删除旧供应商
        db.session.delete(old_supplier)
        db.session.commit()

        print(f"\n合并完成！")
        print(f"  转移REF: {len(refs)} 条")
        print(f"  已删除供应商: {old_name} (ID={old_supplier.id})")
        print(f"  保留供应商: {target_name} (ID={target_supplier.id})")


if __name__ == '__main__':
    merge_supplier()
