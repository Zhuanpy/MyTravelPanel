# -*- coding: utf-8 -*-
"""
将项目人员中出现3次以上的名字自动设置为常用旅客
- 按 member_name 分组，出现 >= 3 次的视为常用
- 取该名字信息最完整的一条记录作为常用旅客数据源
- 已存在于常用旅客表的名字自动跳过

运行方式: python scripts/20260328_auto_frequent_travelers.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project_member import ProjectMember
from App_new.business.projects.models.frequent_traveler import FrequentTraveler

app = create_app()

MIN_COUNT = 3  # 最少出现次数


def get_info_score(m):
    """计算一条记录的信息完整度评分，用于选择最佳数据源"""
    score = 0
    if m.title:
        score += 1
    if m.member_phone:
        score += 2
    if m.member_email:
        score += 2
    if m.id_number:
        score += 3
    if m.passport_issuing_country:
        score += 1
    if m.passport_expiry_date:
        score += 1
    if m.gender:
        score += 1
    if m.date_of_birth:
        score += 2
    if m.nationality:
        score += 1
    if m.airline_memberships:
        score += 2
    return score


with app.app_context():
    # 1. 查找出现 >= MIN_COUNT 次的名字
    from sqlalchemy import func
    frequent_names = db.session.query(
        ProjectMember.member_name,
        func.count(ProjectMember.id).label('cnt')
    ).group_by(
        ProjectMember.member_name
    ).having(
        func.count(ProjectMember.id) >= MIN_COUNT
    ).all()

    if not frequent_names:
        print(f'没有找到出现 {MIN_COUNT} 次以上的人员名字')
        sys.exit(0)

    print(f'找到 {len(frequent_names)} 个出现 {MIN_COUNT}+ 次的名字:\n')

    # 2. 获取已有的常用旅客名字，用于跳过
    existing_names = set(
        t.name for t in FrequentTraveler.query.with_entities(FrequentTraveler.name).all()
    )

    created = 0
    skipped = 0

    for name, count in frequent_names:
        if name in existing_names:
            print(f'  跳过: {name} (出现{count}次，已在常用旅客中)')
            skipped += 1
            continue

        # 3. 取该名字所有记录，按信息完整度排序，取最佳的一条
        members = ProjectMember.query.filter_by(member_name=name).all()
        best = max(members, key=get_info_score)

        # 4. 创建常用旅客
        traveler = FrequentTraveler(
            title=best.title,
            name=best.member_name,
            gender=best.gender,
            date_of_birth=best.date_of_birth,
            nationality=best.nationality,
            phone=best.member_phone,
            email=best.member_email,
            passport_number=best.id_number if best.id_number else None,
            passport_issuing_country=best.passport_issuing_country,
            passport_expiry_date=best.passport_expiry_date,
            airline_memberships=best.airline_memberships,
            remarks=f'自动导入：在项目人员中出现{count}次',
        )
        db.session.add(traveler)
        created += 1
        print(f'  新增: {best.title or ""} {name} (出现{count}次，信息评分{get_info_score(best)})')

    db.session.commit()
    print(f'\n完成！新增 {created} 条，跳过 {skipped} 条（已存在）')
