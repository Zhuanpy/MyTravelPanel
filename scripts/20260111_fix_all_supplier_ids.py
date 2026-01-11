# -*- coding: utf-8 -*-
"""
修复所有表中的 supplier_id 映射
将旧的 supplier_id 通过 supplier_company_mapping 更新为 customer_companies 表中的公司ID

执行方式: python scripts/20260111_fix_all_supplier_ids.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()


def check_mapping_table():
    """检查映射表是否存在"""
    with app.app_context():
        try:
            result = db.session.execute(text("SELECT COUNT(*) FROM supplier_company_mapping"))
            count = result.fetchone()[0]
            print(f"映射表存在，共 {count} 条映射记录")
            return count > 0
        except Exception as e:
            print(f"映射表不存在或无法访问: {e}")
            return False


def show_mapping():
    """显示映射关系"""
    with app.app_context():
        result = db.session.execute(text("""
            SELECT m.supplier_id, m.company_id, c.company_name
            FROM supplier_company_mapping m
            LEFT JOIN customer_companies c ON m.company_id = c.id
            ORDER BY m.supplier_id
        """))
        rows = result.fetchall()

        print("\n" + "=" * 80)
        print("供应商ID映射关系:")
        print("=" * 80)
        print(f"{'旧supplier_id':<15} {'新company_id':<15} {'公司名称'}")
        print("-" * 80)
        for row in rows:
            print(f"{row[0]:<15} {row[1]:<15} {row[2] or 'N/A'}")
        return rows


def fix_prepayments():
    """修复预付账款表的 supplier_id"""
    with app.app_context():
        print("\n" + "=" * 80)
        print("[1] 修复 supplier_prepayments 表")
        print("=" * 80)

        # 查找需要修复的记录
        result = db.session.execute(text("""
            SELECT p.id, p.prepayment_number, p.supplier_id, m.company_id, c.company_name
            FROM supplier_prepayments p
            LEFT JOIN customer_companies cc ON p.supplier_id = cc.id
            LEFT JOIN supplier_company_mapping m ON p.supplier_id = m.supplier_id
            LEFT JOIN customer_companies c ON m.company_id = c.id
            WHERE cc.id IS NULL AND p.supplier_id IS NOT NULL
        """))
        rows = result.fetchall()

        if not rows:
            print("  没有需要修复的预付账款记录")
            # 显示当前状态
            result = db.session.execute(text("""
                SELECT p.id, p.prepayment_number, p.supplier_id, c.company_name
                FROM supplier_prepayments p
                LEFT JOIN customer_companies c ON p.supplier_id = c.id
            """))
            current = result.fetchall()
            print(f"\n  当前预付账款记录 ({len(current)} 条):")
            for r in current:
                print(f"    ID: {r[0]} | 编号: {r[1]} | supplier_id: {r[2]} | 公司: {r[3] or '未关联'}")
            return

        print(f"  找到 {len(rows)} 条需要修复的记录:")
        for row in rows:
            if row[3]:  # 有映射
                print(f"    预付ID: {row[0]} ({row[1]}): {row[2]} -> {row[3]} ({row[4]})")
            else:
                print(f"    预付ID: {row[0]} ({row[1]}): {row[2]} -> 无映射!")

        # 执行修复
        result = db.session.execute(text("""
            UPDATE supplier_prepayments p
            INNER JOIN supplier_company_mapping m ON p.supplier_id = m.supplier_id
            SET p.supplier_id = m.company_id
            WHERE EXISTS (
                SELECT 1 FROM supplier_company_mapping m2
                WHERE p.supplier_id = m2.supplier_id
            )
            AND NOT EXISTS (
                SELECT 1 FROM customer_companies c
                WHERE p.supplier_id = c.id
            )
        """))
        db.session.commit()
        print(f"\n  已更新 {result.rowcount} 条预付账款记录")


def fix_refs():
    """修复REF表的 supplier_id"""
    with app.app_context():
        print("\n" + "=" * 80)
        print("[2] 修复 project_refs 表")
        print("=" * 80)

        # 查找需要修复的记录
        result = db.session.execute(text("""
            SELECT COUNT(*) FROM project_refs r
            LEFT JOIN customer_companies c ON r.supplier_id = c.id
            WHERE r.supplier_id IS NOT NULL AND c.id IS NULL
        """))
        count = result.fetchone()[0]

        if count == 0:
            print("  没有需要修复的REF记录")
            return

        print(f"  找到 {count} 条需要修复的记录")

        # 执行修复
        result = db.session.execute(text("""
            UPDATE project_refs r
            INNER JOIN supplier_company_mapping m ON r.supplier_id = m.supplier_id
            SET r.supplier_id = m.company_id
            WHERE EXISTS (
                SELECT 1 FROM supplier_company_mapping m2
                WHERE r.supplier_id = m2.supplier_id
            )
            AND NOT EXISTS (
                SELECT 1 FROM customer_companies c
                WHERE r.supplier_id = c.id
            )
        """))
        db.session.commit()
        print(f"  已更新 {result.rowcount} 条REF记录")


def fix_eos():
    """修复EO表的 supplier_id（如果有的话）"""
    with app.app_context():
        print("\n" + "=" * 80)
        print("[3] 检查 project_eos 表")
        print("=" * 80)

        # 检查EO表是否有 supplier_id 字段
        try:
            result = db.session.execute(text("SHOW COLUMNS FROM project_eos LIKE 'supplier_id'"))
            if result.fetchone():
                print("  EO表有 supplier_id 字段，检查是否需要修复...")
                # 这里添加修复逻辑
            else:
                print("  EO表没有 supplier_id 字段，跳过")
        except Exception as e:
            print(f"  检查失败: {e}")


def fix_prepayment_usages():
    """修复预付使用记录表"""
    with app.app_context():
        print("\n" + "=" * 80)
        print("[4] 检查 prepayment_usages 表")
        print("=" * 80)

        # 显示当前状态
        result = db.session.execute(text("""
            SELECT u.id, u.prepayment_id, p.prepayment_number, u.eo_id, u.amount, u.status
            FROM prepayment_usages u
            LEFT JOIN supplier_prepayments p ON u.prepayment_id = p.id
            ORDER BY u.id DESC
            LIMIT 20
        """))
        rows = result.fetchall()

        if rows:
            print(f"  最近 {len(rows)} 条使用记录:")
            for r in rows:
                print(f"    使用ID: {r[0]} | 预付: {r[2]} | EO: {r[3]} | 金额: {r[4]} | 状态: {r[5]}")
        else:
            print("  暂无使用记录")


def verify_results():
    """验证修复结果"""
    with app.app_context():
        print("\n" + "=" * 80)
        print("验证修复结果")
        print("=" * 80)

        # 检查预付账款
        result = db.session.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END) as valid,
                SUM(CASE WHEN p.supplier_id IS NOT NULL AND c.id IS NULL THEN 1 ELSE 0 END) as invalid
            FROM supplier_prepayments p
            LEFT JOIN customer_companies c ON p.supplier_id = c.id
        """))
        stats = result.fetchone()
        print(f"\n  预付账款 supplier_id 状态:")
        print(f"    总数: {stats[0]}")
        print(f"    有效: {stats[1]}")
        print(f"    无效: {stats[2]}")

        # 检查REF
        result = db.session.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END) as valid,
                SUM(CASE WHEN r.supplier_id IS NOT NULL AND c.id IS NULL THEN 1 ELSE 0 END) as invalid
            FROM project_refs r
            LEFT JOIN customer_companies c ON r.supplier_id = c.id
        """))
        stats = result.fetchone()
        print(f"\n  REF supplier_id 状态:")
        print(f"    总数: {stats[0]}")
        print(f"    有效: {stats[1]}")
        print(f"    无效: {stats[2]}")

        # 显示预付账款详情
        print("\n" + "-" * 80)
        print("预付账款详情:")
        result = db.session.execute(text("""
            SELECT p.id, p.prepayment_number, p.supplier_id, c.company_name,
                   p.amount, p.balance_amount, p.status
            FROM supplier_prepayments p
            LEFT JOIN customer_companies c ON p.supplier_id = c.id
            ORDER BY p.id
        """))
        rows = result.fetchall()
        for r in rows:
            status_icon = "[OK]" if r[3] else "[X]"
            print(f"  {status_icon} ID: {r[0]} | {r[1]} | supplier_id: {r[2]} | company: {r[3] or 'N/A'} | amount: {r[4]} | balance: {r[5]} | status: {r[6]}")


def main():
    print("=" * 80)
    print("供应商ID全面修复工具")
    print("=" * 80)

    # 检查映射表
    if not check_mapping_table():
        print("\n警告: 映射表不存在或为空，请先运行迁移脚本创建映射表")
        print("运行: python scripts/20260111_merge_company_tables.py")
        return

    # 显示映射关系
    show_mapping()

    # 修复各表
    fix_prepayments()
    fix_refs()
    fix_eos()
    fix_prepayment_usages()

    # 验证结果
    verify_results()

    print("\n" + "=" * 80)
    print("修复完成！请刷新页面验证")
    print("=" * 80)


if __name__ == '__main__':
    main()
