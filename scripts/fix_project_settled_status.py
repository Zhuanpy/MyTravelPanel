# -*- coding: utf-8 -*-
"""
修复项目结算状态脚本

可结算条件：
1. 所有 REF 的 payment_status == 'paid'（款项已收）
2. 所有 EO 的 status == 'paid'（供应商已付款）
3. 项目已生成 Invoice

运行方式: python scripts/fix_project_settled_status.py
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.invoice import ProjectInvoice

def fix_settled_status():
    """修复所有项目的结算状态"""
    app = create_app()

    with app.app_context():
        # 获取所有项目
        projects = ProjectHeader.query.all()

        total = len(projects)
        can_settle_list = []  # 可结算的项目
        reset_list = []  # 被重置的项目
        not_ready_list = []  # 不满足条件的项目
        no_refs = 0

        print(f"开始检查 {total} 个项目的结算状态...")
        print("=" * 60)

        for project in projects:
            # 获取项目的所有 REF
            refs = ProjectRef.query.filter_by(header_id=project.id).all()

            if not refs:
                no_refs += 1
                continue

            # 获取项目的所有 EO
            ref_ids = [ref.id for ref in refs]
            eos = ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).all() if ref_ids else []

            # 获取项目的 Invoice
            invoices = ProjectInvoice.query.filter_by(header_id=project.id).all()

            # 检查条件
            # 1. 所有 REF 款项已收（payment_status == 'paid'）
            all_refs_paid = all(ref.payment_status == 'paid' for ref in refs)
            unpaid_refs = [ref for ref in refs if ref.payment_status != 'paid']

            # 2. 所有 EO 已付款（status == 'paid'）
            all_eos_paid = all(eo.status == 'paid' for eo in eos) if eos else True
            unpaid_eos = [eo for eo in eos if eo.status != 'paid']

            # 3. 已生成 Invoice
            has_invoice = len(invoices) > 0

            # 判断是否可结算
            can_settle = all_refs_paid and all_eos_paid and has_invoice

            # 重置已结算的项目
            if project.is_settled:
                project.is_settled = False
                project.settled_at = None
                project.settled_by = None
                reset_list.append({
                    'hid': project.hid,
                    'desc': project.desc[:30] if project.desc else '-',
                    'can_settle': can_settle
                })

            # 记录可结算的项目
            if can_settle:
                can_settle_list.append({
                    'hid': project.hid,
                    'desc': project.desc[:30] if project.desc else '-',
                    'refs': len(refs),
                    'eos': len(eos),
                    'invoices': len(invoices)
                })
            elif refs:  # 有 REF 但不满足条件
                reasons = []
                if not all_refs_paid:
                    reasons.append(f"{len(unpaid_refs)}个REF未收款")
                if not all_eos_paid:
                    reasons.append(f"{len(unpaid_eos)}个EO未付")
                if not has_invoice:
                    reasons.append("无Invoice")

                if reasons:
                    not_ready_list.append({
                        'hid': project.hid,
                        'reason': ', '.join(reasons)
                    })

        # 提交更改
        db.session.commit()

        # 输出结果
        print("\n【已重置为未结算的项目】")
        print("-" * 60)
        if reset_list:
            for item in reset_list:
                status = "-> 可结算" if item['can_settle'] else "-> 待处理"
                print(f"  {item['hid']}: {item['desc']} {status}")
        else:
            print("  无")

        print("\n【可结算的项目】（满足所有条件）")
        print("-" * 60)
        if can_settle_list:
            for item in can_settle_list:
                print(f"  {item['hid']}: {item['desc']} (REF:{item['refs']}, EO:{item['eos']}, INV:{item['invoices']})")
        else:
            print("  无")

        print("\n【不满足条件的项目】（前20个）")
        print("-" * 60)
        if not_ready_list:
            for item in not_ready_list[:20]:
                print(f"  {item['hid']}: {item['reason']}")
            if len(not_ready_list) > 20:
                print(f"  ... 还有 {len(not_ready_list) - 20} 个")
        else:
            print("  无")

        print("\n" + "=" * 60)
        print(f"统计：")
        print(f"  总项目数: {total}")
        print(f"  无 REF 项目: {no_refs}")
        print(f"  重置项目数: {len(reset_list)}")
        print(f"  可结算项目: {len(can_settle_list)}")
        print(f"  不满足条件: {len(not_ready_list)}")

if __name__ == '__main__':
    fix_settled_status()
