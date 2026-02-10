# -*- coding: utf-8 -*-
"""
同步 project_headers 的 operator_ids / salesperson_ids

问题：
- 老记录只有 operator_names / salesperson_names（文本），没有对应的 ID
- Athina 导入只写 names 不写 ids
- 名字格式不统一（大小写、空格差异）

本脚本：
1. 从 auth_users + user_profiles 构建多种格式的姓名 → ID 映射
2. 遍历所有 project_headers，根据 operator_names 匹配补全 operator_ids
3. 同理处理 salesperson_names → salesperson_ids
4. 对已有 ids 的记录，重新同步缓存的 names 为标准格式
5. 无法匹配的名字自动创建员工账号（is_active=True, is_verified=False），可在筛选下拉框中出现，后续在后台统一处理

运行方式: python scripts/20260210_sync_operator_salesperson_ids.py
加 --dry-run 参数只预览不修改: python scripts/20260210_sync_operator_salesperson_ids.py --dry-run
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def build_name_to_id_map():
    """
    构建多种格式的姓名 → ID 映射（全部小写作为 key）
    映射策略：
    - username
    - first_name + last_name（无空格）
    - first_name + ' ' + last_name
    - first_name（如果 last_name 为空）
    - last_name（如果 first_name 为空）
    """
    rows = db.session.execute(text(
        "SELECT au.id, au.username, up.first_name, up.last_name "
        "FROM auth_users au "
        "LEFT JOIN user_profiles up ON au.id = up.user_id"
    )).fetchall()

    name_map = {}  # lowercase name → user_id
    id_to_display = {}  # user_id → 标准显示名

    for uid, username, first_name, last_name in rows:
        first_name = (first_name or '').strip()
        last_name = (last_name or '').strip()
        username = (username or '').strip()

        # 确定标准显示名
        if first_name or last_name:
            display_name = f"{first_name}{last_name}".strip()
        else:
            display_name = username
        id_to_display[uid] = display_name

        # 注册多种匹配格式（全部小写化）
        candidates = set()
        if username:
            candidates.add(username.lower())
        if first_name and last_name:
            candidates.add(f"{first_name}{last_name}".lower())
            candidates.add(f"{first_name} {last_name}".lower())
            candidates.add(f"{last_name}{first_name}".lower())
            candidates.add(f"{last_name} {first_name}".lower())
        if first_name:
            candidates.add(first_name.lower())
        if last_name:
            candidates.add(last_name.lower())

        for c in candidates:
            if c and c not in name_map:
                name_map[c] = uid

    return name_map, id_to_display


def resolve_name_to_id(name, name_map):
    """尝试将单个名字匹配到用户 ID"""
    if not name:
        return None
    name = name.strip()
    if not name:
        return None

    # 策略1：完全匹配（小写）
    key = name.lower()
    if key in name_map:
        return name_map[key]

    # 策略2：去掉所有空格后匹配
    key_no_space = key.replace(' ', '')
    if key_no_space in name_map:
        return name_map[key_no_space]

    return None


def create_placeholder_staff(name, staff_role_id, name_map, id_to_display, dry_run=False):
    """
    为无法匹配的名字创建一个未激活的员工账号
    返回新用户的 (user_id, display_name)
    """
    # 生成 username：小写 + 去空格
    username = name.strip().lower().replace(' ', '_')

    # 检查 username 是否已存在（可能之前创建过）
    existing = db.session.execute(text(
        "SELECT id FROM auth_users WHERE username = :u"
    ), {'u': username}).fetchone()
    if existing:
        uid = existing[0]
        display = id_to_display.get(uid, name.strip())
        return uid, display

    if dry_run:
        print(f"    [dry-run] 将创建员工: username='{username}', first_name='{name.strip()}'")
        return None, name.strip()

    # 创建 AuthUser（is_active=True 以便出现在筛选下拉框，is_verified=False 标记为待处理）
    from werkzeug.security import generate_password_hash
    import secrets
    random_pwd = secrets.token_urlsafe(16)

    db.session.execute(text(
        "INSERT INTO auth_users (username, email, password_hash, role_id, is_active, is_verified, created_at) "
        "VALUES (:username, :email, :pwd_hash, :role_id, 1, 0, NOW())"
    ), {
        'username': username,
        'email': f"{username}@placeholder.local",
        'pwd_hash': generate_password_hash(random_pwd),
        'role_id': staff_role_id,
    })
    db.session.flush()

    # 获取新创建的用户 ID
    new_user = db.session.execute(text(
        "SELECT id FROM auth_users WHERE username = :u"
    ), {'u': username}).fetchone()
    uid = new_user[0]

    # 创建 UserProfile
    display_name = name.strip().title()  # 首字母大写作为标准格式
    db.session.execute(text(
        "INSERT INTO user_profiles (user_id, first_name, created_at, updated_at) "
        "VALUES (:uid, :fname, NOW(), NOW())"
    ), {'uid': uid, 'fname': display_name})

    # 更新映射缓存
    id_to_display[uid] = display_name
    key = name.strip().lower()
    name_map[key] = uid
    key_no_space = key.replace(' ', '')
    if key_no_space != key:
        name_map[key_no_space] = uid

    print(f"    已创建员工: ID={uid}, username='{username}', name='{display_name}' (待验证)")
    return uid, display_name


def sync_operator_salesperson(dry_run=False):
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("同步 operator_ids / salesperson_ids")
        if dry_run:
            print("【预览模式】不会修改数据库")
        print("=" * 60)

        # 第1步：构建姓名映射
        print("\n--- 第1步：构建姓名 → ID 映射 ---")
        name_map, id_to_display = build_name_to_id_map()
        print(f"  已注册 {len(name_map)} 个名字变体，{len(id_to_display)} 个用户")

        # 获取 staff 角色 ID（用于创建占位员工）
        staff_role = db.session.execute(text(
            "SELECT id FROM roles WHERE name = 'staff'"
        )).fetchone()
        staff_role_id = staff_role[0] if staff_role else 1

        # 第2步：查询所有需要处理的 project_headers
        print("\n--- 第2步：扫描 project_headers ---")
        rows = db.session.execute(text(
            "SELECT id, hid, operator_ids, operator_names, "
            "       salesperson_ids, salesperson_names, "
            "       staff_id, staff_name "
            "FROM project_headers"
        )).fetchall()
        print(f"  共 {len(rows)} 条记录")

        # 统计
        stats = {
            'op_ids_filled': 0,      # 补全了 operator_ids
            'sp_ids_filled': 0,      # 补全了 salesperson_ids
            'op_names_synced': 0,    # 同步了 operator_names
            'sp_names_synced': 0,    # 同步了 salesperson_names
            'staff_id_fixed': 0,     # 修复了 staff_id
            'staff_created': set(),  # 自动创建的员工名字
        }

        # 收集所有无法匹配的名字（先扫描一遍，包括 staff_name）
        unmatched_names = set()
        for row in rows:
            pid, hid, op_ids_str, op_names_str, sp_ids_str, sp_names_str, s_id, s_name = row
            # staff_name 无法匹配且 staff_id 为空
            if not s_id and s_name and s_name.strip():
                if not resolve_name_to_id(s_name, name_map):
                    unmatched_names.add(s_name.strip())
            if not op_ids_str and op_names_str:
                for name in op_names_str.split(','):
                    name = name.strip()
                    if name and not resolve_name_to_id(name, name_map):
                        unmatched_names.add(name)
            if not sp_ids_str and sp_names_str:
                for name in sp_names_str.split(','):
                    name = name.strip()
                    if name and not resolve_name_to_id(name, name_map):
                        unmatched_names.add(name)

        # 第3步：为无法匹配的名字创建占位员工
        if unmatched_names:
            print(f"\n--- 第3步：为 {len(unmatched_names)} 个无法匹配的名字创建占位员工 ---")
            for name in sorted(unmatched_names):
                uid, display = create_placeholder_staff(
                    name, staff_role_id, name_map, id_to_display, dry_run
                )
                if uid:
                    stats['staff_created'].add(name)
        else:
            print("\n--- 第3步：所有名字都已匹配，无需创建员工 ---")

        if not dry_run and unmatched_names:
            db.session.commit()

        # 第4步：逐条处理项目记录
        print(f"\n--- 第4步：处理项目数据 ---")
        for row in rows:
            pid, hid, op_ids_str, op_names_str, sp_ids_str, sp_names_str, s_id, s_name = row
            updates = {}

            # --- 修复 staff_id（经办人）---
            if not s_id and s_name and s_name.strip():
                matched_uid = resolve_name_to_id(s_name, name_map)
                if matched_uid:
                    updates['staff_id'] = matched_uid
                    updates['staff_name'] = id_to_display.get(matched_uid, s_name.strip())
                    stats['staff_id_fixed'] += 1
            elif s_id and s_id in id_to_display:
                # staff_id 存在，同步 staff_name 为标准格式
                expected_name = id_to_display[s_id]
                if expected_name != (s_name or ''):
                    updates['staff_name'] = expected_name

            # --- 处理操作员 ---
            if op_ids_str and op_ids_str.strip():
                # 已有 IDs → 重新同步缓存名字
                ids = [int(s.strip()) for s in op_ids_str.split(',')
                       if s.strip() and s.strip().isdigit()]
                if ids:
                    new_names = ','.join(id_to_display.get(uid, f'ID:{uid}') for uid in ids)
                    if new_names != (op_names_str or ''):
                        updates['operator_names'] = new_names
                        stats['op_names_synced'] += 1
            elif op_names_str and op_names_str.strip():
                # 只有 names，没有 IDs → 匹配（此时所有名字都应该能匹配了）
                names = [n.strip() for n in op_names_str.split(',') if n.strip()]
                matched_ids = []
                matched_names = []
                for name in names:
                    uid = resolve_name_to_id(name, name_map)
                    if uid:
                        matched_ids.append(str(uid))
                        matched_names.append(id_to_display.get(uid, name))
                    else:
                        matched_names.append(name)

                if matched_ids:
                    updates['operator_ids'] = ','.join(matched_ids)
                    updates['operator_names'] = ','.join(matched_names)
                    stats['op_ids_filled'] += 1

            # --- 处理业务员 ---
            if sp_ids_str and sp_ids_str.strip():
                # 已有 IDs → 重新同步缓存名字
                ids = [int(s.strip()) for s in sp_ids_str.split(',')
                       if s.strip() and s.strip().isdigit()]
                if ids:
                    new_names = ','.join(id_to_display.get(uid, f'ID:{uid}') for uid in ids)
                    if new_names != (sp_names_str or ''):
                        updates['salesperson_names'] = new_names
                        stats['sp_names_synced'] += 1
            elif sp_names_str and sp_names_str.strip():
                # 只有 names，没有 IDs → 匹配
                names = [n.strip() for n in sp_names_str.split(',') if n.strip()]
                matched_ids = []
                matched_names = []
                for name in names:
                    uid = resolve_name_to_id(name, name_map)
                    if uid:
                        matched_ids.append(str(uid))
                        matched_names.append(id_to_display.get(uid, name))
                    else:
                        matched_names.append(name)

                if matched_ids:
                    updates['salesperson_ids'] = ','.join(matched_ids)
                    updates['salesperson_names'] = ','.join(matched_names)
                    stats['sp_ids_filled'] += 1

            # 执行更新
            if updates and not dry_run:
                set_clauses = ', '.join(f"{k} = :{k}" for k in updates)
                updates['pid'] = pid
                db.session.execute(text(
                    f"UPDATE project_headers SET {set_clauses} WHERE id = :pid"
                ), updates)

        if not dry_run:
            db.session.commit()

        # 第5步：输出结果
        print("\n--- 结果统计 ---")
        print(f"  修复 staff_id(经办人):  {stats['staff_id_fixed']} 条")
        print(f"  补全 operator_ids:      {stats['op_ids_filled']} 条")
        print(f"  补全 salesperson_ids:    {stats['sp_ids_filled']} 条")
        print(f"  同步 operator_names:     {stats['op_names_synced']} 条")
        print(f"  同步 salesperson_names:   {stats['sp_names_synced']} 条")

        if stats['staff_created']:
            print(f"\n  自动创建占位员工 {len(stats['staff_created'])} 个（is_verified=False，待处理）:")
            for name in sorted(stats['staff_created']):
                print(f"    - '{name}'")
            print("  这些账号已可在筛选下拉框中显示，请在后台「员工管理」中统一处理（设密码/合并/删除）")

        print("\n" + ("【预览完成，未修改数据库】" if dry_run else "同步完成！"))


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    sync_operator_salesperson(dry_run=dry_run)
