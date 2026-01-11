# -*- coding: utf-8 -*-
"""
验证供应商数据迁移是否成功
执行方式: python scripts/20260111_verify_migration.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def verify_migration():
    """验证迁移结果"""
    app = create_app()

    with app.app_context():
        conn = db.engine.connect()

        print("=" * 70)
        print("供应商数据迁移验证报告")
        print("=" * 70)

        all_passed = True

        # 1. 检查供应商数量
        print("\n[1] 供应商数量对比")
        print("-" * 50)

        supplier_count = conn.execute(text("SELECT COUNT(*) FROM suppliers")).fetchone()[0]
        mapping_count = conn.execute(text("SELECT COUNT(*) FROM supplier_company_mapping")).fetchone()[0]

        print(f"  suppliers 表记录数: {supplier_count}")
        print(f"  mapping 表记录数:   {mapping_count}")

        if supplier_count == mapping_count:
            print("  ✓ 数量一致")
        else:
            print(f"  ✗ 数量不一致！缺少 {supplier_count - mapping_count} 条映射")
            all_passed = False

        # 2. 检查是否有未映射的供应商
        print("\n[2] 检查未映射的供应商")
        print("-" * 50)

        unmapped = conn.execute(text("""
            SELECT s.supplier_id, s.name
            FROM suppliers s
            LEFT JOIN supplier_company_mapping m ON s.supplier_id = m.supplier_id
            WHERE m.supplier_id IS NULL
            LIMIT 10
        """)).fetchall()

        if not unmapped:
            print("  ✓ 所有供应商都已映射")
        else:
            print(f"  ✗ 发现 {len(unmapped)} 个未映射的供应商:")
            for s in unmapped:
                print(f"    - ID {s[0]}: {s[1]}")
            all_passed = False

        # 3. 检查 customer_companies 中的供应商
        print("\n[3] 检查 customer_companies 表中的供应商数据")
        print("-" * 50)

        supplier_companies = conn.execute(text("""
            SELECT COUNT(*) FROM customer_companies WHERE is_supplier = 1
        """)).fetchone()[0]

        print(f"  标记为供应商的公司数: {supplier_companies}")

        both_roles = conn.execute(text("""
            SELECT COUNT(*) FROM customer_companies
            WHERE is_supplier = 1 AND is_customer = 1
        """)).fetchone()[0]

        print(f"  同时为客户和供应商的: {both_roles}")

        # 4. 检查外键引用更新情况
        print("\n[4] 检查外键引用更新情况")
        print("-" * 50)

        # project_refs
        try:
            refs_total = conn.execute(text(
                "SELECT COUNT(*) FROM project_refs WHERE supplier_id IS NOT NULL"
            )).fetchone()[0]
            refs_updated = conn.execute(text(
                "SELECT COUNT(*) FROM project_refs WHERE supplier_id IS NOT NULL AND company_id IS NOT NULL"
            )).fetchone()[0]
            refs_pending = refs_total - refs_updated

            print(f"  project_refs:")
            print(f"    - 有supplier_id的记录: {refs_total}")
            print(f"    - 已更新company_id:    {refs_updated}")
            if refs_pending > 0:
                print(f"    ✗ 待更新: {refs_pending}")
                all_passed = False
            else:
                print(f"    ✓ 全部更新完成")
        except Exception as e:
            print(f"  project_refs: 检查失败 - {e}")

        # supplier_prepayments
        try:
            prep_total = conn.execute(text(
                "SELECT COUNT(*) FROM supplier_prepayments WHERE supplier_id IS NOT NULL"
            )).fetchone()[0]
            prep_updated = conn.execute(text(
                "SELECT COUNT(*) FROM supplier_prepayments WHERE supplier_id IS NOT NULL AND company_id IS NOT NULL"
            )).fetchone()[0]
            prep_pending = prep_total - prep_updated

            print(f"  supplier_prepayments:")
            print(f"    - 有supplier_id的记录: {prep_total}")
            print(f"    - 已更新company_id:    {prep_updated}")
            if prep_pending > 0:
                print(f"    ✗ 待更新: {prep_pending}")
                all_passed = False
            else:
                print(f"    ✓ 全部更新完成")
        except Exception as e:
            print(f"  supplier_prepayments: 检查失败 - {e}")

        # 5. 抽样对比数据
        print("\n[5] 抽样数据对比（前5条）")
        print("-" * 50)

        samples = conn.execute(text("""
            SELECT
                s.supplier_id,
                s.name as supplier_name,
                c.id as company_id,
                c.company_name,
                c.is_supplier,
                c.supplier_type_id
            FROM suppliers s
            INNER JOIN supplier_company_mapping m ON s.supplier_id = m.supplier_id
            INNER JOIN customer_companies c ON m.company_id = c.id
            LIMIT 5
        """)).fetchall()

        print(f"  {'供应商ID':<10} {'供应商名称':<20} {'公司ID':<10} {'公司名称':<20} {'is_supplier'}")
        print(f"  {'-'*10} {'-'*20} {'-'*10} {'-'*20} {'-'*11}")
        for row in samples:
            print(f"  {row[0]:<10} {row[1][:18]:<20} {row[2]:<10} {row[3][:18]:<20} {row[4]}")

        # 6. 总结
        print("\n" + "=" * 70)
        if all_passed:
            print("验证结果: ✓ 全部通过")
            print("\n可以安全删除 suppliers 表，但建议：")
            print("1. 先备份 suppliers 表")
            print("2. 保留 supplier_company_mapping 映射表")
            print("3. 确认应用功能正常后再删除")
        else:
            print("验证结果: ✗ 存在问题，请先修复")
        print("=" * 70)

        conn.close()
        return all_passed


if __name__ == '__main__':
    verify_migration()
