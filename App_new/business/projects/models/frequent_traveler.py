# -*- coding: utf-8 -*-
"""常用旅客模型"""

from App_new.exts import db
from datetime import datetime


class FrequentTraveler(db.Model):
    """常用旅客表 - 保存常用客人信息，可快速添加到项目人员"""
    __tablename__ = 'frequent_travelers'

    id = db.Column(db.Integer, primary_key=True)

    # 基本信息
    title = db.Column(db.String(10), nullable=True, comment='称谓: MR/MS/MISS/MASTER')
    name = db.Column(db.String(100), nullable=False, comment='姓名')
    name_en = db.Column(db.String(100), nullable=True, comment='英文姓名')
    gender = db.Column(db.String(10), nullable=True, comment='性别: male/female')
    date_of_birth = db.Column(db.Date, nullable=True, comment='出生日期')
    nationality = db.Column(db.String(50), nullable=True, comment='国籍')

    # 联系信息
    phone = db.Column(db.String(30), nullable=True, comment='联系电话')
    email = db.Column(db.String(100), nullable=True, comment='邮箱')

    # 护照信息
    passport_number = db.Column(db.String(50), nullable=True, comment='护照号码')
    passport_issuing_country = db.Column(db.String(50), nullable=True, comment='护照签发国')
    passport_expiry_date = db.Column(db.Date, nullable=True, comment='护照有效期')

    # 其他证件
    id_card_number = db.Column(db.String(50), nullable=True, comment='身份证号码')

    # 航空会员信息（JSON格式存储多个航空公司会员）
    airline_memberships = db.Column(db.Text, nullable=True, comment='航空会员信息，JSON格式')

    # 关联公司（可选，便于按公司筛选常用旅客）
    company_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id'), nullable=True, comment='关联客户公司ID')

    # 集团/关联标签（与 CustomerCompany.group_name 同风格的字符串标签；
    # 可由公司 group_name 自动回填，也支持无公司时直接打标签）
    group_name = db.Column(db.String(100), nullable=True, comment='集团/关联标签')

    # 备注
    remarks = db.Column(db.Text, nullable=True, comment='备注')

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    company = db.relationship('CustomerCompany', backref='frequent_travelers', lazy=True)

    def __repr__(self):
        return f'<FrequentTraveler {self.name}>'

    def to_dict(self):
        import json
        memberships = []
        if self.airline_memberships:
            try:
                memberships = json.loads(self.airline_memberships)
            except (json.JSONDecodeError, TypeError):
                memberships = []

        return {
            'id': self.id,
            'title': self.title,
            'name': self.name,
            'name_en': self.name_en,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'nationality': self.nationality,
            'phone': self.phone,
            'email': self.email,
            'passport_number': self.passport_number,
            'passport_issuing_country': self.passport_issuing_country,
            'passport_expiry_date': self.passport_expiry_date.isoformat() if self.passport_expiry_date else None,
            'id_card_number': self.id_card_number,
            'airline_memberships': memberships,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'group_name': self.group_name or (self.company.group_name if self.company else None),
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
