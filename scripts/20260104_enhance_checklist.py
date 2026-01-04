# -*- coding: utf-8 -*-
"""
增强任务清单功能 - 添加任务分配和截止日期设置

运行方式: python scripts/20260104_enhance_checklist.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new.exts import db
from app_new import create_app
from sqlalchemy import text


def run_migration():
    """执行数据库迁移"""
    app = create_app()
    with app.app_context():
        try:
            # 检查 todo_checklist_items 表的现有字段
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'todo_checklist_items'
                AND COLUMN_NAME IN ('assigned_to', 'due_days_offset')
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            # 添加 assigned_to 字段 - 任务默认分配给的员工
            if 'assigned_to' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE todo_checklist_items
                    ADD COLUMN assigned_to INT NULL
                    COMMENT '默认分配给的员工ID'
                """))
                print("已添加 assigned_to 字段到 todo_checklist_items")
            else:
                print("assigned_to 字段已存在，跳过")

            # 添加 due_days_offset 字段 - 任务生成后多少天截止
            if 'due_days_offset' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE todo_checklist_items
                    ADD COLUMN due_days_offset INT DEFAULT 0
                    COMMENT '截止天数偏移（生成后多少天截止）'
                """))
                print("已添加 due_days_offset 字段到 todo_checklist_items")
            else:
                print("due_days_offset 字段已存在，跳过")

            # 检查 todo_checklists 表的现有字段
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'todo_checklists'
                AND COLUMN_NAME IN ('default_due_days', 'is_team_visible')
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            # 添加 default_due_days 字段 - 默认截止天数
            if 'default_due_days' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE todo_checklists
                    ADD COLUMN default_due_days INT DEFAULT 7
                    COMMENT '默认截止天数'
                """))
                print("已添加 default_due_days 字段到 todo_checklists")
            else:
                print("default_due_days 字段已存在，跳过")

            # 添加 is_team_visible 字段 - 团队可见
            if 'is_team_visible' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE todo_checklists
                    ADD COLUMN is_team_visible BOOLEAN DEFAULT FALSE
                    COMMENT '是否团队可见'
                """))
                print("已添加 is_team_visible 字段到 todo_checklists")
            else:
                print("is_team_visible 字段已存在，跳过")

            db.session.commit()
            print("\n数据库迁移完成！")

        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {str(e)}")
            raise


if __name__ == '__main__':
    run_migration()
