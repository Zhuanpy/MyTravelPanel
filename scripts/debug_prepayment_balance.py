"""
诊断脚本：检查 US-BANGLA AIRLINES LTD (supplier_id=227) 的预付余额
运行方式: python scripts/debug_prepayment_balance.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment, PrepaymentUsage
    from App_new.business.projects.models.project import ProjectEO

    supplier_id = 227

    # 1. 查看所有预付记录
    print("=" * 80)
    print(f"供应商 ID={supplier_id} 的预付记录")
    print("=" * 80)
    prepayments = SupplierPrepayment.query.filter_by(supplier_id=supplier_id).all()
    total_balance = 0
    for p in prepayments:
        print(f"  ID={p.id} | {p.prepayment_number} | 充值={p.amount} | 余额={p.balance_amount} | 状态={p.status} | 日期={p.payment_date}")
        if p.status in ('confirmed', 'partial_used') and p.balance_amount > 0:
            total_balance += float(p.balance_amount)
    print(f"\n  可用总余额: SGD {total_balance:.2f}")

    # 2. 查看所有使用记录（最近的排在前面）
    print("\n" + "=" * 80)
    print(f"预付使用记录（最近20条）")
    print("=" * 80)
    usages = PrepaymentUsage.query.join(SupplierPrepayment).filter(
        SupplierPrepayment.supplier_id == supplier_id
    ).order_by(PrepaymentUsage.created_at.desc()).limit(20).all()

    for u in usages:
        eo_number = ''
        eo_status = ''
        if u.eo_id:
            eo = ProjectEO.query.get(u.eo_id)
            if eo:
                eo_number = eo.eo_number
                eo_status = eo.status
        print(f"  Usage ID={u.id} | 预付ID={u.prepayment_id} | 金额={u.amount} | 状态={u.status} | EO={eo_number}({eo_status}) | {u.description} | 创建={u.created_at}")

    # 3. 检查异常：已作废的EO但使用记录仍为confirmed/pending
    print("\n" + "=" * 80)
    print("异常检查：已作废EO但使用记录未冲销")
    print("=" * 80)
    abnormal_usages = PrepaymentUsage.query.join(SupplierPrepayment).join(
        ProjectEO, PrepaymentUsage.eo_id == ProjectEO.id
    ).filter(
        SupplierPrepayment.supplier_id == supplier_id,
        ProjectEO.status == 'void',
        PrepaymentUsage.status.in_(['confirmed', 'pending'])
    ).all()

    if abnormal_usages:
        print("  *** 发现异常! ***")
        for u in abnormal_usages:
            eo = ProjectEO.query.get(u.eo_id)
            print(f"  Usage ID={u.id} | 金额={u.amount} | 使用状态={u.status} | EO={eo.eo_number}(状态={eo.status}) | 预付ID={u.prepayment_id}")
        print(f"\n  这些记录扣了余额但EO已作废，需要恢复!")
    else:
        print("  未发现异常")

    # 4. 检查：balance_amount 与实际使用记录是否一致
    print("\n" + "=" * 80)
    print("一致性检查：balance_amount vs 实际使用")
    print("=" * 80)
    for p in prepayments:
        # 统计该预付记录的所有confirmed使用
        confirmed_usage = db.session.query(db.func.sum(PrepaymentUsage.amount)).filter(
            PrepaymentUsage.prepayment_id == p.id,
            PrepaymentUsage.status == 'confirmed'
        ).scalar() or 0

        pending_usage = db.session.query(db.func.sum(PrepaymentUsage.amount)).filter(
            PrepaymentUsage.prepayment_id == p.id,
            PrepaymentUsage.status == 'pending'
        ).scalar() or 0

        expected_balance = float(p.amount) - float(confirmed_usage) - float(pending_usage)
        actual_balance = float(p.balance_amount)
        diff = actual_balance - expected_balance

        status_icon = "✓" if abs(diff) < 0.01 else "✗"
        print(f"  {status_icon} 预付ID={p.id} | 充值={p.amount} | confirmed使用={confirmed_usage} | pending使用={pending_usage} | 预期余额={expected_balance:.2f} | 实际余额={actual_balance:.2f} | 差异={diff:.2f}")
