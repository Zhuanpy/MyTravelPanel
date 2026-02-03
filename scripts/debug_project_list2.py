# -*- coding: utf-8 -*-
"""
调试项目列表 - 模拟登录用户权限过滤
"""
import sys
sys.path.insert(0, '/var/www/MyTravelPanel')

from app_new import app
app.app_context().push()

from App_new.business.projects.models.project import ProjectHeader
from App_new.exts import db
from App_new.auth.models.auth import AuthUser, UserProfile

print("=" * 60)
print("模拟不同用户的权限过滤")
print("=" * 60)

# 获取所有 staff 用户
staff_users = db.session.query(
    AuthUser.id, AuthUser.username, AuthUser.role_id, UserProfile.staff_level
).outerjoin(UserProfile, UserProfile.user_id == AuthUser.id).all()

print("\n所有用户:")
for uid, username, role_id, staff_level in staff_users:
    print(f"  ID: {uid}, Username: {username}, RoleID: {role_id}, StaffLevel: {staff_level}")

# 模拟每个用户的查询
for uid, username, role_id, staff_level in staff_users:
    print(f"\n{'='*60}")
    print(f"模拟用户: {username} (ID={uid}, StaffLevel={staff_level})")
    print("=" * 60)

    base_query = ProjectHeader.query.options(db.joinedload(ProjectHeader.company))

    # 获取角色名称
    from App_new.auth.models.auth import Role
    role = Role.query.get(role_id)
    role_name = role.name if role else None

    print(f"角色: {role_name}")

    # 模拟权限过滤逻辑（来自 project_list.py）
    if role_name == 'staff':
        level = staff_level or 1
        if level == 1:
            # 1级员工只能看自己的项目
            user = AuthUser.query.get(uid)
            user_profile = UserProfile.query.filter_by(user_id=uid).first()
            user_full_name = None
            if user_profile:
                first_name = user_profile.first_name or ''
                last_name = user_profile.last_name or ''
                user_full_name = f"{first_name} {last_name}".strip() or None

            print(f"  1级员工过滤: staff_id={uid} OR staff_name='{username}' OR staff_name='{user_full_name}'")

            if user_full_name and user_full_name != "未设置姓名":
                base_query = base_query.filter(
                    db.or_(
                        ProjectHeader.staff_id == uid,
                        ProjectHeader.staff_name == username,
                        ProjectHeader.staff_name == user_full_name
                    )
                )
            else:
                base_query = base_query.filter(
                    db.or_(
                        ProjectHeader.staff_id == uid,
                        ProjectHeader.staff_name == username
                    )
                )
        else:
            print(f"  2级或以上员工 - 无过滤")
    else:
        print(f"  非 staff 角色 ({role_name}) - 无过滤")

    # 排序并获取前10条
    base_query = base_query.order_by(
        db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
    )

    projects = base_query.limit(10).all()

    print(f"\n  查询结果 (前10条):")
    h1082_found = False
    for p in projects:
        marker = " <-- H1082" if p.hid == 'H1082' else ""
        print(f"    {p.hid}{marker}")
        if p.hid == 'H1082':
            h1082_found = True

    if not h1082_found:
        # 检查 H1082 是否在完整结果中
        all_hids = [p.hid for p in base_query.all()]
        if 'H1082' in all_hids:
            pos = all_hids.index('H1082') + 1
            print(f"\n  ⚠️ H1082 在第 {pos} 位 (可能被分页隐藏)")
        else:
            print(f"\n  ❌ H1082 不在该用户的查询结果中!")

print("\n\n调试完成!")
