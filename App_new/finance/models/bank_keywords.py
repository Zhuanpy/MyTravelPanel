# -*- coding: utf-8 -*-
"""
银行账单关键词模型
用于存储和管理各银行的关键词数据，替代原有的txt文件读取方式
"""

from App_new.exts import db
from datetime import datetime


class BankStatementKeyword(db.Model):
    """银行账单关键词表"""
    __tablename__ = 'bank_statements_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(50), nullable=False, comment='银行名称')
    keyword_type = db.Column(db.String(50), nullable=False, comment='关键词类型：personal_business, business, personal, other')
    keyword = db.Column(db.String(200), nullable=False, comment='关键词内容')
    description = db.Column(db.String(500), comment='关键词描述')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引
    __table_args__ = (
        db.Index('idx_bank_type', 'bank_name', 'keyword_type'),
        db.Index('idx_keyword', 'keyword'),
        db.UniqueConstraint('bank_name', 'keyword', name='uq_bank_keyword'),
    )
    
    def __repr__(self):
        return f'<BankStatementKeyword {self.bank_name}:{self.keyword_type}:{self.keyword}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'keyword_type': self.keyword_type,
            'keyword': self.keyword,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class BankKeywordCategory(db.Model):
    """银行关键词分类表"""
    __tablename__ = 'bank_keyword_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(50), nullable=False, comment='银行名称')
    category_name = db.Column(db.String(100), nullable=False, comment='分类名称')
    category_type = db.Column(db.String(50), nullable=False, comment='分类类型：personal_business, business, personal, other')
    description = db.Column(db.String(500), comment='分类描述')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 索引
    __table_args__ = (
        db.Index('idx_bank_category', 'bank_name', 'category_type'),
        db.UniqueConstraint('bank_name', 'category_name', name='uq_bank_category'),
    )
    
    def __repr__(self):
        return f'<BankKeywordCategory {self.bank_name}:{self.category_name}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'category_name': self.category_name,
            'category_type': self.category_type,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

