"""
为 todo_checklist_items 表添加 estimated_hours 字段
运行方式: python scripts/20260216_add_checklist_item_estimated_hours.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # 检查字段是否已存在
        result = db.session.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'todo_checklist_items' AND COLUMN_NAME = 'estimated_hours'"
        ))
        if result.fetchone():
            print("字段 estimated_hours 已存在，无需修改")
        else:
            db.session.execute(text(
                "ALTER TABLE todo_checklist_items ADD COLUMN estimated_hours FLOAT DEFAULT 0 COMMENT '预估工时（小时）'"
            ))
            db.session.commit()
            print("✓ 已添加 todo_checklist_items.estimated_hours 字段")
    except Exception as e:
        db.session.rollback()
        print(f"✗ 执行失败: {e}")
