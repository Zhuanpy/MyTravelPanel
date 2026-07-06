# -*- coding: utf-8 -*-
"""
预付账款对账诊断（只读，不改任何数据）

背景：批量付款页显示某供应商「可用预付余额」远高于航司账户真实余额
（例：系统显示 INDIGO 可用 1788.40，但真实账户只剩 333.4）。

原因方向：系统里预付余额有两套口径互相漂移——
  1) SupplierPrepayment.balance_amount：存储字段，每次用预付付款时手动扣减
  2) PrepaymentUsage 使用记录：confirmed 之和才是「真正消耗」
批量付款页显示的「可用」= ∑ balance_amount（+已选EO已有使用额）。
若有 INDIGO 的 EO 实际由航司预付账户扣款，但系统里走的是「银行付款」
(payment_source=bank)，则 balance_amount 不会减 → 系统高估可用余额。

本脚本把四组数字并排打出来，定位差额来源：
  A. 充值总额 / 系统余额(∑balance_amount) / 系统已耗(A充值-余额)
  B. 使用记录 confirmed / pending / reversed 之和
  C. 该供应商已付款 EO(is_paid & 非void) 的成本合计（= 真实应消耗）
  D. 付款记录 SupplierPayment 按来源(bank/prepayment/mixed)拆分

运行:
    python scripts/20260706_reconcile_indigo_prepayment.py                # 默认 INDIGO AIRLINE SINGAPORE
    python scripts/20260706_reconcile_indigo_prepayment.py --id 229
    python scripts/20260706_reconcile_indigo_prepayment.py --name "SCOOT"
"""
import sys
import os
import argparse
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment, PrepaymentUsage
from App_new.business.projects.models.supplier_payment import SupplierPayment
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.project import CustomerCompany


def m(v):
    return f'{float(v or 0):,.2f}'


def main():
    parser = argparse.ArgumentParser(description='预付账款对账诊断（只读）')
    parser.add_argument('--id', type=int, help='供应商 customer_companies.id')
    parser.add_argument('--name', type=str, help='供应商名称（模糊匹配）')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # ---- 定位供应商 ----
        if args.id:
            supplier = CustomerCompany.query.get(args.id)
        else:
            name = args.name or 'INDIGO AIRLINE SINGAPORE'
            supplier = CustomerCompany.query.filter(
                CustomerCompany.company_name.like(f'%{name}%')
            ).first()

        if not supplier:
            print(f'未找到供应商 (id={args.id}, name={args.name})')
            return

        sid = supplier.id
        print('=' * 78)
        print(f'供应商: {supplier.company_name}  (id={sid})')
        print('=' * 78)

        # ---- A. 预付记录 ----
        preps = SupplierPrepayment.query.filter_by(supplier_id=sid) \
            .order_by(SupplierPrepayment.payment_date.asc()).all()
        print(f'\n【A. 预付充值记录 SupplierPrepayment】{len(preps)} 条')
        print(f'  {"编号":<16} {"充值":>12} {"余额balance":>14} {"状态":<12} 日期')
        recharge_total = balance_total = Decimal('0')
        prep_ids = []
        for p in preps:
            prep_ids.append(p.id)
            recharge_total += Decimal(str(p.amount or 0))
            balance_total += Decimal(str(p.balance_amount or 0))
            print(f'  {p.prepayment_number:<16} {m(p.amount):>12} {m(p.balance_amount):>14} '
                  f'{p.status:<12} {p.payment_date}')
        print(f'  {"-"*60}')
        print(f'  充值总额           = {m(recharge_total)}')
        print(f'  系统余额∑balance   = {m(balance_total)}   ← 批量付款页「可用预付余额」的主来源')
        print(f'  系统已耗(充值-余额) = {m(recharge_total - balance_total)}')

        # ---- B. 使用记录 ----
        print(f'\n【B. 预付使用记录 PrepaymentUsage】')
        usage_by_status = {}
        if prep_ids:
            rows = db.session.query(
                PrepaymentUsage.status, db.func.sum(PrepaymentUsage.amount)
            ).filter(PrepaymentUsage.prepayment_id.in_(prep_ids)) \
             .group_by(PrepaymentUsage.status).all()
            usage_by_status = {s: Decimal(str(v or 0)) for s, v in rows}
        confirmed = usage_by_status.get('confirmed', Decimal('0'))
        pending = usage_by_status.get('pending', Decimal('0'))
        reversed_ = usage_by_status.get('reversed', Decimal('0'))
        print(f'  confirmed = {m(confirmed)}   pending = {m(pending)}   reversed = {m(reversed_)}')

        # ---- 一致性：每条预付 amount-(confirmed+pending) 是否 == balance_amount ----
        print(f'\n【一致性检查】balance_amount  vs  amount-(confirmed+pending)')
        drift_total = Decimal('0')
        for p in preps:
            c = db.session.query(db.func.sum(PrepaymentUsage.amount)).filter(
                PrepaymentUsage.prepayment_id == p.id,
                PrepaymentUsage.status == 'confirmed').scalar() or 0
            pd = db.session.query(db.func.sum(PrepaymentUsage.amount)).filter(
                PrepaymentUsage.prepayment_id == p.id,
                PrepaymentUsage.status == 'pending').scalar() or 0
            expected = Decimal(str(p.amount)) - Decimal(str(c)) - Decimal(str(pd))
            actual = Decimal(str(p.balance_amount))
            diff = actual - expected
            drift_total += diff
            flag = 'OK ' if abs(diff) < Decimal('0.01') else '*** '
            print(f'  {flag}{p.prepayment_number:<16} 余额={m(actual):>12} 期望={m(expected):>12} 差={m(diff):>10}')
        print(f'  两套口径累计差额 = {m(drift_total)}  (≠0 说明 balance_amount 与使用记录不一致)')

        # ---- C. 该供应商已付款 EO（真实应消耗）----
        ref_ids = [r.id for r in ProjectRef.query.filter_by(supplier_id=sid).all()]
        paid_eos = []
        if ref_ids:
            paid_eos = ProjectEO.query.filter(
                ProjectEO.ref_id.in_(ref_ids),
                ProjectEO.status == 'confirmed',
                ProjectEO.is_paid == True
            ).all()
        paid_cost_total = Decimal('0')
        for eo in paid_eos:
            amt = eo.pay_amount if eo.pay_amount is not None else (eo.ref.cost_price if eo.ref else 0)
            paid_cost_total += Decimal(str(amt or 0))
        print(f'\n【C. 已付款 EO（is_paid & status=confirmed）】{len(paid_eos)} 笔')
        print(f'  付款金额合计 = {m(paid_cost_total)}   ← 若这些全部由预付支付，应消耗这么多')

        # ---- D. 付款记录按来源拆分 ----
        pays = SupplierPayment.query.filter_by(supplier_id=sid).all()
        by_src = {}
        prepay_amt_total = Decimal('0')
        for pay in pays:
            by_src.setdefault(pay.payment_source, Decimal('0'))
            by_src[pay.payment_source] += Decimal(str(pay.total_amount or 0))
            prepay_amt_total += Decimal(str(pay.prepayment_amount or 0))
        print(f'\n【D. 付款记录 SupplierPayment】{len(pays)} 条，按来源:')
        for src, tot in by_src.items():
            print(f'  {src:<12} 合计 = {m(tot)}')
        print(f'  其中标注为预付支付 prepayment_amount 合计 = {m(prepay_amt_total)}')

        # ---- 结论 ----
        print('\n' + '=' * 78)
        print('【对账结论】')
        print(f'  系统显示可用(∑balance)      = {m(balance_total)}')
        print(f'  按使用记录应剩(充值-confirmed) = {m(recharge_total - confirmed)}')
        print(f'  按已付EO应剩(充值-已付EO成本) = {m(recharge_total - paid_cost_total)}   ← 最接近航司真实余额')
        print(f'  若真实账户余额=333.40，则未在预付里扣减的金额 ≈ {m(balance_total - Decimal("333.40"))}')
        print('\n  解读:')
        print('   - 若「按已付EO应剩」≈ 真实余额：说明有 EO 实际用预付支付，')
        print('     但系统里走了 bank 付款(见D的bank合计) → balance_amount 没扣，系统高估。')
        print('   - 若「两套口径累计差额」≠0：balance_amount 与使用记录本身就不一致，需重建。')
        print('\n(本脚本只读，未修改任何数据)')


if __name__ == '__main__':
    main()
