from App_new.exts import db  # 确保你已正确导入 db 对象
from datetime import datetime
import json

# Task模型已删除，现在只保留Todo模型及相关的任务模板和清单功能

class Todo(db.Model):
    """待办事项模型"""
    __tablename__ = 'todos'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_completed = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    priority = db.Column(db.Integer, default=2)  # 1=高，2=中，3=低
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id', ondelete='CASCADE'), nullable=True)
    # 分类（类型）
    category = db.Column(db.String(50), nullable=True)
    # 邮件提醒字段
    recipient_email = db.Column(db.String(255), nullable=True)
    send_email = db.Column(db.Boolean, default=False, nullable=False)
    email_reminder_sent = db.Column(db.Boolean, default=False, nullable=False)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    
    # 任务分配字段
    assigned_to = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='分配给的用户ID')
    assigned_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='分配者用户ID')
    assigned_at = db.Column(db.DateTime, nullable=True, comment='分配时间')
    
    # 业务数据关联字段
    source_type = db.Column(db.String(50), nullable=True, comment='来源类型: visa, project, manual')
    source_id = db.Column(db.Integer, nullable=True, comment='来源业务数据ID')
    reminder_days_before = db.Column(db.Integer, default=0, comment='提前提醒天数')
    auto_generated = db.Column(db.Boolean, default=False, comment='是否自动生成')
    
    # 任务完成记录字段
    completed_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='完成者用户ID')
    completed_at = db.Column(db.DateTime, nullable=True, comment='完成时间')

    # 准时性跟踪字段
    is_on_time = db.Column(db.Boolean, nullable=True, comment='任务是否准时完成: TRUE=准时, FALSE=延迟, NULL=未完成')
    delay_days = db.Column(db.Integer, default=0, comment='延迟天数（负数表示提前完成）')

    # 工时字段
    estimated_hours = db.Column(db.Float, nullable=True, default=0, comment='预估工时（小时）')
    actual_hours = db.Column(db.Float, nullable=True, default=0, comment='实际工时（小时）')

    # 关系
    assignee = db.relationship('AuthUser', foreign_keys=[assigned_to], backref='assigned_todos')
    assigner = db.relationship('AuthUser', foreign_keys=[assigned_by], backref='assigned_todos_by_me')
    completer = db.relationship('AuthUser', foreign_keys=[completed_by], backref='completed_todos')

    def __init__(self, title, description=None, due_date=None, priority=2, user_id=None, category=None, is_completed=False,
                 recipient_email=None, send_email=False, email_reminder_sent=False, email_sent_at=None,
                 assigned_to=None, assigned_by=None, assigned_at=None, source_type=None, source_id=None,
                 reminder_days_before=0, auto_generated=False, completed_by=None, completed_at=None,
                 is_on_time=None, delay_days=0, estimated_hours=0, actual_hours=0):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.user_id = user_id
        self.category = category
        self.is_completed = is_completed
        self.recipient_email = recipient_email
        self.send_email = bool(send_email)
        self.email_reminder_sent = bool(email_reminder_sent)
        self.email_sent_at = email_sent_at
        self.assigned_to = assigned_to
        self.assigned_by = assigned_by
        self.assigned_at = assigned_at
        self.source_type = source_type
        self.source_id = source_id
        self.reminder_days_before = reminder_days_before
        self.auto_generated = bool(auto_generated)
        self.completed_by = completed_by
        self.completed_at = completed_at
        self.is_on_time = is_on_time
        self.delay_days = delay_days
        self.estimated_hours = estimated_hours
        self.actual_hours = actual_hours

    def to_dict(self):
        """将模型转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'is_completed': self.is_completed,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'priority': self.priority,
            'user_id': self.user_id,
            'category': self.category,
            'recipient_email': self.recipient_email,
            'send_email': self.send_email,
            'email_reminder_sent': self.email_reminder_sent,
            'email_sent_at': self.email_sent_at.isoformat() if self.email_sent_at else None,
            'assigned_to': self.assigned_to,
            'assigned_by': self.assigned_by,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'reminder_days_before': self.reminder_days_before,
            'auto_generated': self.auto_generated,
            'assignee_name': self.assignee.username if self.assignee else None,
            'assigner_name': self.assigner.username if self.assigner else None,
            'completed_by': self.completed_by,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completer_name': self.completer.username if self.completer else None,
            'is_on_time': self.is_on_time,
            'delay_days': self.delay_days,
            'estimated_hours': self.estimated_hours or 0,
            'actual_hours': self.actual_hours or 0
        }

    @classmethod
    def create(cls, title, description=None, due_date=None, priority=2, user_id=None, category=None, is_completed=False,
               recipient_email=None, send_email=False, email_reminder_sent=False, email_sent_at=None,
               assigned_to=None, assigned_by=None, assigned_at=None, source_type=None, source_id=None,
               reminder_days_before=0, auto_generated=False, completed_by=None, completed_at=None,
               is_on_time=None, delay_days=0, estimated_hours=0, actual_hours=0):
        """创建新的待办事项"""
        todo = cls(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            user_id=user_id,
            category=category,
            is_completed=is_completed,
            recipient_email=recipient_email,
            send_email=bool(send_email),
            email_reminder_sent=bool(email_reminder_sent),
            email_sent_at=email_sent_at,
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            assigned_at=assigned_at,
            source_type=source_type,
            source_id=source_id,
            reminder_days_before=reminder_days_before,
            auto_generated=bool(auto_generated),
            completed_by=completed_by,
            completed_at=completed_at,
            is_on_time=is_on_time,
            delay_days=delay_days,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours
        )
        db.session.add(todo)
        db.session.commit()
        return todo

    @classmethod
    def update(cls, todo_id, **kwargs):
        """更新待办事项"""
        todo = cls.query.get(todo_id)
        if todo:
            for key, value in kwargs.items():
                if hasattr(todo, key):
                    setattr(todo, key, value)
            todo.updated_at = datetime.utcnow()
            db.session.commit()
            return todo
        return None

    @classmethod
    def delete(cls, todo_id):
        """删除待办事项"""
        todo = cls.query.get(todo_id)
        if todo:
            db.session.delete(todo)
            db.session.commit()
            return True
        return False

    @classmethod
    def get_by_user(cls, user_id):
        """获取指定用户的所有待办事项"""
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def get_completed(cls, user_id=None):
        """获取已完成的待办事项"""
        query = cls.query.filter_by(is_completed=True)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.all()

    @classmethod
    def get_pending(cls, user_id=None):
        """获取未完成的待办事项"""
        query = cls.query.filter_by(is_completed=False)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.all()

    @classmethod
    def get_by_priority(cls, priority, user_id=None):
        """按优先级获取待办事项"""
        query = cls.query.filter_by(priority=priority)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.all()

    @classmethod
    def get_overdue(cls, user_id=None):
        """获取已过期的待办事项"""
        now = datetime.utcnow()
        query = cls.query.filter(cls.due_date < now, cls.is_completed == False)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.all()


class TodoChecklist(db.Model):
    """任务清单模型 - 用于管理一组相关的任务"""
    __tablename__ = 'todo_checklists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, comment='清单名称')
    description = db.Column(db.Text, comment='清单描述')
    category = db.Column(db.String(50), nullable=True, comment='分类')

    # 重复设置
    is_recurring = db.Column(db.Boolean, default=False, comment='是否为重复任务')
    recurrence_type = db.Column(db.String(20), comment='重复类型: daily, weekly, monthly')
    recurrence_days = db.Column(db.String(50), comment='重复的星期几（用于weekly）：1,2,3,4,5,6,0（周一到周日）')
    recurrence_time = db.Column(db.String(10), comment='重复的时间: HH:MM')

    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id', ondelete='CASCADE'), nullable=True)

    # 最后生成任务的时间
    last_generated_at = db.Column(db.DateTime, nullable=True, comment='最后一次生成任务的时间')

    # 新增字段
    default_due_days = db.Column(db.Integer, default=7, comment='默认截止天数')
    is_team_visible = db.Column(db.Boolean, default=False, comment='是否团队可见')

    # 任务项（一对多）
    items = db.relationship('TodoChecklistItem', backref='checklist', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'is_recurring': self.is_recurring,
            'recurrence_type': self.recurrence_type,
            'recurrence_days': self.recurrence_days,
            'recurrence_time': self.recurrence_time,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_generated_at': self.last_generated_at.isoformat() if self.last_generated_at else None,
            'default_due_days': self.default_due_days or 7,
            'is_team_visible': self.is_team_visible or False,
            'items': [item.to_dict() for item in self.items.all()]
        }


class TodoChecklistItem(db.Model):
    """任务清单项目模型 - 清单中的具体任务"""
    __tablename__ = 'todo_checklist_items'

    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('todo_checklists.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False, comment='任务标题')
    description = db.Column(db.Text, comment='任务描述')
    priority = db.Column(db.Integer, default=2, comment='优先级：1=高，2=中，3=低')
    order_index = db.Column(db.Integer, default=0, comment='排序索引')

    # 新增字段
    assigned_to = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='默认分配给的员工ID')
    due_days_offset = db.Column(db.Integer, default=0, comment='截止天数偏移（生成后多少天截止）')

    # 关系
    assignee = db.relationship('AuthUser', foreign_keys=[assigned_to])

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'checklist_id': self.checklist_id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'order_index': self.order_index,
            'assigned_to': self.assigned_to,
            'due_days_offset': self.due_days_offset or 0,
            'assignee_name': self.assignee.username if self.assignee else None
        }