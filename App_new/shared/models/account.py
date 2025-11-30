from App_new.exts import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

# 访问权限级别常量
ACCESS_LEVEL_PRIVATE = 'private'      # 仅创建者可见
ACCESS_LEVEL_LEVEL_1 = 'level_1'      # 1级及以上员工可见
ACCESS_LEVEL_LEVEL_2 = 'level_2'      # 2级员工可见
ACCESS_LEVEL_PUBLIC = 'public'        # 所有员工可见

ACCESS_LEVEL_CHOICES = [
    (ACCESS_LEVEL_PRIVATE, '仅自己可见'),
    (ACCESS_LEVEL_LEVEL_1, '1级及以上员工可见'),
    (ACCESS_LEVEL_LEVEL_2, '2级员工可见'),
    (ACCESS_LEVEL_PUBLIC, '所有员工可见'),
]

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(100), nullable=False)
    website_url = db.Column(db.String(2000))  # 网址
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    owner = db.Column(db.String(100))  # 账户归属
    country = db.Column(db.String(100))  # 国家
    region = db.Column(db.String(100))   # 地区
    description = db.Column(db.Text)      # 详细介绍
    notes = db.Column(db.Text)           # 备注
    file_materials = db.Column(db.Text)  # 文件资料，存储为JSON格式
    additional_info = db.Column(db.Text)  # 补充信息，存储为JSON格式
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    click_count = db.Column(db.Integer, default=0)  # 添加点击统计字段
    
    # 访问权限级别字段
    access_level = db.Column(db.String(20), default=ACCESS_LEVEL_PRIVATE, nullable=False, comment='访问权限级别')
    # 创建者用户ID（用于私有权限判断）
    created_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='创建者用户ID')
    
    # 供应商关联字段 - 一个账号可以属于一个供应商或没有供应商
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=True, comment='关联的供应商ID')
    
    # 关联关系
    supplier = db.relationship('Supplier', backref='accounts', foreign_keys=[supplier_id])
    
    @property
    def creator(self):
        """获取创建者用户对象"""
        if self.created_by:
            from App_new.auth.models.User import User
            return User.query.get(self.created_by)
        return None

    def __repr__(self):
        return f'<Account {self.platform}>'

    def __init__(self, platform, username, password, category=None, website_url=None, 
                 owner=None, country=None, region=None, description=None, notes=None,
                 file_materials=None, additional_info=None, supplier_id=None,
                 access_level=None, created_by=None):
        self.platform = platform
        self.website_url = website_url
        self.username = username
        self.password = password
        self.category = category
        self.owner = owner
        self.country = country
        self.region = region
        self.description = description
        self.notes = notes
        self.file_materials = file_materials
        self.additional_info = additional_info
        self.supplier_id = supplier_id
        self.access_level = access_level or ACCESS_LEVEL_PRIVATE
        self.created_by = created_by

    def to_dict(self):
        # 获取访问权限显示名称
        access_level_display = dict(ACCESS_LEVEL_CHOICES).get(self.access_level, '仅自己可见')
        
        return {
            'id': self.id,
            'platform': self.platform,
            'website_url': self.website_url,
            'username': self.username,
            'password': self.password,
            'category': self.category,
            'owner': self.owner,
            'country': self.country,
            'region': self.region,
            'description': self.description,
            'notes': self.notes,
            'file_materials': json.loads(self.file_materials) if self.file_materials else [],
            'additional_info': json.loads(self.additional_info) if self.additional_info else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'click_count': self.click_count,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'access_level': self.access_level or ACCESS_LEVEL_PRIVATE,
            'access_level_display': access_level_display,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None
        }
    
    def can_access(self, user):
        """检查用户是否有权限访问此账号"""
        # 管理员可以访问所有账号
        if user.role and user.role.name in ['admin', 'super_admin']:
            return True
        
        # 获取用户的员工等级
        staff_level = 1  # 默认等级
        if user.profile:
            staff_level = user.profile.staff_level or 1
        
        access_level = self.access_level or ACCESS_LEVEL_PRIVATE
        
        # 私有权限：仅创建者可见（默认）
        if access_level == ACCESS_LEVEL_PRIVATE:
            return self.created_by == user.id or self.owner == user.username
        
        # 公开权限：所有员工可见
        if access_level == ACCESS_LEVEL_PUBLIC:
            return True
        
        # 1级员工权限
        if access_level == ACCESS_LEVEL_LEVEL_1:
            return staff_level >= 1
        
        # 2级员工权限
        if access_level == ACCESS_LEVEL_LEVEL_2:
            return staff_level >= 2
        
        return False 