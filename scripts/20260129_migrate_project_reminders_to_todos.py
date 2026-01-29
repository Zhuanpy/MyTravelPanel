# -*- coding: utf-8 -*-
"""
迁移项目提醒数据：
1. 将 todos 表中 source_id 从 reminder_id 改为 header_id
2. project_reminders 表数据保留作为备份，不再使用
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    from App_new.business.projects.models.project import ProjectReminder, ProjectHeader
    from App_new.shared.models.Utilsmodels import Todo

    print("开始迁移项目提醒数据...")

    # 获取所有项目提醒类型的 Todo
    todos = Todo.query.filter_by(source_type='project_reminder').all()
    print(f"找到 {len(todos)} 条项目提醒 Todo")

    updated_count = 0
    skipped_count = 0

    for todo in todos:
        # 检查 source_id 是否指向 ProjectReminder
        reminder = ProjectReminder.query.get(todo.source_id)

        if reminder:
            # source_id 是 reminder_id，需要更新为 header_id
            old_source_id = todo.source_id
            todo.source_id = reminder.header_id
            updated_count += 1
            print(f"  更新: Todo {todo.id} source_id: {old_source_id} -> {reminder.header_id}")
        else:
            # source_id 可能已经是 header_id，检查是否有效
            header = ProjectHeader.query.get(todo.source_id)
            if header:
                print(f"  跳过: Todo {todo.id} source_id={todo.source_id} 已指向有效的项目")
                skipped_count += 1
            else:
                print(f"  警告: Todo {todo.id} source_id={todo.source_id} 无效（找不到关联数据）")
                skipped_count += 1

    try:
        db.session.commit()
        print(f"\n迁移完成!")
        print(f"  - 更新成功: {updated_count} 条")
        print(f"  - 已跳过: {skipped_count} 条")
        print(f"\n注意: project_reminders 表数据已保留，可手动删除")
    except Exception as e:
        db.session.rollback()
        print(f"\n迁移失败: {e}")
