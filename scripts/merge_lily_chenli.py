# -*- coding: utf-8 -*-
"""
合并员工：CHEN LI 和 Lily 是同一人，统一为一个账号

步骤：
1. 查找两个账号
2. 选择保留的主账号（CHEN LI，有完整资料）
3. 将 Lily 账号关联的所有项目数据迁移到 CHEN LI
4. 删除 Lily 占位账号

涉及字段：
- project_headers.staff_id / staff_name（经办人）
- project_headers.operator_ids / operator_names（操作员，逗号分隔）
- project_headers.salesperson_ids / salesperson_names（业务员，逗号分隔）

运行方式: python scripts/merge_lily_chenli.py
预览模式: python scripts/merge_lily_chenli.py --dry-run
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def find_users():
    """查找 CHEN LI 和 Lily 两个账号"""
    rows = db.session.execute(text(
        "SELECT au.id, au.username, au.is_active, au.is_verified, "
        "       up.first_name, up.last_name "
        "FROM auth_users au "
        "LEFT JOIN user_profiles up ON au.id = up.user_id "
        "WHERE au.username IN ('lily', 'chenli', 'chen_li') "
        "   OR up.first_name LIKE '%%Lily%%' "
        "   OR up.first_name LIKE '%%CHEN%%' "
        "   OR (up.first_name = 'CHEN' AND up.last_name = 'LI') "
        "ORDER BY au.id"
    )).fetchall()
    return rows


def replace_id_in_csv(csv_str, old_id, new_id):
    """替换逗号分隔字符串中的 ID"""
    if not csv_str:
        return csv_str, False
    parts = [s.strip() for s in csv_str.split(',')]
    changed = False
    new_parts = []
    for p in parts:
        if p == str(old_id):
            new_parts.append(str(new_id))
            changed = True
        else:
            new_parts.append(p)
    return ','.join(new_parts), changed


def replace_name_in_csv(csv_str, old_names, new_name):
    """替换逗号分隔字符串中的名字（忽略大小写）"""
    if not csv_str:
        return csv_str, False
    parts = [s.strip() for s in csv_str.split(',')]
    old_names_lower = [n.lower() for n in old_names]
    changed = False
    new_parts = []
    for p in parts:
        if p.lower() in old_names_lower:
            new_parts.append(new_name)
            changed = True
        else:
            new_parts.append(p)
    return ','.join(new_parts), changed


def merge(dry_run=False):
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("合并员工：CHEN LI + Lily → 统一账号")
        if dry_run:
            print("【预览模式】不会修改数据库")
        print("=" * 60)

        # 第1步：查找两个账号
        print("\n--- 第1步：查找账号 ---")
        users = find_users()
        for u in users:
            print(f"  ID={u[0]}, username='{u[1]}', active={u[2]}, verified={u[3]}, "
                  f"name='{u[4]} {u[5]}'")

        if len(users) < 2:
            print("\n未找到两个账号，请手动确认用户名。")
            print("当前查到的用户如上，请检查 CHEN LI 的 username 是什么。")
            # 列出所有员工供参考
            print("\n所有员工列表：")
            all_staff = db.session.execute(text(
                "SELECT au.id, au.username, up.first_name, up.last_name "
                "FROM auth_users au "
                "LEFT JOIN user_profiles up ON au.id = up.user_id "
                "ORDER BY au.id"
            )).fetchall()
            for s in all_staff:
                print(f"  ID={s[0]}, username='{s[1]}', name='{s[2]} {s[3]}'")
            return

        # 需要人工确认主账号和被合并账号
        # Lily(ID=24) 是占位账号，应该合并到 CHEN LI
        lily_id = None
        keep_id = None
        keep_display = None

        for u in users:
            if u[1] == 'lily':
                lily_id = u[0]
            else:
                keep_id = u[0]
                first = (u[4] or '').strip()
                last = (u[5] or '').strip()
                keep_display = f"{first}{last}".strip() if (first or last) else u[1]

        if not lily_id or not keep_id:
            print("\n无法自动识别主账号和占位账号，请手动确认。")
            return

        print(f"\n  保留账号: ID={keep_id}, 显示名='{keep_display}'")
        print(f"  删除账号: ID={lily_id}, username='lily'（占位）")

        # Lily 可能的名字变体
        lily_names = ['Lily', 'LILY', 'lily']

        # 第2步：迁移 staff_id（经办人）
        print(f"\n--- 第2步：迁移 staff_id ---")
        affected = db.session.execute(text(
            "SELECT id, hid FROM project_headers WHERE staff_id = :old_id"
        ), {'old_id': lily_id}).fetchall()
        print(f"  找到 {len(affected)} 个项目的经办人是 Lily")
        for a in affected:
            print(f"    {a[1]}")

        if not dry_run and affected:
            db.session.execute(text(
                "UPDATE project_headers SET staff_id = :new_id, staff_name = :name "
                "WHERE staff_id = :old_id"
            ), {'new_id': keep_id, 'name': keep_display, 'old_id': lily_id})

        # 第3步：迁移 operator_ids / operator_names
        print(f"\n--- 第3步：迁移 operator_ids/names ---")
        rows = db.session.execute(text(
            "SELECT id, hid, operator_ids, operator_names "
            "FROM project_headers "
            "WHERE FIND_IN_SET(:old_id, operator_ids) > 0"
        ), {'old_id': str(lily_id)}).fetchall()
        print(f"  找到 {len(rows)} 个项目的操作员包含 Lily")

        op_count = 0
        for r in rows:
            new_ids, id_changed = replace_id_in_csv(r[2], lily_id, keep_id)
            new_names, name_changed = replace_name_in_csv(r[3], lily_names, keep_display)
            if id_changed or name_changed:
                print(f"    {r[1]}: op_ids '{r[2]}'→'{new_ids}', op_names '{r[3]}'→'{new_names}'")
                op_count += 1
                if not dry_run:
                    db.session.execute(text(
                        "UPDATE project_headers SET operator_ids=:ids, operator_names=:names "
                        "WHERE id=:pid"
                    ), {'ids': new_ids, 'names': new_names, 'pid': r[0]})

        # 第4步：迁移 salesperson_ids / salesperson_names
        print(f"\n--- 第4步：迁移 salesperson_ids/names ---")
        rows = db.session.execute(text(
            "SELECT id, hid, salesperson_ids, salesperson_names "
            "FROM project_headers "
            "WHERE FIND_IN_SET(:old_id, salesperson_ids) > 0"
        ), {'old_id': str(lily_id)}).fetchall()
        print(f"  找到 {len(rows)} 个项目的业务员包含 Lily")

        sp_count = 0
        for r in rows:
            new_ids, id_changed = replace_id_in_csv(r[2], lily_id, keep_id)
            new_names, name_changed = replace_name_in_csv(r[3], lily_names, keep_display)
            if id_changed or name_changed:
                print(f"    {r[1]}: sp_ids '{r[2]}'→'{new_ids}', sp_names '{r[3]}'→'{new_names}'")
                sp_count += 1
                if not dry_run:
                    db.session.execute(text(
                        "UPDATE project_headers SET salesperson_ids=:ids, salesperson_names=:names "
                        "WHERE id=:pid"
                    ), {'ids': new_ids, 'names': new_names, 'pid': r[0]})

        # 第5步：删除占位账号
        print(f"\n--- 第5步：删除占位账号 lily(ID={lily_id}) ---")
        if not dry_run:
            db.session.execute(text(
                "DELETE FROM user_profiles WHERE user_id = :uid"
            ), {'uid': lily_id})
            db.session.execute(text(
                "DELETE FROM auth_users WHERE id = :uid"
            ), {'uid': lily_id})

        if not dry_run:
            db.session.commit()

        # 汇总
        print(f"\n--- 结果统计 ---")
        print(f"  经办人迁移:  {len(affected)} 个项目")
        print(f"  操作员迁移:  {op_count} 个项目")
        print(f"  业务员迁移:  {sp_count} 个项目")
        print(f"  删除账号:    lily(ID={lily_id})")
        print(f"  保留账号:    {keep_display}(ID={keep_id})")
        print("\n" + ("【预览完成，未修改数据库】" if dry_run else "合并完成！"))


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    merge(dry_run=dry_run)
