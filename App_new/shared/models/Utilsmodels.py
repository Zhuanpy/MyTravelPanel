from App_new.exts import db  # 确保你已正确导入 db 对象
from datetime import datetime

# Task模型已删除，现在只保留Todo模型

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
    # 分类（类型）
    category = db.Column(db.String(50), nullable=True)

    def __init__(self, title, description=None, due_date=None, priority=2, user_id=None, category=None, is_completed=False):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.user_id = user_id
        self.category = category
        self.is_completed = is_completed

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
            'category': self.category
        }

    @classmethod
    def create(cls, title, description=None, due_date=None, priority=2, user_id=None, category=None, is_completed=False):
        """创建新的待办事项"""
        todo = cls(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            user_id=user_id,
            category=category,
            is_completed=is_completed
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