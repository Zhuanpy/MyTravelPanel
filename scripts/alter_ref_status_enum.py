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

        # 1. 先将现有的 draft 和 processing 更新为 confirmed
        print("\n[1/3] 更新现有数据...")
        
        # 统计现有数据
        result = db.session.execute(db.text("""
            SELECT status, COUNT(*) as cnt 
            FROM project_refs 
            GROUP BY status
        """))
        print("  当前状态分布:")
        for row in result:
            print(f"    {row[0]}: {row[1]} 条")

        # 更新 draft -> confirmed
        db.session.execute(db.text("""
            UPDATE project_refs SET status = 'confirmed' WHERE status = 'draft'
        """))
        print("  draft -> confirmed: 完成")

        # 更新 processing -> confirmed  
        db.session.execute(db.text("""
            UPDATE project_refs SET status = 'confirmed' WHERE status = 'processing'
        """))
        print("  processing -> confirmed: 完成")

        db.session.commit()

        # 2. 修改枚举类型
        print("\n[2/3] 修改枚举类型...")
        
        db.session.execute(db.text("""
            ALTER TABLE project_refs 
            MODIFY COLUMN status ENUM('confirmed', 'completed', 'cancelled') 
            NOT NULL DEFAULT 'confirmed'
        """))
        db.session.commit()
        print("  枚举修改完成")

        # 3. 验证
        print("\n[3/3] 验证修改...")
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
