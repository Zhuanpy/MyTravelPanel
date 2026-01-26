# -*- coding: utf-8 -*-
"""
修复空联系人字段

从项目人员名单 (ProjectMember) 获取联系人名字
填充到 ProjectHeader.contact 字段
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.project_member import ProjectMember
from App_new.business.projects.models.ref import ProjectRef
from App_new.shared.models.business_types import BusinessType

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
        print("修复空联系人字段脚本")
        print("=" * 60)
        print(f"模式: {'执行' if execute else '预览'}")
        print()

        # 获取机票业务类型
        flight_type = BusinessType.query.filter(
            db.or_(
                BusinessType.name == '机票',
                BusinessType.code == 'flight'
            )
        ).first()

        if not flight_type:
            print("错误：未找到机票业务类型")
            return

        # 查找所有机票REF对应的项目
        flight_refs = ProjectRef.query.filter_by(ref_type_id=flight_type.id).all()

        # 获取所有相关的 header_id
        header_ids = set(ref.header_id for ref in flight_refs)
        print(f"找到 {len(header_ids)} 个机票相关项目")

        # 查找联系人为空的项目
        empty_contact_headers = ProjectHeader.query.filter(
            ProjectHeader.id.in_(header_ids),
            db.or_(
                ProjectHeader.contact.is_(None),
                ProjectHeader.contact == '',
                ProjectHeader.contact == 'None'
            )
        ).all()

        print(f"其中 {len(empty_contact_headers)} 个项目联系人为空")

        updated = 0
        skipped = 0

        for header in empty_contact_headers:
            member_name = get_member_name(header.id)

            if not member_name:
                print(f"  {header.hid}: 项目人员名单为空，跳过")
                skipped += 1
                continue

            print(f"  {header.hid}: 空 -> {member_name}")

            if execute:
                header.contact = member_name
                updated += 1

        if execute:
            db.session.commit()

        print()
        print("=" * 60)
        print("统计结果")
        print("=" * 60)
        print(f"空联系人项目数: {len(empty_contact_headers)}")
        print(f"已更新: {updated}")
        print(f"跳过: {skipped}")

        if not execute:
            print()
            print("-" * 60)
            print("这是预览模式，未实际修改数据库")
            print("要执行修复，请运行: python scripts/20260126_fix_empty_contact.py --execute")


if __name__ == '__main__':
    execute_mode = '--execute' in sys.argv
    main(execute=execute_mode)
