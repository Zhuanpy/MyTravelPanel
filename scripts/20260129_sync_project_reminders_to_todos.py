# -*- coding: utf-8 -*-
"""
将现有的项目提醒（project_reminders）同步到待办事项表（todos）
实现项目提醒和待办事项的统一管理
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

    print("开始同步项目提醒到待办事项表...")

    # 获取所有项目提醒
    reminders = ProjectReminder.query.all()
    print(f"找到 {len(reminders)} 条项目提醒")

    synced_count = 0
    skipped_count = 0

    for reminder in reminders:
        # 检查是否已存在对应的 Todo
        existing_todo = Todo.query.filter_by(
            source_type='project_reminder',
            source_id=reminder.id
        ).first()

        if existing_todo:
            print(f"  跳过: 提醒 ID={reminder.id} 已存在对应的 Todo")
            skipped_count += 1
            continue

        # 获取项目信息
        header = reminder.header
        if not header:
            print(f"  跳过: 提醒 ID={reminder.id} 找不到对应的项目")
            skipped_count += 1
            continue

        # 创建 Todo
        title = f"[{header.hid}] {reminder.reminder_event}"
        description = f"项目: {header.hid}\n描述: {header.desc or ''}\n提醒事件: {reminder.reminder_event}"
        due_date = datetime.combine(reminder.reminder_date, datetime.min.time()) if reminder.reminder_date else None

        todo = Todo(
            title=title,
            description=description,
            priority=2,  # 中等优先级
            due_date=due_date,
            category='项目提醒',
            source_type='project_reminder',
            source_id=reminder.id,
            is_completed=reminder.is_completed,
            user_id=None  # 项目提醒不关联特定用户
        )

        db.session.add(todo)
        synced_count += 1
        print(f"  同步: [{header.hid}] {reminder.reminder_event} -> Todo")

    try:
        db.session.commit()
        print(f"\n同步完成!")
        print(f"  - 同步成功: {synced_count} 条")
        print(f"  - 已跳过: {skipped_count} 条")
    except Exception as e:
        db.session.rollback()
        print(f"\n同步失败: {e}")
