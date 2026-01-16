# -*- coding: utf-8 -*-
"""
修复收款记录金额问题

问题：从 Athina 导入的收款记录可能包含多个项目的款项，
但只关联到了一个项目，导致金额显示错误。

修复逻辑：
1. 查找所有 extra_info 中包含多个 ref_numbers 的收款记录
2. 解析 extra_info 中的 items，找出属于当前 ref_id 的金额
3. 更新收款金额为正确的值

运行方式: python scripts/fix_receipt_multi_ref_amount.py
确认执行: python scripts/fix_receipt_multi_ref_amount.py --confirm
"""

import sys
import os
import json
import argparse
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.ref import ProjectRef


def main():
    parser = argparse.ArgumentParser(description='修复收款记录金额问题')
    parser.add_argument('--confirm', action='store_true', help='确认执行（不加此参数只预览）')
    args = parser.parse_args()

    dry_run = not args.confirm

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("  修复收款记录金额问题（多REF收款）")
        print("=" * 70)

        if dry_run:
            print("\n  [预览模式 - 数据不会实际修改]")

        # 查找所有有 extra_info 的收款记录
        receipts = ProjectReceipt.query.filter(
            ProjectReceipt.extra_info.isnot(None)
        ).all()

        print(f"\n共有 {len(receipts)} 条收款记录有 extra_info")

        fix_count = 0
        skip_count = 0
        error_count = 0

        for receipt in receipts:
            try:
                # 解析 extra_info
                if not receipt.extra_info:
                    continue

                extra_info = json.loads(receipt.extra_info)
                items = extra_info.get('items', [])

                # 检查是否有多个 ref
                if len(items) <= 1:
                    continue

                # 获取关联的 ref
                if not receipt.ref_id:
                    continue

                ref = ProjectRef.query.get(receipt.ref_id)
                if not ref:
                    continue

                # 查找属于当前 ref 的金额
                correct_amount = None
                for item in items:
                    item_ref_number = item.get('ref_number')
                    if item_ref_number == ref.ref_number:
                        correct_amount = Decimal(str(item.get('amount', 0)))
                        break

                if correct_amount is None:
                    print(f"\n  警告: 收款 {receipt.receipt_number} 找不到 REF {ref.ref_number} 的金额")
                    error_count += 1
                    continue

                current_amount = Decimal(str(receipt.amount))

                # 检查是否需要修复
                if current_amount == correct_amount:
                    skip_count += 1
                    continue

                print(f"\n  收款 {receipt.receipt_number} (ID:{receipt.id})")
                print(f"    关联 REF: {ref.ref_number}")
                print(f"    当前金额: {current_amount}")
                print(f"    正确金额: {correct_amount}")
                print(f"    包含的 REF: {extra_info.get('ref_numbers', [])}")

                if not dry_run:
                    receipt.amount = correct_amount
                    db.session.add(receipt)

                fix_count += 1

            except json.JSONDecodeError as e:
                print(f"\n  错误: 收款 {receipt.receipt_number} extra_info 解析失败: {e}")
                error_count += 1
            except Exception as e:
                print(f"\n  错误: 收款 {receipt.receipt_number} 处理失败: {e}")
                error_count += 1

        print("\n" + "=" * 70)

        if not dry_run:
            try:
                db.session.commit()
                print(f"  修复完成！")
            except Exception as e:
                db.session.rollback()
                print(f"\n保存失败: {str(e)}")
                import traceback
                traceback.print_exc()

        print(f"\n统计:")
        print(f"  需要修复: {fix_count} 条")
        print(f"  无需修复: {skip_count} 条")
        print(f"  处理错误: {error_count} 条")

        if dry_run and fix_count > 0:
            print(f"\n确认修复请添加 --confirm 参数:")
            print(f"  python scripts/fix_receipt_multi_ref_amount.py --confirm")


if __name__ == '__main__':
    main()
