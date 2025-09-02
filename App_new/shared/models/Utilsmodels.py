from App_new.exts import db  # 确保你已正确导入 db 对象
from datetime import datetime

# 定义数据库模型
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    remaining_time = db.Column(db.Integer, default=600)  # 默认为 600 秒 (10分钟)
    status = db.Column(db.String(20), default='stopped')  # 状态字段，可以是 'running', 'paused', 'stopped'

    def create(self, name):
        self.name = name
        db.session.add(self)
        db.session.commit()

    @classmethod
    def update_status(cls, task_id, status, remaining_time=None):
        task = cls.query.get(task_id)
        if task:
            task.status = status
            if remaining_time is not None:  # 如果传递了剩余时间
                task.remaining_time = remaining_time
            db.session.commit()
            return task
        return None

    @classmethod
    def reset(cls, task_id):
        task = cls.query.get(task_id)
        if task:
            task.remaining_time = 600  # 重置为10分钟
            task.status = 'paused'  # 假设任务重置后是暂停状态
            db.session.commit()
            return task
        return None

    @classmethod
    def delete(cls, task_id):
        task = cls.query.get(task_id)
        if task:
            db.session.delete(task)
            db.session.commit()
            return True
        return False

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
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True)

    def __init__(self, title, description=None, due_date=None, priority=2, user_id=None):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.user_id = user_id

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
            'user_id': self.user_id
        }

    @classmethod
    def create(cls, title, description=None, due_date=None, priority=2, user_id=None):
        """创建新的待办事项"""
        todo = cls(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            user_id=user_id
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