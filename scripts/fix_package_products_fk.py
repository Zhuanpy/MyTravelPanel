# -*- coding: utf-8 -*-
"""
修复产品表的 supplier_id 外键约束

问题：数据库外键指向 suppliers 表，但应该指向 customer_companies 表
修复：删除旧约束，添加新约束

涉及表：package_products, products_unified

运行方式: python scripts/fix_package_products_fk.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db


def fix_table_fk(table_name):
    """修复指定表的 supplier_id 外键"""
    print(f"\n{'=' * 60}")
    print(f"  修复 {table_name}.supplier_id 外键约束")
    print("=" * 60)

    # 1. 查看当前外键约束
    print(f"\n[1/3] 查看 {table_name} 当前外键约束...")
    result = db.session.execute(db.text(f"""
        SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = '{table_name}'
        AND COLUMN_NAME = 'supplier_id'
        AND REFERENCED_TABLE_NAME IS NOT NULL
    """))
    constraints = list(result)

    if constraints:
        for row in constraints:
            print(f"  约束名: {row[0]}")
            print(f"  引用表: {row[1]}.{row[2]}")
    else:
        print("  没有找到外键约束")

    # 2. 删除旧约束
    print(f"\n[2/3] 删除 {table_name} 旧外键约束...")
    for row in constraints:
        constraint_name = row[0]
        try:
            db.session.execute(db.text(f"""
                ALTER TABLE `{table_name}`
                DROP FOREIGN KEY `{constraint_name}`
            """))
            print(f"  已删除约束: {constraint_name}")
        except Exception as e:
            print(f"  删除约束失败: {e}")

    db.session.commit()

    # 3. 添加新约束（指向 customer_companies）
    print(f"\n[3/3] 添加 {table_name} 新外键约束...")
    constraint_name = f"fk_{table_name}_supplier"
    try:
        db.session.execute(db.text(f"""
            ALTER TABLE `{table_name}`
            ADD CONSTRAINT `{constraint_name}`
            FOREIGN KEY (supplier_id) REFERENCES customer_companies(id)
            ON DELETE SET NULL ON UPDATE CASCADE
        """))
        db.session.commit()
        print(f"  已添加新约束: {constraint_name} -> customer_companies(id)")
    except Exception as e:
        print(f"  添加约束失败: {e}")
        db.session.rollback()

    # 验证
    print(f"\n验证 {table_name} 修改...")
    result = db.session.execute(db.text(f"""
        SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = '{table_name}'
        AND COLUMN_NAME = 'supplier_id'
        AND REFERENCED_TABLE_NAME IS NOT NULL
    """))
    for row in result:
        print(f"  约束名: {row[0]}")
        print(f"  引用表: {row[1]}.{row[2]}")


def main():
    app = create_app()

    with app.app_context():
        # 修复 package_products 表
        fix_table_fk('package_products')

        # 修复 products_unified 表
        fix_table_fk('products_unified')

        print("\n" + "=" * 60)
        print("  所有表修复完成！")
        print("=" * 60)


if __name__ == '__main__':
    main()
