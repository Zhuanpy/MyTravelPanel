# -*- coding: utf-8 -*-
"""员工姓名相关的共用查询

这里刻意把两件事分开：

1. ``get_staff_options()`` —— 「谁可以被选为经办人」。只列在职（is_active）的
   staff/admin，用于新建/编辑表单和筛选下拉。
2. ``get_user_name_map()`` —— 「这个 user_id 叫什么名字」。覆盖全部用户，
   不过滤 is_active、也不过滤角色。

历史单据里存的是 operator_ids / salesperson_ids，员工离职停用后这些 id 还在。
如果拿第 1 种列表去查名字，离职员工就查不到，页面上会显示成 ``ID:23``
（结算单 SB-20260830-003 里的 Lily 就是这么来的）。
"""

from App_new.exts import db


def _display_name(username, first_name, last_name):
    """优先用 profile 的姓名，没有再退回 username"""
    full = f"{first_name or ''}{last_name or ''}".strip()
    return full or username or ''


def _staff_role_ids():
    from App_new.auth.models.auth import Role
    roles = Role.query.filter(Role.name.in_(['staff', 'admin'])).all()
    return [r.id for r in roles]


def get_staff_options():
    """在职员工列表，供下拉框使用，返回 [{'id':…, 'name':…, 'username':…}]"""
    from App_new.auth.models.auth import AuthUser, UserProfile

    role_ids = _staff_role_ids()
    if not role_ids:
        return []

    rows = db.session.query(
        AuthUser.id, AuthUser.username, UserProfile.first_name, UserProfile.last_name
    ).outerjoin(
        UserProfile, AuthUser.id == UserProfile.user_id
    ).filter(
        AuthUser.role_id.in_(role_ids),
        AuthUser.is_active == True
    ).all()

    return [{
        'id': r.id,
        'name': _display_name(r.username, r.first_name, r.last_name),
        'username': r.username,
    } for r in rows]


def get_user_name_map():
    """{user_id: 显示名} —— 全部用户，含已停用/离职的

    只用于展示历史记录里的姓名，不要拿它当"可选员工"列表。
    """
    from App_new.auth.models.auth import AuthUser, UserProfile

    rows = db.session.query(
        AuthUser.id, AuthUser.username, UserProfile.first_name, UserProfile.last_name
    ).outerjoin(
        UserProfile, AuthUser.id == UserProfile.user_id
    ).all()

    return {r.id: _display_name(r.username, r.first_name, r.last_name) for r in rows}


def resolve_staff_names(id_string, name_map, fallback=''):
    """把 "10,23" 这样的 id 串解析成 "ZHANGZHUAN, Lily"

    id 在 name_map 里找不到时（用户被真删了）才退回 ``ID:<id>``。
    id 串为空则用 fallback（项目上缓存的 *_names 字段）。
    """
    ids = [int(s.strip()) for s in (id_string or '').split(',') if s.strip().isdigit()]
    if not ids:
        return fallback or '-'
    return ', '.join(name_map.get(uid, f'ID:{uid}') for uid in ids)
