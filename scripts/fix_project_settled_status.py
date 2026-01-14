# -*- coding: utf-8 -*-
"""
修复项目结算状态脚本

检查每个项目的所有 REF 的 payment_status：
- 如果所有 REF 都是 'paid'，设置 is_settled = True
- 否则设置 is_settled = False

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
        updated_to_settled = 0
        updated_to_unsettled = 0
        no_refs = 0
        unchanged = 0

        print(f"开始检查 {total} 个项目的结算状态...")
        print("-" * 60)

        for project in projects:
            # 获取项目的所有 REF
            refs = ProjectRef.query.filter_by(header_id=project.id).all()

            if not refs:
                # 没有 REF 的项目，保持原状态
                no_refs += 1
                continue

            # 检查是否所有 REF 都是 paid
            all_paid = all(ref.payment_status == 'paid' for ref in refs)

            old_status = project.is_settled

            if all_paid and not project.is_settled:
                # 应该是已结算，但当前不是
                project.is_settled = True
                project.settled_at = datetime.utcnow()
                project.settled_by = 'system_fix'
                updated_to_settled += 1
                print(f"[已结算] {project.hid}: {len(refs)} 个 REF 全部已付款")

            elif not all_paid and project.is_settled:
                # 不应该是已结算，但当前是
                project.is_settled = False
                project.settled_at = None
                project.settled_by = None
                updated_to_unsettled += 1
                unpaid_count = sum(1 for ref in refs if ref.payment_status != 'paid')
                print(f"[未结算] {project.hid}: {unpaid_count}/{len(refs)} 个 REF 未付款")

            else:
                unchanged += 1

        # 提交更改
        db.session.commit()

        print("-" * 60)
        print(f"修复完成！")
        print(f"  总项目数: {total}")
        print(f"  更新为已结算: {updated_to_settled}")
        print(f"  更新为未结算: {updated_to_unsettled}")
        print(f"  无 REF 项目: {no_refs}")
        print(f"  状态正确无需更新: {unchanged}")

if __name__ == '__main__':
    fix_settled_status()
