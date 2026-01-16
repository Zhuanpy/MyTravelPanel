# -*- coding: utf-8 -*-
"""
修复 US-BANGLA AIRLINES LTD 预付账款使用记录

问题：预付款使用记录顺序混乱，应该按 EO 时间顺序依次使用

修复步骤：
1. 查找 US-BANGLA 所有预付账款记录 (supplier_id = 227)
2. 清除所有使用记录（PrepaymentUsage）
3. 重置所有预付账款余额为充值金额
4. 查找所有该供应商的已付款 EO（通过 REF 的 supplier_id）
5. 按 EO 付款时间排序，按 FIFO 原则重新分配使用记录

运行方式: python scripts/fix_usbangla_prepayment_usage.py
确认执行: python scripts/fix_usbangla_prepayment_usage.py --confirm
"""

import sys
import os
import argparse
from decimal import Decimal
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment, PrepaymentUsage
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.project import CustomerCompany
from App_new.business.projects.models.ref import ProjectRef

# US-BANGLA AIRLINES LTD 的 supplier_id
SUPPLIER_ID = 227


def main():
    parser = argparse.ArgumentParser(description='修复 US-BANGLA 预付账款使用记录')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    args = parser.parse_args()

    dry_run = not args.confirm

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("  修复 US-BANGLA AIRLINES LTD 预付账款使用记录")
        print("=" * 70)

        if dry_run:
            print("\n  [预览模式 - 数据不会实际修改]")

        # 1. 确认供应商
        supplier_id = SUPPLIER_ID
        supplier = CustomerCompany.query.get(supplier_id)
        if not supplier:
            print(f"\n错误: 未找到供应商 ID={supplier_id}")
            return

        print(f"\n供应商: {supplier.company_name} (ID: {supplier_id})")

        # 2. 查找该供应商所有预付账款记录（按充值日期排序 - FIFO）
        prepayments = SupplierPrepayment.query.filter_by(
            supplier_id=supplier_id
        ).filter(
            SupplierPrepayment.status != 'cancelled'
        ).order_by(SupplierPrepayment.payment_date.asc(), SupplierPrepayment.id.asc()).all()

        print(f"\n预付账款记录: {len(prepayments)} 条")
        total_prepayment = Decimal('0')
        for p in prepayments:
            print(f"  {p.prepayment_number}: 充值 {p.amount} SGD, 日期 {p.payment_date}, 当前余额 {p.balance_amount}")
            total_prepayment += Decimal(str(p.amount))
        print(f"  合计充值: {total_prepayment} SGD")

        prepayment_ids = [p.id for p in prepayments]

        # 3. 查找所有该供应商的已付款 EO（通过 REF 的 supplier_id）
        refs_with_supplier = ProjectRef.query.filter_by(supplier_id=supplier_id).all()
        ref_ids = [r.id for r in refs_with_supplier]

        print(f"\n该供应商的 REF 数量: {len(ref_ids)}")

        # 查找这些 REF 对应的已付款 EO
        all_eos = ProjectEO.query.filter(
            ProjectEO.ref_id.in_(ref_ids),
            ProjectEO.status == 'paid'
        ).all() if ref_ids else []

        print(f"已付款的 EO 数量: {len(all_eos)}")

        if not all_eos:
            print("\n没有找到需要处理的已付款 EO，退出。")
            return

        # 4. 按 EO 的付款日期/创建日期排序
        def get_eo_date(eo):
            """获取 EO 的排序日期"""
            if eo.paid_date:
                return eo.paid_date
            if eo.created_at:
                return eo.created_at.date()
            return date.max

        all_eos.sort(key=lambda x: (get_eo_date(x), x.id))

        print("\n按时间排序的 EO 列表:")
        total_eo_amount = Decimal('0')
        for eo in all_eos:
            amount = Decimal(str(eo.pay_amount or 0))
            if amount == 0 and eo.ref:
                amount = Decimal(str(eo.ref.cost_price or 0))
            total_eo_amount += amount
            print(f"  {eo.eo_number}: {amount} SGD (日期: {get_eo_date(eo)})")
        print(f"  合计需分配: {total_eo_amount} SGD")

        # 5. 清除现有使用记录
        print("\n" + "-" * 70)
        print("清除现有使用记录...")

        usage_count = PrepaymentUsage.query.filter(
            PrepaymentUsage.prepayment_id.in_(prepayment_ids)
        ).count()
        print(f"  将删除 {usage_count} 条使用记录")

        if not dry_run:
            PrepaymentUsage.query.filter(
                PrepaymentUsage.prepayment_id.in_(prepayment_ids)
            ).delete(synchronize_session=False)

        # 6. 重置预付账款余额
        print("\n重置预付账款余额...")
        for p in prepayments:
            print(f"  {p.prepayment_number}: {p.balance_amount} -> {p.amount}")
            if not dry_run:
                p.balance_amount = p.amount
                p.status = 'confirmed'

        # 7. 按 FIFO 为每个 EO 创建使用记录
        print("\n" + "-" * 70)
        print("按 FIFO 重新分配预付款使用...")

        created_count = 0
        prepayment_index = 0

        # 用于预览模式的模拟余额
        simulated_balances = {p.id: Decimal(str(p.amount)) for p in prepayments}

        for eo in all_eos:
            amount_to_allocate = Decimal(str(eo.pay_amount or 0))
            if amount_to_allocate == 0 and eo.ref:
                amount_to_allocate = Decimal(str(eo.ref.cost_price or 0))

            if amount_to_allocate <= 0:
                continue

            print(f"\n  处理 {eo.eo_number}: {amount_to_allocate} SGD (日期: {get_eo_date(eo)})")

            # 按 FIFO 从预付账款扣减
            while amount_to_allocate > 0 and prepayment_index < len(prepayments):
                current_prepayment = prepayments[prepayment_index]

                if dry_run:
                    available_balance = simulated_balances[current_prepayment.id]
                else:
                    available_balance = current_prepayment.balance_amount

                if available_balance <= 0:
                    prepayment_index += 1
                    continue

                deduct_amount = min(amount_to_allocate, available_balance)

                print(f"    从 {current_prepayment.prepayment_number} (日期:{current_prepayment.payment_date}) 扣减 {deduct_amount} SGD")

                if not dry_run:
                    # 创建使用记录
                    usage = PrepaymentUsage(
                        prepayment_id=current_prepayment.id,
                        eo_id=eo.id,
                        ref_id=eo.ref_id,
                        amount=deduct_amount,
                        usage_date=get_eo_date(eo),
                        description=f'预付款修复 {eo.eo_number}',
                        status='confirmed',
                        created_by='System Fix'
                    )
                    db.session.add(usage)

                    # 更新预付账款余额
                    current_prepayment.balance_amount -= deduct_amount
                    current_prepayment.update_status()
                else:
                    simulated_balances[current_prepayment.id] -= deduct_amount

                created_count += 1
                amount_to_allocate -= deduct_amount

                # 检查当前预付款是否用完
                new_balance = simulated_balances[current_prepayment.id] if dry_run else current_prepayment.balance_amount
                if new_balance <= 0:
                    prepayment_index += 1

            if amount_to_allocate > 0:
                print(f"    警告: 预付账款不足，剩余 {amount_to_allocate} SGD 无法分配")

        print("\n" + "=" * 70)

        if not dry_run:
            try:
                db.session.commit()
                print(f"  修复完成！创建了 {created_count} 条使用记录")

                # 显示最终余额
                print("\n预付账款最终状态:")
                for p in prepayments:
                    db.session.refresh(p)
                    print(f"  {p.prepayment_number}: 充值 {p.amount}, 余额 {p.balance_amount}, 状态: {p.status_display}")
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(f"  预览完成！将创建 {created_count} 条使用记录")

            print("\n预付账款预计最终状态:")
            for p in prepayments:
                final_balance = simulated_balances[p.id]
                if final_balance <= 0:
                    status = '已用完'
                elif final_balance < Decimal(str(p.amount)):
                    status = '部分使用'
                else:
                    status = '已确认'
                print(f"  {p.prepayment_number}: 充值 {p.amount}, 余额 {final_balance}, 状态: {status}")

            print(f"\n确认修复请添加 --confirm 参数:")
            print(f"  python scripts/fix_usbangla_prepayment_usage.py --confirm")


if __name__ == '__main__':
    main()
