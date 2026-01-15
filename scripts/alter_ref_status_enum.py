# -*- coding: utf-8 -*-
"""
修改 project_refs 表的 status 枚举值

旧值: draft, processing, completed, cancelled
新值: confirmed, completed, cancelled

运行方式: python scripts/alter_ref_status_enum.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db


def main():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("  修改 project_refs.status 枚举值")
        print("=" * 60)

        # 统计现有数据
        print("\n[1/4] 检查现有数据...")
        result = db.session.execute(db.text("""
            SELECT status, COUNT(*) as cnt
            FROM project_refs
            GROUP BY status
        """))
        print("  当前状态分布:")
        for row in result:
            print(f"    {row[0]}: {row[1]} 条")

        # 1. 先扩展枚举类型，添加 confirmed
        print("\n[2/4] 扩展枚举类型（添加 confirmed）...")
        db.session.execute(db.text("""
            ALTER TABLE project_refs
            MODIFY COLUMN status ENUM('draft', 'processing', 'completed', 'cancelled', 'confirmed')
            NOT NULL DEFAULT 'confirmed'
        """))
        db.session.commit()
        print("  枚举扩展完成")

        # 2. 更新数据
        print("\n[3/4] 更新现有数据...")

        # 更新 draft -> confirmed
        result = db.session.execute(db.text("""
            UPDATE project_refs SET status = 'confirmed' WHERE status = 'draft'
        """))
        print(f"  draft -> confirmed: {result.rowcount} 条")

        # 更新 processing -> confirmed
        result = db.session.execute(db.text("""
            UPDATE project_refs SET status = 'confirmed' WHERE status = 'processing'
        """))
        print(f"  processing -> confirmed: {result.rowcount} 条")

        db.session.commit()

        # 3. 收缩枚举类型，移除 draft 和 processing
        print("\n[4/4] 收缩枚举类型（移除 draft, processing）...")
        db.session.execute(db.text("""
            ALTER TABLE project_refs
            MODIFY COLUMN status ENUM('confirmed', 'completed', 'cancelled')
            NOT NULL DEFAULT 'confirmed'
        """))
        db.session.commit()
        print("  枚举收缩完成")

        # 验证
        print("\n验证修改...")
        result = db.session.execute(db.text("""
            SELECT status, COUNT(*) as cnt
            FROM project_refs
            GROUP BY status
        """))
        print("  新状态分布:")
        for row in result:
            print(f"    {row[0]}: {row[1]} 条")

        print("\n" + "=" * 60)
        print("  迁移完成！")
        print("=" * 60)


if __name__ == '__main__':
    main()
