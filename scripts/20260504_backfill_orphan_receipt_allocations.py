# -*- coding: utf-8 -*-
"""
回填"项目级收款 → 发票分配"的孤儿数据
====================================

背景：
某些路径（典型如对账模块的"认领银行交易为收款"）创建 ProjectReceipt 时
设置了 header_id 但 ref_id=NULL 且没有同步建 ReceiptInvoiceAllocation。
结果：钱已收到、project_receipts 有记录，但对应 invoice 的 paid_amount 一直是 0，
列表里继续显示 unpaid。

逻辑：
1. 找出所有 status=confirmed、ref_id IS NULL、且没有 allocation 的 receipt
2. 对每条 receipt：
   - 拉出该 project 下 status != cancelled、payment_status in (unpaid, partial_paid) 的 invoice
   - 按 invoice_date asc / id asc FIFO 把 receipt.amount 分配过去
   - 写 ReceiptInvoiceAllocation + 更新 invoice.paid_amount / payment_status
3. 余额情况：
   - receipt.amount <= 总未付 → 完全消化
   - receipt.amount  > 总未付 → 仅分配到等于"总未付"，剩余打印警告（不会自动建 invoice）
4. 跳过：项目下没有候选 invoice（可能是数据迁移中间态，需要人工核对）

运行方式:
  python scripts/20260504_backfill_orphan_receipt_allocations.py             # dry-run
  python scripts/20260504_backfill_orphan_receipt_allocations.py --apply     # 真正写库
  python scripts/20260504_backfill_orphan_receipt_allocations.py --apply --receipt-id 100   # 仅修复单条
"""
import sys
import os
from decimal import Decimal

# Windows 终端默认 GBK，强制 UTF-8 避免特殊字符崩溃
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, Exception):
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def parse_args():
    apply = '--apply' in sys.argv
    only_id = None
    if '--receipt-id' in sys.argv:
        idx = sys.argv.index('--receipt-id')
        if idx + 1 < len(sys.argv):
            only_id = int(sys.argv[idx + 1])
    return apply, only_id


def main():
    apply_changes, only_id = parse_args()

    app = create_app()
    with app.app_context():
        from App_new.business.projects.models.receipt import (
            ProjectReceipt, ReceiptInvoiceAllocation
        )
        from App_new.business.projects.models.invoice import ProjectInvoice
        from App_new.business.projects.models.project import ProjectHeader

        # 1) 找出所有孤儿 receipt
        q = db.session.query(ProjectReceipt).filter(
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id.is_(None),
            ~ProjectReceipt.id.in_(
                db.session.query(ReceiptInvoiceAllocation.receipt_id).distinct()
            )
        )
        if only_id is not None:
            q = q.filter(ProjectReceipt.id == only_id)

        orphans = q.order_by(ProjectReceipt.payment_date.asc(), ProjectReceipt.id.asc()).all()

        print('=' * 100)
        print(f'扫描完毕：共找到 {len(orphans)} 条孤儿 receipt')
        if not apply_changes:
            print('[DRY-RUN] 仅打印计划，未写库。加 --apply 执行修复。')
        print('=' * 100)

        if not orphans:
            print('没有需要修复的记录。')
            return

        fixed = 0
        skipped_no_invoice = 0
        partial_excess = 0

        for r in orphans:
            header = ProjectHeader.query.get(r.header_id)
            project_hid = header.hid if header else f'(header_id={r.header_id})'

            # 2) 候选 invoice：未付 / 部分付，FIFO（invoice_date asc, id asc）
            candidates = ProjectInvoice.query.filter(
                ProjectInvoice.header_id == r.header_id,
                ProjectInvoice.status != 'cancelled',
                ProjectInvoice.payment_status.in_(['unpaid', 'partial_paid'])
            ).order_by(ProjectInvoice.invoice_date.asc(), ProjectInvoice.id.asc()).all()

            if not candidates:
                print(f'  [SKIP] receipt {r.id} {r.receipt_number} | {project_hid} | {r.amount} '
                      f'→ 该项目无未付 invoice，请人工核对')
                skipped_no_invoice += 1
                continue

            # 3) FIFO 分配
            remaining = Decimal(str(r.amount))
            plan = []  # list of (invoice_id, invoice_number, alloc_amt, before_paid, after_paid, after_status)
            for inv in candidates:
                if remaining <= 0:
                    break
                inv_unpaid = Decimal(str(inv.amount or 0)) - Decimal(str(inv.paid_amount or 0))
                if inv_unpaid <= 0:
                    continue
                alloc = min(remaining, inv_unpaid)
                before_paid = Decimal(str(inv.paid_amount or 0))
                after_paid = before_paid + alloc
                after_status = (
                    'paid' if after_paid >= Decimal(str(inv.amount or 0))
                    else 'partial_paid'
                )
                plan.append((inv.id, inv.invoice_number, alloc, before_paid, after_paid, after_status))
                remaining -= alloc

            if not plan:
                print(f'  [SKIP] receipt {r.id} {r.receipt_number} | {project_hid} '
                      f'→ 候选 invoice 都已付清，请人工核对')
                skipped_no_invoice += 1
                continue

            # 打印计划
            allocated_total = sum(p[2] for p in plan)
            tag = ''
            if remaining > 0:
                tag = f' ⚠ 多余 {remaining}（receipt 大于该项目总未付，不会自动新建 invoice）'
                partial_excess += 1
            print(f'  receipt {r.id:>4} {r.receipt_number} | {project_hid:<8} '
                  f'| {r.amount} → 分配 {allocated_total}{tag}')
            for (inv_id, inv_no, alloc, before, after, st) in plan:
                print(f'      -> invoice {inv_id:>4} {inv_no:<10} +{alloc} '
                      f'(paid {before} -> {after}, status -> {st})')

            # 4) 真正写库
            if apply_changes:
                for (inv_id, inv_no, alloc, _b, after_paid, after_status) in plan:
                    db.session.add(ReceiptInvoiceAllocation(
                        receipt_id=r.id,
                        invoice_id=inv_id,
                        allocated_amount=alloc
                    ))
                    inv = ProjectInvoice.query.get(inv_id)
                    inv.paid_amount = after_paid
                    inv.payment_status = after_status
                fixed += 1

        if apply_changes:
            db.session.commit()
            print(f'\n完成：修复 {fixed} 条，跳过 {skipped_no_invoice} 条无候选 invoice')
            if partial_excess:
                print(f'⚠ 其中 {partial_excess} 条 receipt 金额大于项目总未付，已只分配到等于总未付的部分，剩余请人工核对')
        else:
            print(f'\n[DRY-RUN] 计划修复 {len(orphans) - skipped_no_invoice} 条，'
                  f'跳过 {skipped_no_invoice} 条无候选 invoice')
            if partial_excess:
                print(f'⚠ 其中 {partial_excess} 条 receipt 金额大于项目总未付，'
                      f'apply 后会只分配到等于总未付的部分')
            print('确认无误后请加 --apply 执行。')


if __name__ == '__main__':
    main()
