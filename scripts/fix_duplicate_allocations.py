"""
修复收款重复分配问题

问题描述：
CSV导入的多项目合并收款，每个发票都被分配了收款全额，
而不是按发票金额分配，导致严重的重复计算。

修复逻辑：
1. 找出总分配金额超过收款金额的收款
2. 删除现有分配记录
3. 按发票金额重新创建分配记录
4. 更新发票已付金额

使用方法：
python scripts/fix_duplicate_allocations.py          # 仅检查
python scripts/fix_duplicate_allocations.py --fix    # 检查并修复
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app, db
from sqlalchemy import text
from decimal import Decimal


def get_over_allocated_receipts():
    """获取总分配超过收款金额的收款"""
    sql = text("""
        SELECT
            pr.id as receipt_id,
            pr.receipt_number,
            pr.amount as receipt_amount,
            SUM(ria.allocated_amount) as total_allocated,
            COUNT(ria.id) as alloc_count
        FROM project_receipts pr
        JOIN receipt_invoice_allocations ria ON ria.receipt_id = pr.id
        WHERE pr.status = 'confirmed'
        GROUP BY pr.id, pr.receipt_number, pr.amount
        HAVING SUM(ria.allocated_amount) > pr.amount + 0.01
        ORDER BY SUM(ria.allocated_amount) - pr.amount DESC
    """)
    return db.session.execute(sql).fetchall()


def get_receipt_allocations(receipt_id):
    """获取收款的所有分配详情"""
    sql = text("""
        SELECT
            ria.id as alloc_id,
            ria.invoice_id,
            pi.invoice_number,
            pi.header_id,
            ph.hid,
            pi.amount as invoice_amount,
            ria.allocated_amount
        FROM receipt_invoice_allocations ria
        JOIN project_invoices pi ON ria.invoice_id = pi.id
        JOIN project_headers ph ON pi.header_id = ph.id
        WHERE ria.receipt_id = :receipt_id
        ORDER BY pi.id
    """)
    return db.session.execute(sql, {'receipt_id': receipt_id}).fetchall()


def fix_receipt_allocations(receipt_id, receipt_amount):
    """修复单笔收款的分配"""
    # 获取分配详情
    allocations = get_receipt_allocations(receipt_id)
    if not allocations:
        return False, "无分配记录"

    # 计算发票总金额
    invoice_total = sum(float(a[5]) for a in allocations)  # invoice_amount

    # 检查发票总金额是否与收款金额匹配（允许小误差）
    if abs(invoice_total - float(receipt_amount)) > 0.01:
        # 不匹配，需要手动检查
        return False, f"发票总额({invoice_total:.2f})与收款({float(receipt_amount):.2f})不匹配"

    # 删除现有分配记录
    delete_sql = text("DELETE FROM receipt_invoice_allocations WHERE receipt_id = :receipt_id")
    db.session.execute(delete_sql, {'receipt_id': receipt_id})

    # 按发票金额重新创建分配记录
    insert_sql = text("""
        INSERT INTO receipt_invoice_allocations (receipt_id, invoice_id, allocated_amount)
        VALUES (:receipt_id, :invoice_id, :amount)
    """)

    invoice_ids_amounts = []
    for a in allocations:
        invoice_id = a[1]
        invoice_amount = float(a[5])
        db.session.execute(insert_sql, {
            'receipt_id': receipt_id,
            'invoice_id': invoice_id,
            'amount': invoice_amount
        })
        invoice_ids_amounts.append((invoice_id, invoice_amount))

    # 更新发票已付金额
    for invoice_id, amount in invoice_ids_amounts:
        # 重新计算发票的总已付金额
        calc_sql = text("""
            SELECT COALESCE(SUM(ria.allocated_amount), 0)
            FROM receipt_invoice_allocations ria
            JOIN project_receipts pr ON ria.receipt_id = pr.id
            WHERE ria.invoice_id = :invoice_id AND pr.status = 'confirmed'
        """)
        paid = db.session.execute(calc_sql, {'invoice_id': invoice_id}).scalar()

        update_sql = text("UPDATE project_invoices SET paid_amount = :paid WHERE id = :id")
        db.session.execute(update_sql, {'paid': paid, 'id': invoice_id})

    return True, f"已修复，{len(allocations)}条分配"


def main():
    fix_mode = '--fix' in sys.argv

    app = create_app()
    with app.app_context():
        print("=" * 90)
        print("检查收款重复分配问题")
        print("=" * 90)
        print()

        receipts = get_over_allocated_receipts()

        if not receipts:
            print("✓ 未发现重复分配问题")
            return

        print(f"发现 {len(receipts)} 笔收款存在重复分配：")
        print()
        print("-" * 90)
        print(f"{'收款ID':<8} {'收款单号':<20} {'收款金额':>12} {'分配总额':>14} {'超额':>12} {'分配数':>6}")
        print("-" * 90)

        total_over = 0
        can_fix = []
        cannot_fix = []

        for r in receipts:
            receipt_id = r[0]
            receipt_number = r[1]
            receipt_amount = float(r[2])
            total_allocated = float(r[3])
            alloc_count = r[4]
            over_amount = total_allocated - receipt_amount

            total_over += over_amount

            # 检查是否可以自动修复
            allocations = get_receipt_allocations(receipt_id)
            invoice_total = sum(float(a[5]) for a in allocations)

            if abs(invoice_total - receipt_amount) <= 0.01:
                can_fix.append(r)
                marker = "✓ "
            else:
                cannot_fix.append((r, invoice_total))
                marker = "✗ "

            print(f"{marker}{receipt_id:<6} {receipt_number:<20} {receipt_amount:>12.2f} {total_allocated:>14.2f} {over_amount:>12.2f} {alloc_count:>6}")

        print("-" * 90)
        print(f"总超额: {total_over:,.2f}")
        print()
        print(f"可自动修复: {len(can_fix)} 笔 (发票总额=收款金额)")
        print(f"需手动检查: {len(cannot_fix)} 笔 (发票总额≠收款金额)")
        print()

        if cannot_fix:
            print("需手动检查的收款：")
            for r, inv_total in cannot_fix[:10]:  # 只显示前10条
                print(f"  收款{r[1]} (ID:{r[0]}): 收款{float(r[2]):.2f}, 发票总额{inv_total:.2f}")
            if len(cannot_fix) > 10:
                print(f"  ... 还有 {len(cannot_fix) - 10} 条")
            print()

        if fix_mode and can_fix:
            print("开始修复...")
            fixed_count = 0
            for r in can_fix:
                receipt_id = r[0]
                receipt_number = r[1]
                receipt_amount = r[2]

                success, msg = fix_receipt_allocations(receipt_id, receipt_amount)
                if success:
                    fixed_count += 1
                    print(f"  ✓ 收款 {receipt_number}: {msg}")
                else:
                    print(f"  ✗ 收款 {receipt_number}: {msg}")

            db.session.commit()
            print()
            print(f"✓ 已修复 {fixed_count} 笔收款的分配记录")
        elif not fix_mode:
            print("提示: 使用 --fix 参数执行修复")
            print("  python scripts/fix_duplicate_allocations.py --fix")


if __name__ == '__main__':
    main()
