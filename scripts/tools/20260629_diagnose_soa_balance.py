"""
SOA 余额对账诊断(只读,不修改任何数据)

用途: 排查"项目详情 Balance=0 但 SOA 仍有余额"这类两套口径对不上的情况。
对照打印一个项目的:发票(amount / paid_amount / unpaid)、REF(销售价 / 实收 / 未付)、
收据(REF级 / 项目级)、收款-发票分配记录。

运行方式:
    python scripts/tools/20260629_diagnose_soa_balance.py H491
    python scripts/tools/20260629_diagnose_soa_balance.py --id 1736
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.invoice import ProjectInvoice
from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation


def money(v):
    return f'{float(v or 0):.2f}'


def main():
    args = sys.argv[1:]
    if not args:
        print('用法: python scripts/tools/20260629_diagnose_soa_balance.py <HID>  或  --id <project_id>')
        return

    app = create_app()
    with app.app_context():
        # 定位项目
        if args[0] == '--id' and len(args) > 1:
            header = ProjectHeader.query.get(int(args[1]))
        else:
            header = ProjectHeader.query.filter_by(hid=args[0]).first()

        if not header:
            print(f'未找到项目: {args}')
            return

        cur = header.currency or 'SGD'
        print('=' * 70)
        print(f'项目 #{header.id}  HID={header.hid}  {header.desc or ""}')
        print('=' * 70)

        refs = ProjectRef.query.filter_by(header_id=header.id).all()
        invoices = ProjectInvoice.query.filter_by(header_id=header.id).all()

        # ---- 发票 ----
        print('\n【发票 ProjectInvoice】(SOA 用 amount - paid_amount)')
        inv_amount_total = inv_paid_total = inv_unpaid_total = 0.0
        for inv in invoices:
            amount = float(inv.amount or 0)
            paid = float(inv.paid_amount or 0)
            unpaid = amount - paid
            if inv.status != 'cancelled':
                inv_amount_total += amount
                inv_paid_total += paid
                inv_unpaid_total += unpaid
            ref_ids = inv.ref_ids
            print(f'  INV#{inv.id} {inv.invoice_number or "-"} status={inv.status} pstatus={inv.payment_status} '
                  f'amount={money(amount)} paid={money(paid)} unpaid={money(unpaid)} ref_ids={ref_ids}')
        print(f'  -> 非取消发票合计: amount={money(inv_amount_total)} paid={money(inv_paid_total)} '
              f'unpaid(SOA口径)={money(inv_unpaid_total)} {cur}')

        # ---- REF ----
        print('\n【REF ProjectRef】(详情页用 销售价 - 实收, max(0,..))')
        ref_sell_total = ref_recv_total = ref_unpaid_total = 0.0
        for r in refs:
            sell = float(r.selling_price or 0)
            recv = ProjectReceipt.get_ref_total_received(r.id, header.id)
            unpaid = r.unpaid_amount  # max(0, sell-recv)
            ref_sell_total += sell
            ref_recv_total += recv
            ref_unpaid_total += unpaid
            print(f'  REF#{r.id} selling={money(sell)} received={money(recv)} '
                  f'unpaid(详情口径)={money(unpaid)} pstatus={r.payment_status}')
        print(f'  -> 合计: selling={money(ref_sell_total)} received={money(ref_recv_total)} '
              f'unpaid(详情口径)={money(ref_unpaid_total)} {cur}')

        # ---- 收据 ----
        print('\n【收据 ProjectReceipt】(本项目)')
        receipts = ProjectReceipt.query.filter_by(header_id=header.id).all()
        recv_confirmed = 0.0
        for rc in receipts:
            level = f'REF#{rc.ref_id}' if rc.ref_id else '项目级(ref_id=None)'
            if rc.status == 'confirmed':
                recv_confirmed += float(rc.amount or 0)
            print(f'  RC#{rc.id} {rc.receipt_number or "-"} {level} amount={money(rc.amount)} '
                  f'status={rc.status} invoice_id={rc.invoice_id} date={rc.payment_date}')
        print(f'  -> confirmed 收据合计: {money(recv_confirmed)} {cur}')

        # ---- 分配记录 ----
        print('\n【收款-发票分配 ReceiptInvoiceAllocation】(决定 invoice.paid_amount)')
        inv_ids = [inv.id for inv in invoices]
        if inv_ids:
            allocs = ReceiptInvoiceAllocation.query.filter(
                ReceiptInvoiceAllocation.invoice_id.in_(inv_ids)
            ).all()
            if not allocs:
                print('  (无分配记录) —— 若收款只记在 REF 级而没有分配到发票，'
                      'invoice.paid_amount 不会被这些收款抬高')
            alloc_total = 0.0
            for a in allocs:
                alloc_total += float(a.allocated_amount or 0)
                print(f'  ALLOC#{a.id} receipt#{a.receipt_id} -> invoice#{a.invoice_id} '
                      f'allocated={money(a.allocated_amount)}')
            print(f'  -> 分配合计: {money(alloc_total)} {cur}')

        # ---- 结论提示 ----
        print('\n【对照结论】')
        print(f'  发票口径未付(SOA)   = {money(inv_unpaid_total)} {cur}')
        print(f'  REF口径未付(详情)   = {money(ref_unpaid_total)} {cur}')
        diff = inv_unpaid_total - ref_unpaid_total
        print(f'  差额                = {money(diff)} {cur}')
        if abs(inv_amount_total - ref_sell_total) > 0.001:
            print(f'  ⚠ 发票金额合计({money(inv_amount_total)}) ≠ REF销售合计({money(ref_sell_total)})，'
                  f'差 {money(inv_amount_total - ref_sell_total)} → 可能是「成因1: 发票比REF多/少开」')
        if abs(inv_paid_total - recv_confirmed) > 0.001:
            print(f'  ⚠ 发票paid合计({money(inv_paid_total)}) ≠ confirmed收据合计({money(recv_confirmed)})，'
                  f'差 {money(recv_confirmed - inv_paid_total)} → 可能是「成因2: 收款未同步到发票paid_amount」')
        print('\n(本脚本只读，未修改任何数据)')


if __name__ == '__main__':
    main()
