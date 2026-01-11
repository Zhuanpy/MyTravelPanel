# -*- coding: utf-8 -*-
"""
数据库迁移脚本：合并客户公司和供应商表
将 suppliers 表数据迁移到 customer_companies 表

执行方式: python scripts/20260111_merge_company_tables.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text
from datetime import datetime


def run_migration():
    """执行迁移"""
    app = create_app()

    with app.app_context():
        conn = db.engine.connect()
        trans = conn.begin()

        try:
            print("=" * 60)
            print("开始合并客户公司和供应商表")
            print("=" * 60)

            # 步骤1：添加新字段到 customer_companies 表
            print("\n[步骤1] 添加新字段到 customer_companies 表...")

            new_columns = [
                ("is_customer", "BIT DEFAULT 1 NOT NULL"),
                ("is_supplier", "BIT DEFAULT 0 NOT NULL"),
                ("supplier_type_id", "INT NULL"),
                ("country", "NVARCHAR(50) NULL"),
                ("city", "NVARCHAR(50) NULL"),
                ("region", "NVARCHAR(50) NULL"),
            ]

            for col_name, col_def in new_columns:
                try:
                    conn.execute(text(f"ALTER TABLE customer_companies ADD {col_name} {col_def}"))
                    print(f"  + 添加字段: {col_name}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower() or "Column names" in str(e):
                        print(f"  - 字段已存在: {col_name}")
                    else:
                        print(f"  ! 添加字段失败 {col_name}: {e}")

            # 步骤2：更新现有客户公司记录
            print("\n[步骤2] 更新现有客户公司记录...")
            result = conn.execute(text("""
                UPDATE customer_companies
                SET is_customer = 1, is_supplier = 0
                WHERE is_customer IS NULL OR is_supplier IS NULL
            """))
            print(f"  更新了 {result.rowcount} 条记录")

            # 步骤3：创建映射表
            print("\n[步骤3] 创建 supplier_id → company_id 映射表...")
            try:
                conn.execute(text("""
                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'supplier_company_mapping')
                    CREATE TABLE supplier_company_mapping (
                        supplier_id INT PRIMARY KEY,
                        company_id INT NOT NULL,
                        migrated_at DATETIME DEFAULT GETDATE()
                    )
                """))
                print("  + 映射表创建成功")
            except Exception as e:
                print(f"  - 映射表可能已存在: {e}")

            # 步骤4：迁移供应商数据
            print("\n[步骤4] 迁移供应商数据...")

            # 获取所有供应商
            suppliers = conn.execute(text("""
                SELECT supplier_id, name, supplier_type_id, contact_person, phone, email,
                       address, country, city, region, status, created_at, notes, click_count
                FROM suppliers
            """)).fetchall()

            print(f"  找到 {len(suppliers)} 个供应商")

            merged_count = 0
            created_count = 0

            for supplier in suppliers:
                supplier_id = supplier[0]
                supplier_name = supplier[1].strip().upper() if supplier[1] else ''

                # 检查是否存在同名公司（大小写不敏感）
                existing = conn.execute(text("""
                    SELECT id FROM customer_companies
                    WHERE UPPER(company_name) = :name
                """), {"name": supplier_name}).fetchone()

                if existing:
                    # 合并：更新现有公司，添加供应商标识
                    company_id = existing[0]
                    conn.execute(text("""
                        UPDATE customer_companies
                        SET is_supplier = 1,
                            supplier_type_id = COALESCE(supplier_type_id, :supplier_type_id),
                            country = COALESCE(country, :country),
                            city = COALESCE(city, :city),
                            region = COALESCE(region, :region)
                        WHERE id = :company_id
                    """), {
                        "company_id": company_id,
                        "supplier_type_id": supplier[2],
                        "country": supplier[7],
                        "city": supplier[8],
                        "region": supplier[9]
                    })
                    merged_count += 1
                    print(f"    合并: {supplier_name} → ID {company_id}")
                else:
                    # 新建：创建新的公司记录
                    result = conn.execute(text("""
                        INSERT INTO customer_companies
                        (company_name, contact_person, contact_phone, contact_email, address,
                         status, remarks, click_count, created_at, is_customer, is_supplier,
                         supplier_type_id, country, city, region)
                        OUTPUT INSERTED.id
                        VALUES
                        (:name, :contact_person, :phone, :email, :address,
                         :status, :notes, :click_count, :created_at, 0, 1,
                         :supplier_type_id, :country, :city, :region)
                    """), {
                        "name": supplier_name if supplier_name else f"Supplier_{supplier_id}",
                        "contact_person": supplier[3],
                        "phone": supplier[4],
                        "email": supplier[5],
                        "address": supplier[6],
                        "status": 'active' if supplier[10] == 'active' else 'inactive',
                        "notes": supplier[12],
                        "click_count": supplier[13] or 0,
                        "created_at": supplier[11] or datetime.utcnow(),
                        "supplier_type_id": supplier[2],
                        "country": supplier[7],
                        "city": supplier[8],
                        "region": supplier[9]
                    })
                    company_id = result.fetchone()[0]
                    created_count += 1
                    print(f"    新建: {supplier_name} → ID {company_id}")

                # 记录映射关系
                try:
                    conn.execute(text("""
                        INSERT INTO supplier_company_mapping (supplier_id, company_id)
                        VALUES (:supplier_id, :company_id)
                    """), {"supplier_id": supplier_id, "company_id": company_id})
                except:
                    # 可能已存在
                    conn.execute(text("""
                        UPDATE supplier_company_mapping
                        SET company_id = :company_id
                        WHERE supplier_id = :supplier_id
                    """), {"supplier_id": supplier_id, "company_id": company_id})

            print(f"\n  迁移完成: 合并 {merged_count} 条, 新建 {created_count} 条")

            # 步骤5：更新外键引用
            print("\n[步骤5] 更新外键引用...")

            # 5.1 更新 project_refs 表
            print("  更新 project_refs.supplier_id...")
            try:
                # 先添加 company_id 列（如果不存在）
                try:
                    conn.execute(text("ALTER TABLE project_refs ADD company_id INT NULL"))
                    print("    + 添加 project_refs.company_id 列")
                except:
                    pass

                result = conn.execute(text("""
                    UPDATE r SET r.company_id = m.company_id
                    FROM project_refs r
                    INNER JOIN supplier_company_mapping m ON r.supplier_id = m.supplier_id
                    WHERE r.company_id IS NULL
                """))
                print(f"    更新了 {result.rowcount} 条 project_refs 记录")
            except Exception as e:
                print(f"    ! 更新失败: {e}")

            # 5.2 更新 supplier_prepayments 表
            print("  更新 supplier_prepayments.supplier_id...")
            try:
                try:
                    conn.execute(text("ALTER TABLE supplier_prepayments ADD company_id INT NULL"))
                    print("    + 添加 supplier_prepayments.company_id 列")
                except:
                    pass

                result = conn.execute(text("""
                    UPDATE p SET p.company_id = m.company_id
                    FROM supplier_prepayments p
                    INNER JOIN supplier_company_mapping m ON p.supplier_id = m.supplier_id
                    WHERE p.company_id IS NULL
                """))
                print(f"    更新了 {result.rowcount} 条 supplier_prepayments 记录")
            except Exception as e:
                print(f"    ! 更新失败: {e}")

            # 5.3 更新 supplier_statements 表
            print("  更新 supplier_statements.supplier_id...")
            try:
                try:
                    conn.execute(text("ALTER TABLE supplier_statements ADD company_id INT NULL"))
                    print("    + 添加 supplier_statements.company_id 列")
                except:
                    pass

                result = conn.execute(text("""
                    UPDATE s SET s.company_id = m.company_id
                    FROM supplier_statements s
                    INNER JOIN supplier_company_mapping m ON s.supplier_id = m.supplier_id
                    WHERE s.company_id IS NULL
                """))
                print(f"    更新了 {result.rowcount} 条 supplier_statements 记录")
            except Exception as e:
                print(f"    ! 更新失败: {e}")

            # 5.4 更新 accounts 表
            print("  更新 accounts.supplier_id...")
            try:
                try:
                    conn.execute(text("ALTER TABLE accounts ADD company_id INT NULL"))
                    print("    + 添加 accounts.company_id 列")
                except:
                    pass

                result = conn.execute(text("""
                    UPDATE a SET a.company_id = m.company_id
                    FROM accounts a
                    INNER JOIN supplier_company_mapping m ON a.supplier_id = m.supplier_id
                    WHERE a.company_id IS NULL
                """))
                print(f"    更新了 {result.rowcount} 条 accounts 记录")
            except Exception as e:
                print(f"    ! 更新失败: {e}")

            trans.commit()
            print("\n" + "=" * 60)
            print("迁移完成！")
            print("=" * 60)
            print("\n注意事项:")
            print("1. suppliers 表数据已保留，可用于验证")
            print("2. 新增了 supplier_company_mapping 映射表")
            print("3. 相关模型文件的外键引用需要手动更新")
            print("4. 请运行应用测试功能是否正常")

        except Exception as e:
            trans.rollback()
            print(f"\n迁移失败，已回滚: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()

        return True


def show_statistics():
    """显示迁移后的统计信息"""
    app = create_app()

    with app.app_context():
        conn = db.engine.connect()

        print("\n" + "=" * 60)
        print("迁移统计")
        print("=" * 60)

        # 公司统计
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_customer = 1 AND is_supplier = 0 THEN 1 ELSE 0 END) as customers_only,
                SUM(CASE WHEN is_customer = 0 AND is_supplier = 1 THEN 1 ELSE 0 END) as suppliers_only,
                SUM(CASE WHEN is_customer = 1 AND is_supplier = 1 THEN 1 ELSE 0 END) as both
            FROM customer_companies
        """)).fetchone()

        print(f"\n公司总数: {result[0]}")
        print(f"  - 仅客户: {result[1]}")
        print(f"  - 仅供应商: {result[2]}")
        print(f"  - 客户+供应商: {result[3]}")

        # 映射表统计
        try:
            mapping_count = conn.execute(text(
                "SELECT COUNT(*) FROM supplier_company_mapping"
            )).fetchone()[0]
            print(f"\n映射记录: {mapping_count}")
        except:
            pass

        conn.close()


if __name__ == '__main__':
    if run_migration():
        show_statistics()
