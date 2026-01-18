"""
修复多项目合并收款的ref_id问题

问题描述：
CSV导入时，多项目合并收款被错误地设置了ref_id，
导致整笔金额被算作单个REF的收款，造成未付款显示负数。

检查条件：
1. 收款有 ref_id（被当作REF级别收款）
2. 同时有多条发票分配记录（实际是多项目收款）
3. 或者收款金额与对应REF售价不匹配

修复方案：
将这些收款的 ref_id 清除，改为项目级别收款，
让系统通过发票分配记录正确计算每个项目的收款。

使用方法：
python scripts/fix_multi_project_receipts.py          # 仅检查，不修复
python scripts/fix_multi_project_receipts.py --fix    # 检查并修复
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app, db
from sqlalchemy import text
from decimal import Decimal

def check_problematic_receipts():
    """检查有问题的收款记录"""

    # 查询：有ref_id且有多条发票分配的收款
    sql = text("""
        SELECT
            pr.id as receipt_id,
            pr.receipt_number,
            pr.amount as receipt_amount,
            pr.ref_id,
            pr.header_id as receipt_header_id,
            r.ref_number,
            r.selling_price as ref_selling_price,
            COUNT(ria.id) as allocation_count,
            SUM(ria.allocated_amount) as total_allocated,
            GROUP_CONCAT(DISTINCT pi.header_id) as allocated_to_projects
        FROM project_receipts pr
        JOIN project_refs r ON pr.ref_id = r.id
        LEFT JOIN receipt_invoice_allocations ria ON ria.receipt_id = pr.id
        WHERE pr.ref_id IS NOT NULL
          AND pr.status = 'confirmed'
        GROUP BY pr.id, pr.receipt_number, pr.amount, pr.ref_id,
                 pr.header_id, r.ref_number, r.selling_price
        HAVING COUNT(ria.id) > 1
           OR (COUNT(ria.id) = 1 AND SUM(ria.allocated_amount) != pr.amount)
           OR pr.amount != r.selling_price
        ORDER BY pr.id DESC
    """)

    result = db.session.execute(sql).fetchall()
    return result


def fix_receipt(receipt_id):
    """修复单条收款记录"""
    sql = text("UPDATE project_receipts SET ref_id = NULL WHERE id = :id")
    db.session.execute(sql, {'id': receipt_id})


def main():
    fix_mode = '--fix' in sys.argv

    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("检查多项目合并收款的ref_id问题")
        print("=" * 80)
        print()

        receipts = check_problematic_receipts()

        if not receipts:
            print("✓ 未发现有问题的收款记录")
            return

        print(f"发现 {len(receipts)} 条可能有问题的收款记录：")
        print()
        print("-" * 80)
        print(f"{'ID':<6} {'收款号':<10} {'收款金额':>12} {'REF号':<10} {'REF售价':>12} {'分配数':>6} {'分配总额':>12} {'分配项目'}")
        print("-" * 80)

        to_fix = []

        for r in receipts:
            receipt_id = r[0]
            receipt_number = r[1]
            receipt_amount = float(r[2] or 0)
            ref_id = r[3]
            receipt_header_id = r[4]
            ref_number = r[5]
            ref_selling_price = float(r[6] or 0)
            allocation_count = r[7]
            total_allocated = float(r[8] or 0)
            allocated_projects = r[9]

            # 判断是否需要修复
            needs_fix = False
            reason = ""

            # 条件1：有多条分配记录（多项目收款）
            if allocation_count > 1:
                needs_fix = True
                reason = f"多项目收款({allocation_count}条分配)"
            # 条件2：收款金额与REF售价不匹配
            elif abs(receipt_amount - ref_selling_price) > 0.01:
                needs_fix = True
                reason = f"金额不匹配(差额:{receipt_amount - ref_selling_price:.2f})"

            if needs_fix:
                to_fix.append((receipt_id, receipt_number, reason))
                marker = "** "
            else:
                marker = "   "

            print(f"{marker}{receipt_id:<6} {receipt_number:<10} {receipt_amount:>12.2f} {ref_number:<10} {ref_selling_price:>12.2f} {allocation_count:>6} {total_allocated:>12.2f} {allocated_projects}")

        print("-" * 80)
        print()
        print(f"需要修复: {len(to_fix)} 条 (标记 ** 的记录)")
        print()

        if to_fix:
            print("详细修复列表：")
            for receipt_id, receipt_number, reason in to_fix:
                print(f"  - 收款 {receipt_number} (ID:{receipt_id}): {reason}")
            print()

            if fix_mode:
                print("开始修复...")
                for receipt_id, receipt_number, reason in to_fix:
                    fix_receipt(receipt_id)
                    print(f"  ✓ 已修复收款 {receipt_number} (ID:{receipt_id})")

                db.session.commit()
                print()
                print(f"✓ 已修复 {len(to_fix)} 条收款记录")
            else:
                print("提示: 使用 --fix 参数执行修复")
                print("  python scripts/fix_multi_project_receipts.py --fix")


if __name__ == '__main__':
    main()
