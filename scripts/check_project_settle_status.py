# -*- coding: utf-8 -*-
"""
检查项目结算状态脚本

可结算条件：
1. 所有 REF 都关联了 InvoiceItem（已开票）
2. 所有 EO 的 status == 'paid'（供应商已付款）
3. Balance = 0（客户款项已收齐：total_selling - total_received ≈ 0）

运行方式: python scripts/check_project_settle_status.py
可选参数:
  --hid H1234      检查指定项目
  --fix            自动修复（将满足条件的项目标记为可结算状态）
"""

import sys
import os
import argparse
from datetime import datetime
from decimal import Decimal

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
from App_new.business.projects.models.receipt import ProjectReceipt


def check_project_can_settle(project):
    """
    检查单个项目是否满足可结算条件

    返回: (can_settle, details)
    """
    details = {
        'hid': project.hid,
        'desc': project.desc[:40] if project.desc else '-',
        'is_settled': project.is_settled,
        'ref_count': 0,
        'invoiced_ref_count': 0,
        'eo_count': 0,
        'paid_eo_count': 0,
        'total_selling': Decimal('0'),
        'total_received': Decimal('0'),
        'balance': Decimal('0'),
        'all_refs_invoiced': False,
        'all_eos_paid': True,
        'balance_cleared': False,
        'can_settle': False,
        'reasons': []
    }

    # 获取项目的所有 REF
    refs = ProjectRef.query.filter_by(header_id=project.id).all()
    details['ref_count'] = len(refs)

    if not refs:
        details['reasons'].append('无REF记录')
        return False, details

    # 计算总销售金额
    total_selling = sum(Decimal(str(ref.selling_price or 0)) for ref in refs)
    details['total_selling'] = total_selling

    # 获取有 InvoiceItem 的 REF 数量
    ref_ids = [ref.id for ref in refs]
    invoiced_ref_ids = db.session.query(db.distinct(InvoiceItem.ref_id)).filter(
        InvoiceItem.ref_id.in_(ref_ids)
    ).all()
    invoiced_ref_count = len(invoiced_ref_ids)
    details['invoiced_ref_count'] = invoiced_ref_count

    # 条件1: 所有 REF 都有 InvoiceItem
    all_refs_invoiced = len(refs) == invoiced_ref_count
    details['all_refs_invoiced'] = all_refs_invoiced
    if not all_refs_invoiced:
        details['reasons'].append(f'REF未全部开票({invoiced_ref_count}/{len(refs)})')

    # 获取项目的所有 EO
    eos = ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).all() if ref_ids else []
    details['eo_count'] = len(eos)

    # 条件2: 所有 EO 的 status == 'paid'
    if eos:
        paid_eos = [eo for eo in eos if eo.status == 'paid']
        details['paid_eo_count'] = len(paid_eos)
        all_eos_paid = len(paid_eos) == len(eos)
        details['all_eos_paid'] = all_eos_paid
        if not all_eos_paid:
            unpaid_eos = [eo for eo in eos if eo.status != 'paid']
            details['reasons'].append(f'EO未全部付款({len(paid_eos)}/{len(eos)})')
            # 显示未付款的 EO 状态
            for eo in unpaid_eos[:3]:
                details['reasons'].append(f'  - {eo.eo_number}: status={eo.status}')
    else:
        details['all_eos_paid'] = True  # 没有 EO 视为满足条件

    # 条件3: Balance = 0
    # 获取已确认的收款总额
    receipts = ProjectReceipt.query.filter(
        ProjectReceipt.header_id == project.id,
        ProjectReceipt.status == 'confirmed'
    ).all()
    total_received = sum(Decimal(str(r.amount or 0)) for r in receipts)
    details['total_received'] = total_received

    balance = total_selling - total_received
    details['balance'] = balance
    balance_cleared = abs(balance) < Decimal('0.01')
    details['balance_cleared'] = balance_cleared
    if not balance_cleared:
        details['reasons'].append(f'余额未清({balance:.2f})')

    # 综合判断
    can_settle = all_refs_invoiced and details['all_eos_paid'] and balance_cleared
    details['can_settle'] = can_settle

    return can_settle, details


def check_single_project(hid):
    """检查单个项目"""
    project = ProjectHeader.query.filter_by(hid=hid).first()
    if not project:
        print(f"错误: 找不到项目 {hid}")
        return

    can_settle, details = check_project_can_settle(project)

    print(f"\n{'='*60}")
    print(f"项目: {details['hid']} - {details['desc']}")
    print(f"{'='*60}")
    print(f"当前状态: {'已结算' if details['is_settled'] else '未结算'}")
    print(f"\n【条件检查】")
    print(f"  1. REF开票: {details['invoiced_ref_count']}/{details['ref_count']} {'✓' if details['all_refs_invoiced'] else '✗'}")
    print(f"  2. EO付款: {details['paid_eo_count']}/{details['eo_count']} {'✓' if details['all_eos_paid'] else '✗'}")
    print(f"  3. 余额清零: {details['balance']:.2f} {'✓' if details['balance_cleared'] else '✗'}")
    print(f"\n【财务数据】")
    print(f"  销售总额: {details['total_selling']:.2f}")
    print(f"  已收款额: {details['total_received']:.2f}")
    print(f"  余额: {details['balance']:.2f}")
    print(f"\n【结论】")
    if can_settle:
        print(f"  ✓ 满足可结算条件")
    else:
        print(f"  ✗ 不满足可结算条件")
        print(f"  原因:")
        for reason in details['reasons']:
            print(f"    - {reason}")


def check_all_projects():
    """检查所有项目"""
    projects = ProjectHeader.query.all()

    total = len(projects)
    can_settle_list = []
    settled_list = []
    not_ready_list = []
    no_refs_count = 0

    print(f"开始检查 {total} 个项目的结算状态...")
    print("=" * 70)

    for project in projects:
        can_settle, details = check_project_can_settle(project)

        if details['ref_count'] == 0:
            no_refs_count += 1
            continue

        if project.is_settled:
            settled_list.append(details)
        elif can_settle:
            can_settle_list.append(details)
        else:
            not_ready_list.append(details)

    # 输出结果
    print(f"\n【已结算的项目】({len(settled_list)}个)")
    print("-" * 70)
    if settled_list:
        for item in settled_list[:10]:
            print(f"  {item['hid']}: {item['desc']}")
        if len(settled_list) > 10:
            print(f"  ... 还有 {len(settled_list) - 10} 个")
    else:
        print("  无")

    print(f"\n【可结算的项目】({len(can_settle_list)}个) - 满足所有条件")
    print("-" * 70)
    if can_settle_list:
        for item in can_settle_list:
            print(f"  {item['hid']}: {item['desc']}")
            print(f"         REF:{item['ref_count']} INV:{item['invoiced_ref_count']} EO:{item['eo_count']} PAY:{item['paid_eo_count']} BAL:{item['balance']:.2f}")
    else:
        print("  无")

    print(f"\n【不满足条件的项目】({len(not_ready_list)}个，显示前20个)")
    print("-" * 70)
    if not_ready_list:
        for item in not_ready_list[:20]:
            reasons = ', '.join([r for r in item['reasons'] if not r.startswith('  -')])
            print(f"  {item['hid']}: {reasons}")
        if len(not_ready_list) > 20:
            print(f"  ... 还有 {len(not_ready_list) - 20} 个")
    else:
        print("  无")

    print(f"\n{'='*70}")
    print(f"统计汇总:")
    print(f"  总项目数: {total}")
    print(f"  无REF项目: {no_refs_count}")
    print(f"  已结算: {len(settled_list)}")
    print(f"  可结算: {len(can_settle_list)}")
    print(f"  不满足条件: {len(not_ready_list)}")

    return can_settle_list


def main():
    parser = argparse.ArgumentParser(description='检查项目结算状态')
    parser.add_argument('--hid', type=str, help='检查指定项目编号')
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        if args.hid:
            check_single_project(args.hid)
        else:
            check_all_projects()


if __name__ == '__main__':
    main()
