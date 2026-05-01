# -*- coding: utf-8 -*-
"""
修复预付账款状态漂移
====================

背景：
某些预付账款记录由于历史代码路径（usage 冲销时只回退 balance_amount，
未同步 update_status），出现 status='consumed' 但 balance_amount > 0 的情况。
这会导致：
- /company/<id>/prepayments 接口按 status 过滤时漏掉这些记录
- 批量付款时供应商可用余额计算偏低

逻辑：
1. 找出 status 与 balance_amount 不一致的记录：
   - status='consumed' 但 balance_amount > 0  → 应为 partial_used 或 confirmed
   - status='confirmed' 但 balance_amount < amount → 应为 partial_used
   - status='partial_used' 但 balance_amount <= 0 → 应为 consumed
   - status='partial_used' 但 balance_amount == amount → 应为 confirmed
2. 调用 update_status() 修正

运行方式: python scripts/20260501_fix_prepayment_status_drift.py [--apply]
默认 dry-run 只打印待修复列表；加 --apply 才真正写库。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def main():
    apply_changes = '--apply' in sys.argv

    app = create_app()
    with app.app_context():
        from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment

        # 查询所有 confirmed/partial_used/consumed 的记录
        prepayments = SupplierPrepayment.query.filter(
            SupplierPrepayment.status.in_(['confirmed', 'partial_used', 'consumed'])
        ).all()

        drift_records = []
        for p in prepayments:
            # 推算应有状态
            if p.balance_amount <= 0:
                expected = 'consumed'
            elif p.balance_amount < p.amount:
                expected = 'partial_used'
            else:  # balance_amount >= amount（== amount，> amount 是异常但归为 confirmed）
                expected = 'confirmed'

            if p.status != expected:
                drift_records.append((p, expected))

        print('=' * 100)
        print(f'扫描完毕：共 {len(prepayments)} 条记录，发现 {len(drift_records)} 条状态漂移')
        print('=' * 100)

        if not drift_records:
            print('没有需要修复的记录。')
            return

        for p, expected in drift_records:
            supplier_name = p.supplier.company_name if p.supplier else '(无供应商)'
            print(
                f'  ID={p.id:>5} | {p.prepayment_number} | {supplier_name[:35]:<35} | '
                f'充值={p.amount} | 余额={p.balance_amount} | '
                f'当前状态={p.status} → 应为={expected}'
            )

        if not apply_changes:
            print('\n[DRY-RUN] 仅预览，未修改数据库。加 --apply 执行修复。')
            return

        print('\n开始修复...')
        for p, expected in drift_records:
            p.status = expected
        db.session.commit()
        print(f'完成：已修复 {len(drift_records)} 条记录。')


if __name__ == '__main__':
    main()
