"""
检查和修复无效的收款分配记录

问题类型：
1. 收款金额为0但有分配记录
2. 分配金额为负数
3. 分配总额超过收款金额

使用方法：
python scripts/fix_invalid_receipt_allocations.py          # 仅检查
python scripts/fix_invalid_receipt_allocations.py --fix    # 检查并修复
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app, db
from sqlalchemy import text


def check_zero_amount_with_allocation():
    """检查收款金额为0但有分配记录的情况"""
    sql = text("""
        SELECT
            pr.id as receipt_id,
            pr.receipt_number,
            pr.amount as receipt_amount,
            pr.header_id,
            COUNT(ria.id) as alloc_count,
            SUM(ria.allocated_amount) as total_allocated
        FROM project_receipts pr
        JOIN receipt_invoice_allocations ria ON ria.receipt_id = pr.id
        WHERE pr.amount = 0 AND pr.status = 'confirmed'
        GROUP BY pr.id, pr.receipt_number, pr.amount, pr.header_id
        HAVING COUNT(ria.id) > 0
    """)
    return db.session.execute(sql).fetchall()


def check_negative_allocations():
    """检查分配金额为负数的情况"""
    sql = text("""
        SELECT
            ria.id as alloc_id,
            ria.receipt_id,
            ria.invoice_id,
            ria.allocated_amount,
            pr.receipt_number,
            pr.amount as receipt_amount,
            pi.invoice_number,
            pi.header_id
        FROM receipt_invoice_allocations ria
        JOIN project_receipts pr ON ria.receipt_id = pr.id
        JOIN project_invoices pi ON ria.invoice_id = pi.id
        WHERE ria.allocated_amount < 0
    """)
    return db.session.execute(sql).fetchall()


def check_over_allocated():
    """检查分配总额超过收款金额的情况"""
    sql = text("""
        SELECT
            pr.id as receipt_id,
            pr.receipt_number,
            pr.amount as receipt_amount,
            pr.header_id,
            SUM(ria.allocated_amount) as total_allocated,
            SUM(ria.allocated_amount) - pr.amount as over_amount
        FROM project_receipts pr
        JOIN receipt_invoice_allocations ria ON ria.receipt_id = pr.id
        WHERE pr.status = 'confirmed'
        GROUP BY pr.id, pr.receipt_number, pr.amount, pr.header_id
        HAVING SUM(ria.allocated_amount) > pr.amount + 0.01
    """)
    return db.session.execute(sql).fetchall()


def check_under_allocated():
    """检查分配总额少于收款金额的情况（分配不完整）"""
    sql = text("""
        SELECT
            pr.id as receipt_id,
            pr.receipt_number,
            pr.amount as receipt_amount,
            pr.header_id,
            SUM(ria.allocated_amount) as total_allocated,
            pr.amount - SUM(ria.allocated_amount) as under_amount
        FROM project_receipts pr
        JOIN receipt_invoice_allocations ria ON ria.receipt_id = pr.id
        WHERE pr.status = 'confirmed' AND pr.amount > 0
        GROUP BY pr.id, pr.receipt_number, pr.amount, pr.header_id
        HAVING SUM(ria.allocated_amount) < pr.amount - 0.01
    """)
    return db.session.execute(sql).fetchall()


def fix_zero_amount_allocations(receipt_ids):
    """删除金额为0收款的分配记录"""
    if not receipt_ids:
        return
    sql = text("DELETE FROM receipt_invoice_allocations WHERE receipt_id IN :ids")
    db.session.execute(sql, {'ids': tuple(receipt_ids)})


def fix_negative_allocations(alloc_ids):
    """删除负数分配记录"""
    if not alloc_ids:
        return
    sql = text("DELETE FROM receipt_invoice_allocations WHERE id IN :ids")
    db.session.execute(sql, {'ids': tuple(alloc_ids)})


def update_invoice_paid_amounts():
    """重新计算并更新所有发票的已付金额"""
    sql = text("""
        UPDATE project_invoices pi
        SET paid_amount = COALESCE((
            SELECT SUM(ria.allocated_amount)
            FROM receipt_invoice_allocations ria
            JOIN project_receipts pr ON ria.receipt_id = pr.id
            WHERE ria.invoice_id = pi.id AND pr.status = 'confirmed'
        ), 0)
    """)
    db.session.execute(sql)


def main():
    fix_mode = '--fix' in sys.argv

    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("检查无效的收款分配记录")
        print("=" * 80)
        print()

        issues_found = False
        zero_receipt_ids = []
        negative_alloc_ids = []
        affected_invoice_ids = set()

        # 1. 检查收款金额为0但有分配
        print("【1】收款金额为0但有分配记录：")
        print("-" * 60)
        zero_issues = check_zero_amount_with_allocation()
        if zero_issues:
            issues_found = True
            print(f"{'收款ID':<8} {'收款单号':<12} {'收款金额':>10} {'项目ID':<8} {'分配数':>6} {'分配总额':>12}")
            print("-" * 60)
            for r in zero_issues:
                print(f"{r[0]:<8} {r[1]:<12} {float(r[2]):>10.2f} {r[3]:<8} {r[4]:>6} {float(r[5]):>12.2f}")
                zero_receipt_ids.append(r[0])
        else:
            print("✓ 未发现问题")
        print()

        # 2. 检查负数分配
        print("【2】分配金额为负数：")
        print("-" * 60)
        negative_issues = check_negative_allocations()
        if negative_issues:
            issues_found = True
            print(f"{'分配ID':<8} {'收款单号':<12} {'收款金额':>10} {'发票号':<12} {'分配金额':>12} {'项目ID':<8}")
            print("-" * 60)
            for r in negative_issues:
                print(f"{r[0]:<8} {r[4]:<12} {float(r[5]):>10.2f} {r[6]:<12} {float(r[3]):>12.2f} {r[7]:<8}")
                negative_alloc_ids.append(r[0])
                affected_invoice_ids.add(r[2])
        else:
            print("✓ 未发现问题")
        print()

        # 3. 检查超额分配
        print("【3】分配总额超过收款金额：")
        print("-" * 60)
        over_issues = check_over_allocated()
        if over_issues:
            issues_found = True
            print(f"{'收款ID':<8} {'收款单号':<12} {'收款金额':>10} {'项目ID':<8} {'分配总额':>12} {'超额':>10}")
            print("-" * 60)
            for r in over_issues:
                print(f"{r[0]:<8} {r[1]:<12} {float(r[2]):>10.2f} {r[3]:<8} {float(r[4]):>12.2f} {float(r[5]):>10.2f}")
        else:
            print("✓ 未发现问题")
        print()

        # 4. 检查分配不完整
        print("【4】分配总额少于收款金额（分配不完整）：")
        print("-" * 60)
        under_issues = check_under_allocated()
        if under_issues:
            issues_found = True
            print(f"{'收款ID':<8} {'收款单号':<12} {'收款金额':>10} {'项目ID':<8} {'分配总额':>12} {'少分配':>10}")
            print("-" * 60)
            for r in under_issues:
                print(f"{r[0]:<8} {r[1]:<12} {float(r[2]):>10.2f} {r[3]:<8} {float(r[4]):>12.2f} {float(r[5]):>10.2f}")
        else:
            print("✓ 未发现问题")
        print()

        # 汇总
        print("=" * 80)
        if not issues_found:
            print("✓ 所有检查通过，未发现无效分配记录")
            return

        print("问题汇总：")
        print(f"  - 收款金额为0但有分配: {len(zero_receipt_ids)} 条")
        print(f"  - 分配金额为负数: {len(negative_alloc_ids)} 条")
        print(f"  - 分配超额: {len(over_issues)} 条 (需手动检查)")
        print(f"  - 分配不完整: {len(under_issues)} 条 (需手动检查)")
        print()

        if fix_mode:
            print("开始修复...")

            # 修复金额为0的收款分配
            if zero_receipt_ids:
                fix_zero_amount_allocations(zero_receipt_ids)
                print(f"  ✓ 已删除 {len(zero_receipt_ids)} 条金额为0收款的分配记录")

            # 修复负数分配
            if negative_alloc_ids:
                fix_negative_allocations(negative_alloc_ids)
                print(f"  ✓ 已删除 {len(negative_alloc_ids)} 条负数分配记录")

            # 更新发票已付金额
            update_invoice_paid_amounts()
            print("  ✓ 已重新计算所有发票的已付金额")

            db.session.commit()
            print()
            print("✓ 修复完成")
        else:
            print("提示: 使用 --fix 参数执行修复")
            print("  python scripts/fix_invalid_receipt_allocations.py --fix")
            print()
            print("注意: ")
            print("  - 超额分配和分配不完整问题需要手动检查，脚本不会自动修复")
            print("  - 分配不完整可能是收款金额与发票金额不匹配，需核实后手动调整")


if __name__ == '__main__':
    main()
