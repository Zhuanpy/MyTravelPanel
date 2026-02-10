# -*- coding: utf-8 -*-
"""修复 ref id=2873 的编号（R01 → 正确编号）

运行方式: python scripts/fix_ref_2873_number.py
预览模式: python scripts/fix_ref_2873_number.py --dry-run
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def fix(dry_run=False):
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("修复 REF 编号")
        if dry_run:
            print("【预览模式】不会修改数据库")
        print("=" * 60)

        # 查看 ref 2873 当前状态
        ref = db.session.execute(text(
            "SELECT id, header_id, ref_number, description FROM project_refs WHERE id = 2873"
        )).fetchone()

        if not ref:
            print("未找到 ref id=2873")
            return

        print(f"\n当前: id={ref[0]}, header_id={ref[1]}, ref_number='{ref[2]}', desc='{ref[3]}'")

        if ref[2] != 'R01':
            print(f"ref_number 不是 R01，无需修复")
            return

        # 查找当前最大的 REF 编号
        max_row = db.session.execute(text(
            "SELECT MAX(CAST(SUBSTRING(ref_number, 2) AS UNSIGNED)) "
            "FROM project_refs WHERE ref_number REGEXP '^R[0-9]+$'"
        )).fetchone()
        max_num = max_row[0] or 0
        new_num = max_num + 1
        new_ref_number = f"R{str(new_num).zfill(2)}"

        # 确保新编号不存在
        exists = db.session.execute(text(
            "SELECT id FROM project_refs WHERE ref_number = :rn"
        ), {'rn': new_ref_number}).fetchone()
        if exists:
            print(f"编号 {new_ref_number} 已存在，跳过")
            return

        print(f"修复: ref_number '{ref[2]}' → '{new_ref_number}'")

        if not dry_run:
            db.session.execute(text(
                "UPDATE project_refs SET ref_number = :new_rn WHERE id = 2873"
            ), {'new_rn': new_ref_number})
            db.session.commit()
            print("修复完成！")
        else:
            print("【预览完成，未修改数据库】")


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    fix(dry_run=dry_run)
