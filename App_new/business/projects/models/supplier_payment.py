# -*- coding: utf-8 -*-
"""
供应商付款记录模型
用于记录每次向供应商的付款（批量付款）
"""

from App_new.exts import db
from datetime import datetime, date
from decimal import Decimal


class SupplierPayment(db.Model):
    """供应商付款记录表 - 记录每次批量付款"""
    __tablename__ = 'supplier_payments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    payment_no = db.Column(db.String(30), unique=True, nullable=False, comment='付款编号')

    # 关联供应商
    supplier_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id'), nullable=True, comment='供应商ID')

    # 付款信息
    payment_date = db.Column(db.Date, nullable=False, comment='付款日期')
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0, comment='付款总金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币')

    # 付款来源
    payment_source = db.Column(db.Enum('bank', 'prepayment', 'mixed'),
                               default='bank', nullable=False, comment='付款来源：银行/预付账款/混合')

    # 银行付款信息
    payment_voucher_no = db.Column(db.String(50), nullable=True, comment='银行付款凭证号')
    bank_account_id = db.Column(db.Integer, db.ForeignKey('project_chart_of_accounts.id'),
                                nullable=True, comment='付款银行账户')

    # 预付账款信息（如果使用预付账款）
    prepayment_amount = db.Column(db.Numeric(12, 2), default=0, comment='使用预付账款金额')

    # EO 数量统计
    eo_count = db.Column(db.Integer, default=0, comment='包含EO数量')

    # 状态
    status = db.Column(db.Enum('draft', 'confirmed', 'cancelled'),
                       default='confirmed', nullable=False, comment='状态')

    # 备注
    remarks = db.Column(db.Text, nullable=True, comment='备注')

    # 日记账关联
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('project_journal_entries.id'),
                                 nullable=True, comment='日记账分录ID')

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    supplier = db.relationship('CustomerCompany', foreign_keys=[supplier_id],
                               backref=db.backref('payments', lazy='dynamic'))
    bank_account = db.relationship('ChartOfAccount', foreign_keys=[bank_account_id])
    eos = db.relationship('ProjectEO', backref='payment_record', lazy='dynamic',
                          foreign_keys='ProjectEO.payment_record_id')

    def __repr__(self):
        return f'<SupplierPayment {self.payment_no}: {self.total_amount} {self.currency}>'

    @classmethod
    def generate_payment_no(cls):
        """生成付款编号，格式：PAY + YYYYMMDD + 3位序号"""
        today = datetime.now().strftime('%Y%m%d')
        prefix = f'PAY{today}'

        # 查找今天最后一个编号
        last_record = cls.query.filter(
            cls.payment_no.like(f'{prefix}%')
        ).order_by(cls.payment_no.desc()).first()

        if last_record:
            try:
                last_number = int(last_record.payment_no[-3:])
                new_number = str(last_number + 1).zfill(3)
            except ValueError:
                new_number = '001'
        else:
            new_number = '001'

        return f'{prefix}{new_number}'

    @property
    def status_display(self):
        """状态显示"""
        status_map = {
            'draft': '草稿',
            'confirmed': '已确认',
            'cancelled': '已取消'
        }
        return status_map.get(self.status, self.status)

    @property
    def payment_source_display(self):
        """付款来源显示"""
        source_map = {
            'bank': '银行付款',
            'prepayment': '预付账款',
            'mixed': '混合付款'
        }
        return source_map.get(self.payment_source, self.payment_source)

    @property
    def supplier_name(self):
        """获取供应商名称"""
        return self.supplier.company_name if self.supplier else None

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'payment_no': self.payment_no,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier_name,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'total_amount': float(self.total_amount),
            'currency': self.currency,
            'payment_source': self.payment_source,
            'payment_source_display': self.payment_source_display,
            'payment_voucher_no': self.payment_voucher_no,
            'prepayment_amount': float(self.prepayment_amount) if self.prepayment_amount else 0,
            'eo_count': self.eo_count,
            'status': self.status,
            'status_display': self.status_display,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }
