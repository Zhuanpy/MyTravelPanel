from ..exts  import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(100), nullable=False)
    website_url = db.Column(db.String(500))  # 网址
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

    def __repr__(self):
        return f'<Account {self.platform}>'

    def __init__(self, platform, username, password, category=None, website_url=None, 
                 owner=None, country=None, region=None, description=None, notes=None,
                 file_materials=None, additional_info=None):
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

    def to_dict(self):
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
            'click_count': self.click_count
        } 