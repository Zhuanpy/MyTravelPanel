# -*- coding: utf-8 -*-
"""
修复 package_products 表的 supplier_id 外键约束

问题：数据库外键指向 suppliers 表，但应该指向 customer_companies 表
修复：删除旧约束，添加新约束

运行方式: python scripts/fix_package_products_fk.py
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
        print("  修复 package_products.supplier_id 外键约束")
        print("=" * 60)

        # 1. 查看当前外键约束
        print("\n[1/3] 查看当前外键约束...")
        result = db.session.execute(db.text("""
            SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'package_products'
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
        print("\n[2/3] 删除旧外键约束...")
        for row in constraints:
            constraint_name = row[0]
            try:
                db.session.execute(db.text(f"""
                    ALTER TABLE package_products
                    DROP FOREIGN KEY `{constraint_name}`
                """))
                print(f"  已删除约束: {constraint_name}")
            except Exception as e:
                print(f"  删除约束失败: {e}")

        db.session.commit()

        # 3. 添加新约束（指向 customer_companies）
        print("\n[3/3] 添加新外键约束...")
        try:
            db.session.execute(db.text("""
                ALTER TABLE package_products
                ADD CONSTRAINT fk_package_products_supplier
                FOREIGN KEY (supplier_id) REFERENCES customer_companies(id)
                ON DELETE SET NULL ON UPDATE CASCADE
            """))
            db.session.commit()
            print("  已添加新约束: fk_package_products_supplier -> customer_companies(id)")
        except Exception as e:
            print(f"  添加约束失败: {e}")
            db.session.rollback()

        # 验证
        print("\n验证修改...")
        result = db.session.execute(db.text("""
            SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'package_products'
            AND COLUMN_NAME = 'supplier_id'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """))
        for row in result:
            print(f"  约束名: {row[0]}")
            print(f"  引用表: {row[1]}.{row[2]}")

        print("\n" + "=" * 60)
        print("  修复完成！")
        print("=" * 60)


if __name__ == '__main__':
    main()
