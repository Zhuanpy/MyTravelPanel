# -*- coding: utf-8 -*-
"""提醒工具模块"""

from datetime import datetime, timedelta
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.shared.models.Utilsmodels import Todo


LEGACY_REMINDER_SOURCE_TYPE = 'project_header_reminder'


def create_reminder_todo(project_header, creator_id=None):
    """
    为项目表头创建/更新提醒待办事项（基于 ProjectHeader.reminder_event/date 单字段）。

    dedup 策略：
    1. 主键：source_type='project_header_reminder' + source_id=header.id（稳定，
       不受 desc/event 内容变化影响）
    2. fallback：旧的 title+description+category 匹配（兼容尚未回填的历史记录）
       命中后顺手回填 source_type/source_id

    与新版 project_reminder blueprint（source_type='project_reminder'，每项目可
    多条）通过不同的 source_type 隔离，避免语义混淆。

    负责人（assigned_to）来源优先级：
        显式传入的 creator_id（来自 current_user） > project_header.staff_id
    更新已有 todo 时，仅在 assigned_to 为空时补齐，避免覆盖人工调整。
    """
    if not project_header.reminder_event or not project_header.reminder_date:
        return None

    title = f"项目提醒: {project_header.hid}"
    description = f"项目: {project_header.desc}\n提醒事件: {project_header.reminder_event}"
    assignee_id = creator_id or getattr(project_header, 'staff_id', None)

    # 主路径：按稳定键查
    existing_todo = Todo.query.filter_by(
        source_type=LEGACY_REMINDER_SOURCE_TYPE,
        source_id=project_header.id
    ).first()

    # fallback：兼容尚未回填的历史记录
    if not existing_todo:
        existing_todo = Todo.query.filter_by(
            title=title,
            description=description,
            category="项目提醒"
        ).first()

    if existing_todo:
        # 更新内容并补齐 source 字段（自动回填历史记录）
        existing_todo.title = title
        existing_todo.description = description
        existing_todo.due_date = project_header.reminder_date
        existing_todo.source_type = LEGACY_REMINDER_SOURCE_TYPE
        existing_todo.source_id = project_header.id
        # 仅在尚未分配时补齐负责人，不覆盖已有的人工调整
        if assignee_id and not existing_todo.assigned_to:
            existing_todo.assigned_to = assignee_id
            existing_todo.assigned_by = assignee_id
            existing_todo.assigned_at = datetime.utcnow()
        existing_todo.updated_at = datetime.utcnow()
        db.session.commit()
        return existing_todo

    todo = Todo(
        title=title,
        description=description,
        category="项目提醒",
        priority=2,
        due_date=project_header.reminder_date,
        source_type=LEGACY_REMINDER_SOURCE_TYPE,
        source_id=project_header.id,
        user_id=assignee_id,
        assigned_to=assignee_id,
        assigned_by=assignee_id,
        assigned_at=datetime.utcnow() if assignee_id else None
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
