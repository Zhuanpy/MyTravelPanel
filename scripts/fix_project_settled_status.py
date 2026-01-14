# -*- coding: utf-8 -*-
"""
修复项目结算状态脚本

功能：
1. 重置被错误设置为"已结算"的项目（如果不是所有 REF 都已付款）
2. 报告哪些项目是"可结算"的（所有 REF 已付款但未结算）

注意：此脚本不会自动将项目设为"已结算"，只会重置错误的状态

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

def fix_settled_status():
    """修复所有项目的结算状态"""
    app = create_app()

    with app.app_context():
        # 获取所有项目
        projects = ProjectHeader.query.all()

        total = len(projects)
        can_settle_list = []  # 可结算的项目
        reset_list = []  # 被重置的项目
        no_refs = 0

        print(f"开始检查 {total} 个项目的结算状态...")
        print("=" * 60)

        for project in projects:
            # 获取项目的所有 REF
            refs = ProjectRef.query.filter_by(header_id=project.id).all()

            if not refs:
                no_refs += 1
                continue

            # 检查是否所有 REF 都是 paid
            all_paid = all(ref.payment_status == 'paid' for ref in refs)
            unpaid_count = sum(1 for ref in refs if ref.payment_status != 'paid')

            # 重置所有已结算的项目为未结算
            if project.is_settled:
                project.is_settled = False
                project.settled_at = None
                project.settled_by = None
                reset_list.append({
                    'hid': project.hid,
                    'desc': project.desc[:30] if project.desc else '-',
                    'unpaid_count': unpaid_count,
                    'total_refs': len(refs),
                    'all_paid': all_paid
                })

            # 记录可结算的项目（所有 REF 都已付款但未结算）
            if not project.is_settled and all_paid:
                can_settle_list.append({
                    'hid': project.hid,
                    'desc': project.desc[:30] if project.desc else '-',
                    'total_refs': len(refs)
                })

        # 提交更改
        db.session.commit()

        # 输出结果
        print("\n【已重置为未结算的项目】（原本是已结算）")
        print("-" * 60)
        if reset_list:
            for item in reset_list:
                status = "可结算" if item['all_paid'] else f"{item['unpaid_count']}/{item['total_refs']} 未付款"
                print(f"  {item['hid']}: {item['desc']} -> {status}")
        else:
            print("  无")

        print("\n【可结算的项目】（所有款项已收，可手动结算）")
        print("-" * 60)
        if can_settle_list:
            for item in can_settle_list:
                print(f"  {item['hid']}: {item['desc']} ({item['total_refs']} 个 REF)")
        else:
            print("  无")

        print("\n" + "=" * 60)
        print(f"统计：")
        print(f"  总项目数: {total}")
        print(f"  无 REF 项目: {no_refs}")
        print(f"  重置为未结算: {len(reset_list)}")
        print(f"  可结算项目: {len(can_settle_list)}")

if __name__ == '__main__':
    fix_settled_status()
