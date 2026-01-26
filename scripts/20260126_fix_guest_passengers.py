# -*- coding: utf-8 -*-
"""
修复乘客名为 Guest 的记录

从项目人员名单 (ProjectMember) 获取正确的乘客名
优先级：
1. is_leader=True 的人员
2. 第一个人员
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.flight.models.flight import ProjectFlightPassenger
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.project_member import ProjectMember

app = create_app()


def get_member_name(header_id):
    """
    从项目人员名单获取名字
    优先级：leader > 第一个人员
    """
    # 先找 leader
    leader = ProjectMember.query.filter_by(
        header_id=header_id,
        is_leader=True
    ).first()

    if leader and leader.member_name:
        return leader.member_name

    # 找第一个人员
    first_member = ProjectMember.query.filter_by(
        header_id=header_id
    ).order_by(ProjectMember.id).first()

    if first_member and first_member.member_name:
        return first_member.member_name

    return None


def main(execute=False):
    with app.app_context():
        print("=" * 60)
        print("修复 Guest 乘客名脚本")
        print("=" * 60)
        print(f"模式: {'执行' if execute else '预览'}")
        print()

        # 查找所有名为 Guest 的乘客
        guest_passengers = ProjectFlightPassenger.query.filter(
            ProjectFlightPassenger.name == 'Guest'
        ).all()

        print(f"找到 {len(guest_passengers)} 个 Guest 乘客记录")

        updated = 0
        skipped = 0

        for passenger in guest_passengers:
            # 获取关联的 REF
            ref = ProjectRef.query.get(passenger.ref_id)
            if not ref:
                print(f"  乘客 ID {passenger.id}: 找不到关联的 REF")
                skipped += 1
                continue

            # 从项目人员名单获取名字
            member_name = get_member_name(ref.header_id)

            if not member_name:
                print(f"  REF {ref.ref_number}: 项目人员名单为空")
                skipped += 1
                continue

            print(f"  REF {ref.ref_number}: Guest -> {member_name}")

            if execute:
                passenger.name = member_name
                updated += 1

        if execute:
            db.session.commit()

        print()
        print("=" * 60)
        print("统计结果")
        print("=" * 60)
        print(f"Guest 乘客总数: {len(guest_passengers)}")
        print(f"已更新: {updated}")
        print(f"跳过: {skipped}")

        if not execute:
            print()
            print("-" * 60)
            print("这是预览模式，未实际修改数据库")
            print("要执行修复，请运行: python scripts/20260126_fix_guest_passengers.py --execute")


if __name__ == '__main__':
    execute_mode = '--execute' in sys.argv
    main(execute=execute_mode)
