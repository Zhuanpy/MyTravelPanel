# -*- coding: utf-8 -*-
"""
修复付款记录的 payment_source 字段

根据 prepayment_amount 和 total_amount 判断正确的 payment_source:
- 全部使用预付账款: prepayment
- 全部银行付款: bank
- 混合付款: mixed

运行方式: python scripts/fix_payment_source.py
确认执行: python scripts/fix_payment_source.py --confirm
"""

import sys
import os
import argparse
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.supplier_payment import SupplierPayment


def main():
    parser = argparse.ArgumentParser(description='修复付款记录的 payment_source 字段')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    args = parser.parse_args()

    dry_run = not args.confirm

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("  修复付款记录的 payment_source 字段")
        print("=" * 70)

        if dry_run:
            print("\n  [预览模式 - 数据不会实际修改]")

        # 查询所有付款记录
        payments = SupplierPayment.query.all()
        print(f"\n共 {len(payments)} 条付款记录")

        fixed_count = 0
        for p in payments:
            total = Decimal(str(p.total_amount)) if p.total_amount else Decimal('0')
            prepay = Decimal(str(p.prepayment_amount)) if p.prepayment_amount else Decimal('0')

            # 判断正确的 payment_source
            if prepay > 0 and prepay >= total:
                correct_source = 'prepayment'
            elif prepay > 0 and prepay < total:
                correct_source = 'mixed'
            else:
                correct_source = 'bank'

            # 检查是否需要修复
            if p.payment_source != correct_source:
                supplier_name = p.supplier.company_name if p.supplier else '未知'
                print(f"\n  {p.payment_no}:")
                print(f"    供应商: {supplier_name}")
                print(f"    总金额: {total}, 预付使用: {prepay}")
                print(f"    当前: {p.payment_source} -> 应为: {correct_source}")

                if not dry_run:
                    p.payment_source = correct_source

                fixed_count += 1

        print("\n" + "-" * 70)
        print(f"需要修复: {fixed_count} 条")

        if not dry_run and fixed_count > 0:
            try:
                db.session.commit()
                print("\n" + "=" * 70)
                print("  修复完成！数据已保存")
                print("=" * 70)
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return

        if dry_run and fixed_count > 0:
            print(f"\n预览完成。确认修复请添加 --confirm 参数:")
            print(f"  python scripts/fix_payment_source.py --confirm")


if __name__ == '__main__':
    main()
