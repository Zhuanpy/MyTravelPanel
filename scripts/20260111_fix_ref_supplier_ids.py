# -*- coding: utf-8 -*-
"""
修复 REF 表的 supplier_id 映射
使用 supplier_company_mapping 表将旧的 supplier_id 更新为新的 company_id
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
            result = db.session.execute(text("SELECT * FROM supplier_company_mapping"))
            rows = result.fetchall()
            print(f"\n{'='*80}")
            print(f"supplier_company_mapping 映射表 (共 {len(rows)} 条)")
            print(f"{'='*80}")
            for row in rows:
                print(f"旧 supplier_id: {row[0]} -> 新 company_id: {row[1]}")
            return True
        except Exception as e:
            print(f"映射表不存在: {e}")
            return False

def fix_ref_supplier_ids():
    """修复 REF 的 supplier_id"""
    with app.app_context():
        conn = db.engine.connect()
        trans = conn.begin()

        try:
            # 先检查有多少 REF 需要修复
            result = conn.execute(text("""
                SELECT COUNT(*) FROM project_refs r
                LEFT JOIN customer_companies c ON r.supplier_id = c.id
                WHERE r.supplier_id IS NOT NULL AND c.id IS NULL
            """))
            invalid_count = result.fetchone()[0]
            print(f"\n需要修复的 REF 数量: {invalid_count}")

            if invalid_count == 0:
                print("没有需要修复的记录")
                return

            # 显示将要修复的记录
            print(f"\n{'='*80}")
            print("将要修复的 REF 记录:")
            print(f"{'='*80}")

            refs_to_fix = conn.execute(text("""
                SELECT r.id, r.ref_number, r.supplier_id, m.company_id, c.company_name
                FROM project_refs r
                LEFT JOIN customer_companies cc ON r.supplier_id = cc.id
                LEFT JOIN supplier_company_mapping m ON r.supplier_id = m.supplier_id
                LEFT JOIN customer_companies c ON m.company_id = c.id
                WHERE r.supplier_id IS NOT NULL AND cc.id IS NULL
                ORDER BY r.supplier_id
                LIMIT 50
            """)).fetchall()

            for ref in refs_to_fix:
                ref_id, ref_number, old_id, new_id, company_name = ref
                if new_id:
                    print(f"REF {ref_id} ({ref_number}): {old_id} -> {new_id} ({company_name})")
                else:
                    print(f"REF {ref_id} ({ref_number}): {old_id} -> 无映射!")

            # 执行修复
            print(f"\n{'='*80}")
            print("执行修复...")
            print(f"{'='*80}")

            result = conn.execute(text("""
                UPDATE project_refs r
                INNER JOIN supplier_company_mapping m ON r.supplier_id = m.supplier_id
                SET r.supplier_id = m.company_id
                WHERE EXISTS (
                    SELECT 1 FROM supplier_company_mapping m2
                    WHERE r.supplier_id = m2.supplier_id
                )
            """))
            print(f"更新了 {result.rowcount} 条 REF 记录")

            # 检查剩余无法修复的记录
            remaining = conn.execute(text("""
                SELECT r.id, r.ref_number, r.supplier_id
                FROM project_refs r
                LEFT JOIN customer_companies c ON r.supplier_id = c.id
                WHERE r.supplier_id IS NOT NULL AND c.id IS NULL
                LIMIT 20
            """)).fetchall()

            if remaining:
                print(f"\n警告: 仍有 {len(remaining)} 条 REF 无法修复（无映射记录）:")
                for r in remaining:
                    print(f"  REF {r[0]} ({r[1]}): supplier_id={r[2]}")

            trans.commit()
            print("\n修复完成！")

        except Exception as e:
            trans.rollback()
            print(f"\n修复失败，已回滚: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

def verify_fix():
    """验证修复结果"""
    with app.app_context():
        # 检查 SCOOT 相关
        result = db.session.execute(text("""
            SELECT r.id, r.ref_number, r.supplier_id, c.company_name
            FROM project_refs r
            INNER JOIN customer_companies c ON r.supplier_id = c.id
            WHERE c.company_name LIKE '%SCOOT%'
            LIMIT 10
        """)).fetchall()

        print(f"\n{'='*80}")
        print("SCOOT AIRLINE 的 REF 记录:")
        print(f"{'='*80}")
        if result:
            for r in result:
                print(f"REF {r[0]} ({r[1]}): supplier_id={r[2]}, 公司={r[3]}")
        else:
            print("无记录")

        # 统计
        stats = db.session.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END) as valid,
                SUM(CASE WHEN r.supplier_id IS NOT NULL AND c.id IS NULL THEN 1 ELSE 0 END) as invalid
            FROM project_refs r
            LEFT JOIN customer_companies c ON r.supplier_id = c.id
        """)).fetchone()

        print(f"\nREF supplier_id 统计:")
        print(f"  总数: {stats[0]}")
        print(f"  有效: {stats[1]}")
        print(f"  无效: {stats[2]}")

if __name__ == '__main__':
    print("REF supplier_id 修复工具")
    print("=" * 60)

    # 检查映射表
    if check_mapping_table():
        # 执行修复
        fix_ref_supplier_ids()
        # 验证结果
        verify_fix()
    else:
        print("\n无法执行修复：映射表不存在")
