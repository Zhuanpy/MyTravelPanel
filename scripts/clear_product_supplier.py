# -*- coding: utf-8 -*-
"""
清空产品表的供应商关联

问题：表合并后 supplier_id 指向错误的公司
修复：清空所有产品的 supplier_id，手动重新选择

涉及表：package_products, products_unified

运行方式: python scripts/clear_product_supplier.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db


def clear_table_supplier(table_name):
    """清空指定表的 supplier_id"""
    print(f"\n--- 清空 {table_name} 表 ---")

    # 统计当前有供应商关联的产品数量
    result = db.session.execute(db.text(
        f"SELECT COUNT(*) FROM {table_name} WHERE supplier_id IS NOT NULL"
    ))
    count = result.scalar()
    print(f"当前有供应商关联的记录数量: {count}")

    if count == 0:
        print("没有需要清理的数据")
        return 0

    # 清空所有产品的 supplier_id
    result = db.session.execute(db.text(
        f"UPDATE {table_name} SET supplier_id = NULL"
    ))
    db.session.commit()

    print(f"已清空 {result.rowcount} 条记录的供应商关联")
    return result.rowcount


def main():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("  清空产品表的供应商关联")
        print("=" * 60)

        total = 0
        total += clear_table_supplier('package_products')
        total += clear_table_supplier('products_unified')

        print("\n" + "=" * 60)
        print(f"  完成！共清空 {total} 条记录")
        print("  请在产品编辑页面重新选择正确的供应商")
        print("=" * 60)


if __name__ == '__main__':
    main()
