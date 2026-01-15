# -*- coding: utf-8 -*-
"""
修复 SCOOT 供应商付款记录的 payment_source 字段

问题：从 Athina 导入的付款记录默认 payment_source='bank'
实际：SCOOT 付款都使用预付账款支付

修复：将 SCOOT (supplier_id=226) 的付款记录改为 prepayment

运行方式: python scripts/fix_scoot_payment_source.py
确认执行: python scripts/fix_scoot_payment_source.py --confirm
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.supplier_payment import SupplierPayment


def main():
    parser = argparse.ArgumentParser(description='修复 SCOOT 付款记录的 payment_source')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    parser.add_argument('--supplier-id', type=int, default=226, help='供应商ID，默认226(SCOOT)')
    args = parser.parse_args()

    dry_run = not args.confirm
    supplier_id = args.supplier_id

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print(f"  修复供应商 ID={supplier_id} 付款记录的 payment_source 为 prepayment")
        print("=" * 70)

        if dry_run:
            print("\n  [预览模式 - 数据不会实际修改]")

        # 查询该供应商所有非 prepayment 的付款记录
        payments = SupplierPayment.query.filter(
            SupplierPayment.supplier_id == supplier_id,
            SupplierPayment.payment_source != 'prepayment'
        ).all()

        if not payments:
            print(f"\n没有需要修复的记录（所有付款已是 prepayment）")
            return

        print(f"\n需要修复的付款记录: {len(payments)} 条\n")

        for p in payments:
            print(f"  {p.payment_no}:")
            print(f"    付款日期: {p.payment_date}")
            print(f"    总金额: {p.total_amount} {p.currency}")
            print(f"    当前来源: {p.payment_source} -> 改为: prepayment")
            print(f"    prepayment_amount: {p.prepayment_amount} -> 改为: {p.total_amount}")
            print()

            if not dry_run:
                p.payment_source = 'prepayment'
                p.prepayment_amount = p.total_amount

        print("-" * 70)

        if not dry_run:
            try:
                db.session.commit()
                print("\n" + "=" * 70)
                print(f"  修复完成！已更新 {len(payments)} 条记录")
                print("=" * 70)
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return
        else:
            print(f"\n预览完成。确认修复请添加 --confirm 参数:")
            print(f"  python scripts/fix_scoot_payment_source.py --confirm")


if __name__ == '__main__':
    main()
