from App_new.exts import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # 用户角色：admin, user
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # 用户个人信息
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    
    def __init__(self, username, email, password, role='user', full_name=None, 
                 phone=None, department=None, position=None):
        self.username = username
        self.email = email
        self.set_password(password)
        self.role = role
        self.full_name = full_name
        self.phone = phone
        self.department = department
        self.position = position

    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """检查是否是管理员"""
        return self.role == 'admin'

    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'full_name': self.full_name,
            'phone': self.phone,
            'department': self.department,
            'position': self.position
        }

    @staticmethod
    def create_user(username, email, password, role='user', full_name=None, 
                   phone=None, department=None, position=None):
        """创建新用户"""
        try:
            user = User(
                username=username,
                email=email,
                password=password,
                role=role,
                full_name=full_name,
                phone=phone,
                department=department,
                position=position
            )
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"创建用户失败: {str(e)}")

    @staticmethod
    def get_by_username(username):
        """通过用户名获取用户"""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_by_email(email):
        """通过邮箱获取用户"""
        return User.query.filter_by(email=email).first()

    def __repr__(self):
        return f'<User {self.username}>' 