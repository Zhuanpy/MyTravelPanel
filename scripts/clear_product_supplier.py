# -*- coding: utf-8 -*-
"""
清空旅游产品的供应商关联

问题：表合并后 supplier_id 指向错误的公司
修复：清空所有产品的 supplier_id，手动重新选择

运行方式: python scripts/clear_product_supplier.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db


def main():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("  清空旅游产品的供应商关联")
        print("=" * 60)

        # 统计当前有供应商关联的产品数量
        result = db.session.execute(db.text(
            "SELECT COUNT(*) FROM package_products WHERE supplier_id IS NOT NULL"
        ))
        count = result.scalar()
        print(f"\n当前有供应商关联的产品数量: {count}")

        if count == 0:
            print("\n没有需要清理的数据")
            return

        # 清空所有产品的 supplier_id
        result = db.session.execute(db.text(
            "UPDATE package_products SET supplier_id = NULL"
        ))
        db.session.commit()

        print(f"已清空 {result.rowcount} 条产品的供应商关联")

        print("\n" + "=" * 60)
        print("  完成！请在产品编辑页面重新选择正确的供应商")
        print("=" * 60)


if __name__ == '__main__':
    main()
