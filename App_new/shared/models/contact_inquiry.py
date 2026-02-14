# -*- coding: utf-8 -*-
"""
客户在线咨询模型
"""
from App_new.exts import db
from datetime import datetime


class ContactInquiry(db.Model):
    """客户咨询记录"""
    __tablename__ = 'contact_inquiries'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='客户姓名')
    phone = db.Column(db.String(30), nullable=False, comment='客户电话')
    email = db.Column(db.String(150), nullable=False, comment='客户邮箱')
    service_type = db.Column(db.String(50), nullable=True, comment='服务类型: visa/tour/flight/hotel/other')
    message = db.Column(db.Text, nullable=False, comment='咨询内容')

    # 状态管理
    status = db.Column(db.String(20), default='new', nullable=False, comment='状态: new/read/replied/closed')

    # 员工处理
    assigned_to = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='分配给的员工ID')
    staff_notes = db.Column(db.Text, nullable=True, comment='内部备注')

    # 访客信息
    ip_address = db.Column(db.String(50), nullable=True, comment='客户IP地址')
    user_agent = db.Column(db.String(500), nullable=True, comment='客户浏览器信息')

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='提交时间')
    read_at = db.Column(db.DateTime, nullable=True, comment='已读时间')
    replied_at = db.Column(db.DateTime, nullable=True, comment='回复时间')

    # 关系
    assignee = db.relationship('AuthUser', foreign_keys=[assigned_to], backref='assigned_inquiries')

    # 服务类型映射
    SERVICE_TYPE_MAP = {
        'visa': '签证申请',
        'tour': '旅游配套',
        'flight': '机票预订',
        'hotel': '酒店预订',
        'other': '其他服务',
    }

    STATUS_MAP = {
        'new': '新咨询',
        'read': '已读',
        'replied': '已回复',
        'closed': '已关闭',
    }

    @property
    def service_type_display(self):
        return self.SERVICE_TYPE_MAP.get(self.service_type, self.service_type or '未选择')

    @property
    def status_display(self):
        return self.STATUS_MAP.get(self.status, self.status)

    def __repr__(self):
        return f'<ContactInquiry {self.id} - {self.name}>'
