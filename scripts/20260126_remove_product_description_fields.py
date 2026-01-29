# -*- coding: utf-8 -*-
"""
删除产品表中的 short_description 和 highlights 字段
保留 description / product_description 字段作为唯一描述字段

涉及表：
- products_unified: 删除 short_description 和 highlights
- package_products: 删除 highlights

执行前：先将 highlights 内容合并到 description/product_description
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

def column_exists(conn, table_name, column_name):
    """检查列是否存在"""
    result = conn.execute(db.text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = DATABASE()
        AND table_name = :table_name
        AND column_name = :column_name
    """), {'table_name': table_name, 'column_name': column_name})
    return result.scalar() > 0


def migrate():
    with app.app_context():
        conn = db.engine.connect()

        try:
            # ========== products_unified 表 ==========
            print("=" * 50)
            print("处理 products_unified 表...")
            print("=" * 50)

            # 先检查 highlights 列是否存在
            if column_exists(conn, 'products_unified', 'highlights'):
                # 1. 先将 highlights 内容合并到 description（如果 description 为空）
                print("合并 highlights 到 description...")
                conn.execute(db.text("""
                    UPDATE products_unified
                    SET description = CONCAT_WS('\n\n', highlights, description)
                    WHERE highlights IS NOT NULL AND highlights != ''
                      AND (description IS NULL OR description = '')
                """))

                # 2. 如果两者都有内容，将 highlights 添加到 description 开头
                conn.execute(db.text("""
                    UPDATE products_unified
                    SET description = CONCAT_WS('\n\n', highlights, description)
                    WHERE highlights IS NOT NULL AND highlights != ''
                      AND description IS NOT NULL AND description != ''
                      AND description NOT LIKE CONCAT(highlights, '%')
                """))

                conn.commit()
                print("products_unified 数据合并完成")

                # 删除 highlights 列
                print("删除 products_unified.highlights 列...")
                conn.execute(db.text("ALTER TABLE products_unified DROP COLUMN highlights"))
                conn.commit()
                print("highlights 列已删除")
            else:
                print("products_unified.highlights 列不存在，跳过数据合并和删除")

            # 检查并删除 short_description 列
            if column_exists(conn, 'products_unified', 'short_description'):
                print("删除 products_unified.short_description 列...")
                conn.execute(db.text("ALTER TABLE products_unified DROP COLUMN short_description"))
                conn.commit()
                print("short_description 列已删除")
            else:
                print("products_unified.short_description 列不存在，跳过")

            # ========== package_products 表（旅游产品） ==========
            print("\n" + "=" * 50)
            print("处理 package_products 表（旅游产品）...")
            print("=" * 50)

            # 先检查 highlights 列是否存在
            if column_exists(conn, 'package_products', 'highlights'):
                # 1. 先将 highlights 内容合并到 product_description
                print("合并 highlights 到 product_description...")
                conn.execute(db.text("""
                    UPDATE package_products
                    SET product_description = CONCAT_WS('\n\n', highlights, product_description)
                    WHERE highlights IS NOT NULL AND highlights != ''
                      AND (product_description IS NULL OR product_description = '')
                """))

                # 2. 如果两者都有内容，将 highlights 添加到 product_description 开头
                conn.execute(db.text("""
                    UPDATE package_products
                    SET product_description = CONCAT_WS('\n\n', highlights, product_description)
                    WHERE highlights IS NOT NULL AND highlights != ''
                      AND product_description IS NOT NULL AND product_description != ''
                      AND product_description NOT LIKE CONCAT(highlights, '%')
                """))

                conn.commit()
                print("package_products 数据合并完成")

                # 删除 highlights 列
                print("删除 package_products.highlights 列...")
                conn.execute(db.text("ALTER TABLE package_products DROP COLUMN highlights"))
                conn.commit()
                print("highlights 列已删除")
            else:
                print("package_products.highlights 列不存在，跳过数据合并和删除")

            print("\n" + "=" * 50)
            print("迁移完成！")
            print("=" * 50)

        except Exception as e:
            print(f"迁移失败: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

if __name__ == '__main__':
    migrate()
