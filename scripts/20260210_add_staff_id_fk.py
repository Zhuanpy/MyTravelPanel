# -*- coding: utf-8 -*-
"""
将 project_headers.staff_id 改为外键关联 auth_users.id

步骤:
1. 查找并修复孤立的 staff_id（不在 auth_users 中的）
2. 统一同步 staff_name 为标准格式（从 user_profiles 获取）
3. 添加 FK 约束

运行方式: python scripts/20260210_add_staff_id_fk.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def migrate():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("ProjectHeader.staff_id 改为外键关联")
        print("=" * 60)

        # 第1步：查找孤立的 staff_id
        print("\n--- 第1步：检查孤立的 staff_id ---")
        orphans = db.session.execute(text(
            "SELECT ph.id, ph.hid, ph.staff_id, ph.staff_name "
            "FROM project_headers ph "
            "WHERE ph.staff_id IS NOT NULL "
            "AND ph.staff_id NOT IN (SELECT id FROM auth_users)"
        )).fetchall()

        if orphans:
            print(f"  发现 {len(orphans)} 条孤立记录，尝试修复...")
            for row in orphans:
                pid, hid, sid, sname = row
                fixed = False
                if sname:
                    # 尝试通过 username 匹配
                    match = db.session.execute(text(
                        "SELECT id FROM auth_users WHERE username = :name"
                    ), {'name': sname.strip()}).fetchone()
                    if not match:
                        # 尝试通过 user_profiles 姓名匹配
                        match = db.session.execute(text(
                            "SELECT au.id FROM auth_users au "
                            "JOIN user_profiles up ON au.id = up.user_id "
                            "WHERE CONCAT(IFNULL(up.first_name,''), IFNULL(up.last_name,'')) = :name "
                            "OR CONCAT(IFNULL(up.first_name,''), ' ', IFNULL(up.last_name,'')) = :name2"
                        ), {'name': sname.replace(' ', ''), 'name2': sname.strip()}).fetchone()
                    if match:
                        db.session.execute(text(
                            "UPDATE project_headers SET staff_id = :uid WHERE id = :pid"
                        ), {'uid': match[0], 'pid': pid})
                        print(f"    HID={hid}: staff_id {sid} → {match[0]} (通过姓名 '{sname}' 匹配)")
                        fixed = True
                if not fixed:
                    db.session.execute(text(
                        "UPDATE project_headers SET staff_id = NULL WHERE id = :pid"
                    ), {'pid': pid})
                    print(f"    HID={hid}: staff_id {sid} 无法匹配，已置 NULL (staff_name='{sname}')")
            db.session.commit()
        else:
            print("  没有孤立的 staff_id")

        # 第2步：同步 staff_name 为标准格式
        print("\n--- 第2步：同步 staff_name ---")
        result = db.session.execute(text(
            "UPDATE project_headers ph "
            "JOIN auth_users au ON ph.staff_id = au.id "
            "LEFT JOIN user_profiles up ON au.id = up.user_id "
            "SET ph.staff_name = CASE "
            "  WHEN up.first_name IS NOT NULL AND up.first_name != '' "
            "    THEN CONCAT(IFNULL(up.first_name,''), IFNULL(up.last_name,'')) "
            "  ELSE au.username "
            "END "
            "WHERE ph.staff_id IS NOT NULL"
        ))
        db.session.commit()
        print(f"  已同步 {result.rowcount} 条记录的 staff_name")

        # 第3步：添加 FK 约束
        print("\n--- 第3步：添加 FK 约束 ---")
        fk_exists = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'project_headers' "
            "AND CONSTRAINT_NAME = 'fk_project_staff'"
        )).scalar()

        if fk_exists == 0:
            db.session.execute(text(
                "ALTER TABLE project_headers "
                "ADD CONSTRAINT fk_project_staff "
                "FOREIGN KEY (staff_id) REFERENCES auth_users(id) "
                "ON DELETE SET NULL"
            ))
            db.session.commit()
            print("  FK 约束添加完成")
        else:
            print("  FK 约束已存在，跳过")

        print("\n✓ 迁移完成！")


if __name__ == '__main__':
    migrate()
