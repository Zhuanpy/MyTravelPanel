# -*- coding: utf-8 -*-
"""退款相关模型 - 项目退款记录（面向客户的退款凭证，项目级别）

说明：
- 退款针对项目（header），一次退款可包含多条 REF 明细（ProjectRefundItem）。
- 仅用于生成"退款凭证 / Refund Confirmation"打印文档，
  不自动冲减收款或影响 REF/项目结算状态（财务打通为后续需求）。
"""

from App_new.exts import db
from datetime import datetime


class ProjectRefund(db.Model):
    """项目退款记录表（项目级别，含多条 REF 明细）"""
    __tablename__ = 'project_refunds'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    refund_number = db.Column(db.String(30), unique=True, nullable=False, comment='退款单号')
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=False, comment='项目主表ID')

    # 退款汇总信息
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, comment='退款总金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币类型')
    refund_method = db.Column(db.Enum('cash', 'bank_transfer', 'credit_card', 'cheque', 'wechat', 'other'),
                              default='bank_transfer', nullable=False, comment='退款方式')
    refund_date = db.Column(db.Date, nullable=False, comment='退款日期')

    # 收款方（退给谁）信息
    payee_name = db.Column(db.String(100), nullable=True, comment='退款收款人/客户姓名')
    payee_contact = db.Column(db.String(50), nullable=True, comment='收款人联系方式')

    # 退款原因和备注
    reason = db.Column(db.String(255), nullable=True, comment='退款原因')
    remarks = db.Column(db.Text, nullable=True, comment='备注')

    # 状态
    status = db.Column(db.Enum('confirmed', 'cancelled'),
                       default='confirmed', nullable=False, comment='退款状态')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    header = db.relationship('ProjectHeader', backref='refunds')
    items = db.relationship('ProjectRefundItem', back_populates='refund',
                            cascade='all, delete-orphan', order_by='ProjectRefundItem.id')

    def __repr__(self):
        return f'<ProjectRefund {self.refund_number}: {self.amount} {self.currency}>'

    def to_dict(self):
        return {
            'id': self.id,
            'refund_number': self.refund_number,
            'header_id': self.header_id,
            'amount': float(self.amount) if self.amount else 0,
            'currency': self.currency,
            'refund_method': self.refund_method,
            'refund_date': self.refund_date.isoformat() if self.refund_date else None,
            'payee_name': self.payee_name,
            'payee_contact': self.payee_contact,
            'reason': self.reason,
            'remarks': self.remarks,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'items': [it.to_dict() for it in self.items],
        }

    @classmethod
    def generate_refund_number(cls):
        """生成退款单号，格式: RF + 年月日 + 3位序号，例如: RF20260616001"""
        today = datetime.now().strftime('%Y%m%d')
        prefix = f'RF{today}'

        last = cls.query.filter(
            cls.refund_number.like(f'{prefix}%')
        ).order_by(cls.refund_number.desc()).first()

        if last:
            try:
                new_seq = str(int(last.refund_number[-3:]) + 1).zfill(3)
            except ValueError:
                new_seq = '001'
        else:
            new_seq = '001'

        return f'{prefix}{new_seq}'

    @property
    def refund_method_display(self):
        """退款方式中文显示"""
        method_map = {
            'cash': '现金',
            'bank_transfer': '银行转账',
            'credit_card': '信用卡',
            'cheque': '支票',
            'wechat': 'WeChat',
            'other': '其他',
        }
        return method_map.get(self.refund_method, self.refund_method)

    @property
    def refund_method_display_en(self):
        """退款方式英文显示（用于面向客户的凭证）"""
        method_map = {
            'cash': 'Cash',
            'bank_transfer': 'Bank Transfer',
            'credit_card': 'Credit Card',
            'cheque': 'Cheque',
            'wechat': 'WeChat',
            'other': 'Other',
        }
        return method_map.get(self.refund_method, self.refund_method)

    @property
    def status_display(self):
        """状态中文显示"""
        return {'confirmed': '已确认', 'cancelled': '已取消'}.get(self.status, self.status)


class ProjectRefundItem(db.Model):
    """退款明细表（一条退款下的多个 REF 明细）"""
    __tablename__ = 'project_refund_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    refund_id = db.Column(db.Integer, db.ForeignKey('project_refunds.id', ondelete='CASCADE'),
                          nullable=False, comment='退款记录ID')
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False, comment='REF明细ID')

    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, comment='该REF退款金额')
    original_ticket_no = db.Column(db.String(100), nullable=True, comment='原票号')
    flight_info = db.Column(db.String(255), nullable=True, comment='航班/行程信息')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    refund = db.relationship('ProjectRefund', back_populates='items')
    ref = db.relationship('ProjectRef')

    def __repr__(self):
        return f'<ProjectRefundItem refund={self.refund_id} ref={self.ref_id}: {self.amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'refund_id': self.refund_id,
            'ref_id': self.ref_id,
            'amount': float(self.amount) if self.amount else 0,
            'original_ticket_no': self.original_ticket_no,
            'flight_info': self.flight_info,
        }
