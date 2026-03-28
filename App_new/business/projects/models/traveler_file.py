# -*- coding: utf-8 -*-
"""常用旅客文件模型"""

import os
from App_new.exts import db
from datetime import datetime


class TravelerFile(db.Model):
    """常用旅客文件/附件 - 护照首页、IC、会员卡等"""
    __tablename__ = 'traveler_files'

    id = db.Column(db.Integer, primary_key=True)
    traveler_id = db.Column(db.Integer, db.ForeignKey('frequent_travelers.id', ondelete='CASCADE'), nullable=False, comment='旅客ID')

    # 文件分类
    file_category = db.Column(db.String(30), nullable=True, comment='文件分类: passport/ic/membership_card/visa/other')

    # 文件信息
    filename = db.Column(db.String(255), nullable=False, comment='原始文件名')
    stored_filename = db.Column(db.String(255), nullable=False, comment='存储文件名(UUID)')
    file_path = db.Column(db.String(500), nullable=False, comment='文件存储路径')
    file_size = db.Column(db.Integer, nullable=True, comment='文件大小(字节)')
    file_type = db.Column(db.String(100), nullable=True, comment='MIME类型')

    # 描述
    description = db.Column(db.String(200), nullable=True, comment='文件描述')

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    traveler = db.relationship('FrequentTraveler', backref=db.backref('files', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<TravelerFile {self.filename}>'

    @property
    def file_size_display(self):
        if not self.file_size:
            return '未知'
        if self.file_size < 1024:
            return f'{self.file_size} B'
        elif self.file_size < 1024 * 1024:
            return f'{self.file_size / 1024:.1f} KB'
        else:
            return f'{self.file_size / (1024 * 1024):.1f} MB'

    @property
    def file_extension(self):
        _, ext = os.path.splitext(self.filename)
        return ext.lower() if ext else ''

    @property
    def is_image(self):
        return self.file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

    @property
    def category_display(self):
        mapping = {
            'passport': '护照',
            'ic': 'IC/身份证',
            'membership_card': '会员卡',
            'visa': '签证页',
            'other': '其他',
        }
        return mapping.get(self.file_category, self.file_category or '其他')

    def to_dict(self):
        return {
            'id': self.id,
            'traveler_id': self.traveler_id,
            'file_category': self.file_category,
            'category_display': self.category_display,
            'filename': self.filename,
            'stored_filename': self.stored_filename,
            'file_size': self.file_size,
            'file_size_display': self.file_size_display,
            'file_type': self.file_type,
            'is_image': self.is_image,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
