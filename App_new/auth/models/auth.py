from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from ...exts import db

class Role(db.Model):
    """角色模型"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # admin, staff, member, guest
    description = db.Column(db.String(200))
    permissions = db.Column(db.JSON)  # 存储权限列表
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    users = db.relationship('AuthUser', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': self.permissions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AuthUser(db.Model, UserMixin):
    """认证用户模型"""
    __tablename__ = 'auth_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 登录失败锁定相关字段
    login_attempts = db.Column(db.Integer, default=0, comment='登录失败次数')
    is_locked = db.Column(db.Boolean, default=False, comment='账户是否被锁定')
    locked_at = db.Column(db.DateTime, nullable=True, comment='账户锁定时间')
    unlock_at = db.Column(db.DateTime, nullable=True, comment='账户解锁时间')
    
    # 关系
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """检查用户是否有指定权限"""
        if not self.role or not self.role.permissions:
            return False
        return permission in self.role.permissions
    
    def is_account_locked(self):
        """检查账户是否被锁定"""
        if not self.is_locked:
            return False
        
        # 如果设置了自动解锁时间且已过期，则自动解锁
        if self.unlock_at and self.unlock_at < datetime.utcnow():
            self.unlock_account()
            return False
        
        return True
    
    def record_login_failure(self):
        """记录登录失败"""
        self.login_attempts += 1
        
        # 如果失败次数达到5次，锁定账户
        if self.login_attempts >= 5:
            self.lock_account()
        
        db.session.commit()
    
    def record_login_success(self):
        """记录登录成功，重置失败计数"""
        self.login_attempts = 0
        self.is_locked = False
        self.locked_at = None
        self.unlock_at = None
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def lock_account(self, lock_duration_hours=24):
        """锁定账户"""
        from datetime import timedelta
        self.is_locked = True
        self.locked_at = datetime.utcnow()
        self.unlock_at = datetime.utcnow() + timedelta(hours=lock_duration_hours)
        db.session.commit()
    
    def unlock_account(self):
        """解锁账户"""
        self.is_locked = False
        self.locked_at = None
        self.unlock_at = None
        self.login_attempts = 0
        db.session.commit()
    
    def get_remaining_lock_time(self):
        """获取剩余锁定时间（分钟）"""
        if not self.is_locked or not self.unlock_at:
            return 0
        
        remaining = self.unlock_at - datetime.utcnow()
        if remaining.total_seconds() <= 0:
            return 0
        
        return int(remaining.total_seconds() / 60)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.name if self.role else None,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_locked': self.is_locked,
            'login_attempts': self.login_attempts,
            'locked_at': self.locked_at.isoformat() if self.locked_at else None,
            'unlock_at': self.unlock_at.isoformat() if self.unlock_at else None
        }

class UserProfile(db.Model):
    """用户资料模型"""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id', ondelete='CASCADE'), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(100))
    position = db.Column(db.String(50))
    avatar = db.Column(db.String(255))  # 头像文件路径
    preferences = db.Column(db.JSON)  # 用户偏好设置
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserProfile {self.user_id}>'
    
    def get_full_name(self):
        """获取完整姓名"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return "未设置姓名"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'company': self.company,
            'position': self.position,
            'avatar': self.avatar,
            'preferences': self.preferences,
            'full_name': self.get_full_name()
        }

class InvitationCode(db.Model):
    """邀请码管理模型"""
    __tablename__ = 'invitation_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, comment='邀请码')
    role_name = db.Column(db.String(20), nullable=False, comment='角色名称 (staff/admin)')
    created_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False, comment='创建者ID')
    used_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='使用者ID')
    is_used = db.Column(db.Boolean, default=False, comment='是否已使用')
    expires_at = db.Column(db.DateTime, nullable=True, comment='过期时间')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    used_at = db.Column(db.DateTime, nullable=True, comment='使用时间')
    
    # 关系
    creator = db.relationship('AuthUser', foreign_keys=[created_by], backref='created_invitations')
    user = db.relationship('AuthUser', foreign_keys=[used_by], backref='used_invitation')
    
    def __repr__(self):
        return f'<InvitationCode {self.code}>'
    
    @staticmethod
    def generate_code(length=16):
        """生成随机邀请码"""
        import secrets
        import string
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    def is_valid(self):
        """检查邀请码是否有效"""
        if self.is_used:
            return False, "邀请码已被使用"
        
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False, "邀请码已过期"
        
        return True, "邀请码有效"
    
    def use_code(self, user_id):
        """使用邀请码"""
        if self.is_used:
            return False, "邀请码已被使用"
        
        self.is_used = True
        self.used_by = user_id
        self.used_at = datetime.utcnow()
        db.session.commit()
        return True, "邀请码使用成功"

# 初始化角色数据
def init_roles():
    """初始化角色数据"""
    roles_data = [
        {
            'name': 'admin',
            'description': '系统管理员，拥有所有权限',
            'permissions': [
                'manage_all_data',      # 管理全站数据
                'manage_users',         # 用户管理
                'manage_roles',         # 权限管理
                'manage_orders',        # 订单管理
                'publish_content',      # 内容发布
                'view_analytics',       # 查看统计
                'system_config'         # 系统配置
            ]
        },
        {
            'name': 'staff',
            'description': '公司员工，管理所属项目',
            'permissions': [
                'manage_own_projects',  # 管理所属项目
                'create_quotes',        # 新增报价
                'edit_quotes',          # 修改报价
                'upload_files',         # 上传文件
                'update_progress',      # 更新项目进度
                'view_own_orders'       # 查看相关订单
            ]
        },
        {
            'name': 'member',
            'description': '会员客户，可以下单查看订单',
            'permissions': [
                'view_own_orders',      # 查看自己的订单
                'place_orders',         # 下单
                'view_quotes',          # 查看报价
                'view_invoices',        # 查看发票
                'edit_profile'          # 编辑个人资料
            ]
        },
        {
            'name': 'guest',
            'description': '普通访客，只能浏览公开信息',
            'permissions': [
                'view_public_info',     # 浏览公开信息
                'view_visa_services',   # 查看签证服务
                'view_tour_packages'    # 查看旅游配套
            ]
        }
    ]
    
    for role_data in roles_data:
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(**role_data)
            db.session.add(role)
    
    db.session.commit()

def get_role_id(role_name):
    """根据角色名称获取角色ID"""
    role = Role.query.filter_by(name=role_name).first()
    return role.id if role else None

def create_default_admin():
    """创建默认管理员账户"""
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        return
    
    # 检查是否已存在管理员
    admin_user = AuthUser.query.filter_by(role_id=admin_role.id).first()
    if admin_user:
        return
    
    # 创建默认管理员
    admin_user = AuthUser(
        username='admin',
        email='admin@mytravelpanel.com',
        role_id=admin_role.id,
        is_active=True,
        is_verified=True
    )
    admin_user.set_password('admin123')
    
    # 先添加用户并提交，获取用户ID
    db.session.add(admin_user)
    db.session.commit()
    
    # 创建管理员资料
    admin_profile = UserProfile(
        user_id=admin_user.id,
        first_name='系统',
        last_name='管理员',
        company='MyTravelPanel',
        position='系统管理员'
    )
    
    db.session.add(admin_profile)
    db.session.commit() 