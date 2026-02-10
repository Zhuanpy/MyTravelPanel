# -*- coding: utf-8 -*-
"""检查 Lily 相关的项目数据状态"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    rows = db.session.execute(text(
        "SELECT id, hid, staff_id, staff_name, operator_ids, operator_names, "
        "salesperson_ids, salesperson_names "
        "FROM project_headers "
        "WHERE operator_names LIKE '%%Lily%%' OR salesperson_names LIKE '%%Lily%%' "
        "OR operator_names LIKE '%%LILY%%' OR salesperson_names LIKE '%%LILY%%' "
        "OR staff_name LIKE '%%LILY%%' OR staff_name LIKE '%%lily%%' OR staff_name LIKE '%%Lily%%'"
    )).fetchall()

    print("=" * 80)
    print(f"找到 {len(rows)} 条记录:")
    print("=" * 80)
    for r in rows:
        print(f"  HID={r[1]}")
        print(f"    staff_id={r[2]}, staff_name='{r[3]}'")
        print(f"    op_ids='{r[4]}', op_names='{r[5]}'")
        print(f"    sp_ids='{r[6]}', sp_names='{r[7]}'")
        print()

    # 查看 Lily 的用户ID
    lily = db.session.execute(text(
        "SELECT au.id, au.username, au.is_active, up.first_name, up.last_name "
        "FROM auth_users au LEFT JOIN user_profiles up ON au.id = up.user_id "
        "WHERE au.username LIKE '%%lily%%' OR up.first_name LIKE '%%Lily%%'"
    )).fetchall()
    print("Lily 用户信息:")
    for u in lily:
        print(f"  ID={u[0]}, username='{u[1]}', is_active={u[2]}, name='{u[3]} {u[4]}'")
