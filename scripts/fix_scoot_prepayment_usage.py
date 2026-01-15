# -*- coding: utf-8 -*-
"""
修复 SCOOT 预付账款使用记录

问题：从 Athina 导入的付款记录标记为 payment_source='prepayment'，
但没有创建 PrepaymentUsage 记录，导致预付账款余额不正确。

修复步骤：
1. 查找 SCOOT 所有 payment_source='prepayment' 的付款记录
2. 查找这些付款关联的 EO
3. 按 FIFO 原则为每个 EO 创建 PrepaymentUsage 记录
4. 重新计算预付账款余额

运行方式: python scripts/fix_scoot_prepayment_usage.py
确认执行: python scripts/fix_scoot_prepayment_usage.py --confirm
"""

import sys
import os
import argparse
from decimal import Decimal
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.supplier_payment import SupplierPayment
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment, PrepaymentUsage
from App_new.business.projects.models.eo import ProjectEO


def main():
    parser = argparse.ArgumentParser(description='修复 SCOOT 预付账款使用记录')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    parser.add_argument('--supplier-id', type=int, default=226, help='供应商ID，默认226(SCOOT)')
    args = parser.parse_args()

    dry_run = not args.confirm
    supplier_id = args.supplier_id

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print(f"  修复供应商 ID={supplier_id} 预付账款使用记录")
        print("=" * 70)

        if dry_run:
            print("\n  [预览模式 - 数据不会实际修改]")

        # 1. 查找该供应商所有预付账款记录（按创建时间排序 - FIFO）
        prepayments = SupplierPrepayment.query.filter_by(
            supplier_id=supplier_id
        ).order_by(SupplierPrepayment.payment_date.asc()).all()

        print(f"\n预付账款记录: {len(prepayments)} 条")
        total_prepayment = Decimal('0')
        for p in prepayments:
            print(f"  {p.prepayment_number}: 充值 {p.amount} SGD, 日期 {p.payment_date}")
            total_prepayment += Decimal(str(p.amount))
        print(f"  合计充值: {total_prepayment} SGD")

        # 2. 查找该供应商 payment_source='prepayment' 的付款记录
        payments = SupplierPayment.query.filter(
            SupplierPayment.supplier_id == supplier_id,
            SupplierPayment.payment_source == 'prepayment'
        ).order_by(SupplierPayment.payment_date.asc()).all()

        print(f"\n预付款付款记录: {len(payments)} 条")
        total_payment = Decimal('0')
        for p in payments:
            print(f"  {p.payment_no}: {p.total_amount} SGD, 日期 {p.payment_date}")
            total_payment += Decimal(str(p.total_amount))
        print(f"  合计付款: {total_payment} SGD")

        # 3. 查找这些付款关联的 EO
        print("\n" + "-" * 70)
        print("分析付款记录关联的 EO...")

        all_eos = []
        for payment in payments:
            eos = ProjectEO.query.filter_by(payment_record_id=payment.id).all()
            for eo in eos:
                # 检查是否已有使用记录
                existing_usage = PrepaymentUsage.query.filter_by(
                    eo_id=eo.id,
                    status='confirmed'
                ).first()
                all_eos.append({
                    'eo': eo,
                    'payment': payment,
                    'has_usage': existing_usage is not None,
                    'existing_usage': existing_usage
                })

        eos_without_usage = [e for e in all_eos if not e['has_usage']]
        print(f"  总 EO 数量: {len(all_eos)}")
        print(f"  已有使用记录: {len(all_eos) - len(eos_without_usage)}")
        print(f"  缺少使用记录: {len(eos_without_usage)}")

        if not eos_without_usage:
            print("\n所有 EO 都已有预付使用记录，无需修复。")
            return

        # 4. 按付款日期排序需要创建使用记录的 EO
        eos_without_usage.sort(key=lambda x: (x['payment'].payment_date, x['eo'].id))

        print("\n" + "-" * 70)
        print("需要创建使用记录的 EO:")
        for item in eos_without_usage:
            eo = item['eo']
            payment = item['payment']
            amount = eo.pay_amount or eo.cost_price or Decimal('0')
            print(f"  {eo.eo_number}: {amount} SGD (付款日期: {payment.payment_date})")

        # 5. 重置预付账款余额（用于重新计算）
        if not dry_run:
            print("\n" + "-" * 70)
            print("重置预付账款余额...")
            for p in prepayments:
                # 计算已有的confirmed使用记录总额
                existing_usages = PrepaymentUsage.query.filter_by(
                    prepayment_id=p.id,
                    status='confirmed'
                ).all()
                used_amount = sum(Decimal(str(u.amount)) for u in existing_usages)
                p.balance_amount = Decimal(str(p.amount)) - used_amount
                print(f"  {p.prepayment_number}: 余额重置为 {p.balance_amount}")

        # 6. 按 FIFO 为每个 EO 创建使用记录
        print("\n" + "-" * 70)
        print("按 FIFO 创建预付使用记录...")

        created_count = 0
        prepayment_index = 0

        for item in eos_without_usage:
            eo = item['eo']
            payment = item['payment']
            amount_to_allocate = Decimal(str(eo.pay_amount or eo.cost_price or 0))

            if amount_to_allocate <= 0:
                print(f"  跳过 {eo.eo_number}: 金额为 0")
                continue

            print(f"\n  处理 {eo.eo_number}: {amount_to_allocate} SGD")

            # 按 FIFO 从预付账款扣减
            while amount_to_allocate > 0 and prepayment_index < len(prepayments):
                current_prepayment = prepayments[prepayment_index]

                # 在 dry_run 模式下模拟余额
                if dry_run:
                    # 计算模拟余额
                    existing_usages = PrepaymentUsage.query.filter_by(
                        prepayment_id=current_prepayment.id,
                        status='confirmed'
                    ).all()
                    simulated_balance = Decimal(str(current_prepayment.amount)) - sum(
                        Decimal(str(u.amount)) for u in existing_usages
                    )
                    # 减去之前在此次运行中分配的金额
                    for prev_item in eos_without_usage[:eos_without_usage.index(item)]:
                        if hasattr(prev_item, 'allocations'):
                            for alloc in prev_item.get('allocations', []):
                                if alloc['prepayment_id'] == current_prepayment.id:
                                    simulated_balance -= alloc['amount']
                    available_balance = simulated_balance
                else:
                    available_balance = current_prepayment.balance_amount

                if available_balance <= 0:
                    prepayment_index += 1
                    continue

                deduct_amount = min(amount_to_allocate, available_balance)

                print(f"    从 {current_prepayment.prepayment_number} 扣减 {deduct_amount} SGD")

                if not dry_run:
                    # 创建使用记录
                    usage = PrepaymentUsage(
                        prepayment_id=current_prepayment.id,
                        eo_id=eo.id,
                        ref_id=eo.ref_id,
                        amount=deduct_amount,
                        usage_date=payment.payment_date or date.today(),
                        description=f'Athina导入修复 {eo.eo_number}',
                        status='confirmed',
                        created_by='System Fix'
                    )
                    db.session.add(usage)

                    # 更新预付账款余额
                    current_prepayment.balance_amount -= deduct_amount
                    current_prepayment.update_status()

                    created_count += 1
                else:
                    # 记录分配用于模拟
                    if 'allocations' not in item:
                        item['allocations'] = []
                    item['allocations'].append({
                        'prepayment_id': current_prepayment.id,
                        'amount': deduct_amount
                    })
                    created_count += 1

                amount_to_allocate -= deduct_amount

                if current_prepayment.balance_amount <= 0 if not dry_run else (available_balance - deduct_amount) <= 0:
                    prepayment_index += 1

            if amount_to_allocate > 0:
                print(f"    警告: 预付账款不足，剩余 {amount_to_allocate} SGD 无法分配")

        print("\n" + "=" * 70)

        if not dry_run:
            try:
                db.session.commit()
                print(f"  修复完成！创建了 {created_count} 条使用记录")

                # 显示最终余额
                print("\n预付账款最终余额:")
                for p in prepayments:
                    db.session.refresh(p)
                    print(f"  {p.prepayment_number}: {p.balance_amount} SGD ({p.status})")
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(f"  预览完成！将创建 {created_count} 条使用记录")
            print(f"\n确认修复请添加 --confirm 参数:")
            print(f"  python scripts/fix_scoot_prepayment_usage.py --confirm")


if __name__ == '__main__':
    main()
