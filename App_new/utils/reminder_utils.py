# -*- coding: utf-8 -*-
"""提醒工具模块"""

from datetime import datetime, timedelta
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.shared.models.Utilsmodels import Todo


def create_reminder_todo(project_header):
    """
    为项目表头创建提醒待办事项
    
    Args:
        project_header: ProjectHeader实例
    """
    if not project_header.reminder_event or not project_header.reminder_date:
        return None
    
    # 检查是否已经存在相同的提醒待办事项
    existing_todo = Todo.query.filter_by(
        title=f"项目提醒: {project_header.hid}",
        description=f"项目: {project_header.desc}\n提醒事件: {project_header.reminder_event}",
        category="项目提醒"
    ).first()
    
    if existing_todo:
        # 更新现有待办事项的截止日期
        existing_todo.due_date = project_header.reminder_date
        existing_todo.updated_at = datetime.utcnow()
        db.session.commit()
        return existing_todo
    
    # 创建新的待办事项
    todo = Todo(
        title=f"项目提醒: {project_header.hid}",
        description=f"项目: {project_header.desc}\n提醒事件: {project_header.reminder_event}",
        category="项目提醒",
        priority=2,  # 中等优先级
        due_date=project_header.reminder_date
    )
    
    db.session.add(todo)
    db.session.commit()
    return todo


def sync_project_reminders():
    """
    同步所有项目提醒到待办事项列表
    """
    # 获取所有有提醒信息的项目
    projects_with_reminders = ProjectHeader.query.filter(
        ProjectHeader.reminder_event.isnot(None),
        ProjectHeader.reminder_date.isnot(None)
    ).all()
    
    synced_count = 0
    for project in projects_with_reminders:
        todo = create_reminder_todo(project)
        if todo:
            synced_count += 1
    
    return synced_count


def get_upcoming_reminders(days_ahead=1):
    """
    获取即将到来的提醒（用于邮件通知）
    
    Args:
        days_ahead: 提前多少天提醒，默认1天
    
    Returns:
        list: 即将到期的项目提醒列表
    """
    tomorrow = datetime.utcnow() + timedelta(days=days_ahead)
    tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    reminders = ProjectHeader.query.filter(
        ProjectHeader.reminder_date.between(tomorrow_start, tomorrow_end),
        ProjectHeader.reminder_sent == False,
        ProjectHeader.status.in_(['draft', 'active'])  # 只提醒草稿和进行中的项目
    ).all()
    
    return reminders


def mark_reminder_sent(project_header):
    """
    标记提醒已发送
    
    Args:
        project_header: ProjectHeader实例
    """
    project_header.reminder_sent = True
    db.session.commit()
