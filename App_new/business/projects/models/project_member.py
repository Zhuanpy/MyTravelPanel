# -*- coding: utf-8 -*-
"""项目人员模型"""

from App_new.exts import db
from datetime import datetime


class ProjectMember(db.Model):
    """项目人员关联表 - 一个项目可关联多个人员"""
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=False, comment='项目ID')
    
    # 人员信息
    title = db.Column(db.String(10), nullable=True, comment='称谓: MR/MS/MISS/MASTER')
    member_name = db.Column(db.String(100), nullable=False, comment='人员姓名')
    member_name_en = db.Column(db.String(100), nullable=True, comment='英文姓名')
    member_role = db.Column(db.String(50), nullable=True, comment='角色/职位')
    member_phone = db.Column(db.String(20), nullable=True, comment='联系电话')
    member_email = db.Column(db.String(100), nullable=True, comment='邮箱')
    
    # 证件信息
    id_type = db.Column(db.String(20), nullable=True, comment='证件类型: passport/id_card/other')
    id_number = db.Column(db.String(50), nullable=True, comment='证件号码')
    
    # Leader标识
    is_leader = db.Column(db.Boolean, default=False, nullable=False, comment='是否为Leader')
    
    # 其他
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ProjectMember {self.member_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'header_id': self.header_id,
            'title': self.title,
            'member_name': self.member_name,
            'member_name_en': self.member_name_en,
            'member_role': self.member_role,
            'member_phone': self.member_phone,
            'member_email': self.member_email,
            'id_type': self.id_type,
            'id_number': self.id_number,
            'is_leader': self.is_leader,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

