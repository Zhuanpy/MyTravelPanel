# -*- coding: utf-8 -*-
"""
供应商预付账款模型
用于管理航司账户充值等预付款项
"""

from App_new.exts import db
from datetime import datetime
from decimal import Decimal


class SupplierPrepayment(db.Model):
    """供应商预付账款表 - 记录每次充值"""
    __tablename__ = 'supplier_prepayments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prepayment_number = db.Column(db.String(30), unique=True, nullable=False, comment='预付编号')

    # 关联公司（supplier_id 重命名为指向 customer_companies）
    supplier_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id'), nullable=True, comment='供应商公司ID')

    # 预付信息
    amount = db.Column(db.Numeric(12, 2), nullable=False, comment='充值金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币')
    payment_date = db.Column(db.Date, nullable=False, comment='充值日期')
    payment_method = db.Column(db.Enum('bank_transfer', 'credit_card', 'cash', 'paynow', 'other'),
                               default='bank_transfer', nullable=False, comment='支付方式')

    # 余额信息
    balance_amount = db.Column(db.Numeric(12, 2), nullable=False, comment='剩余余额')

    # 银行账户（充值来源）
    bank_account_id = db.Column(db.Integer, db.ForeignKey('project_chart_of_accounts.id'),
                                nullable=True, comment='银行账户科目ID')

    # 预付科目（默认1201预付-航空公司）
    prepayment_account_id = db.Column(db.Integer, db.ForeignKey('project_chart_of_accounts.id'),
                                      nullable=True, comment='预付账款科目ID')

    # 状态
    status = db.Column(db.Enum('draft', 'confirmed', 'partial_used', 'consumed', 'cancelled'),
                       default='draft', nullable=False, comment='状态')

    # 日记账关联
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('project_journal_entries.id'),
                                 nullable=True, comment='日记账分录ID')

    # 核对状态
    is_reconciled = db.Column(db.Boolean, default=False, comment='是否已核对')
    reconciled_at = db.Column(db.DateTime, nullable=True, comment='核对时间')
    reconciled_by = db.Column(db.String(50), nullable=True, comment='核对人')

    # 备注
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    reference = db.Column(db.String(100), nullable=True, comment='参考号/交易号')

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    supplier = db.relationship('CustomerCompany', foreign_keys=[supplier_id], backref=db.backref('prepayments', lazy='dynamic'))
    bank_account = db.relationship('ChartOfAccount', foreign_keys=[bank_account_id])
    prepayment_account = db.relationship('ChartOfAccount', foreign_keys=[prepayment_account_id])
    usages = db.relationship('PrepaymentUsage', backref='prepayment', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def confirmed_usages(self):
        """只返回已确认的使用记录"""
        return self.usages.filter_by(status='confirmed')

    @property
    def company_name(self):
        """获取公司名称"""
        if self.supplier:
            return self.supplier.company_name
        return None

    def __repr__(self):
        return f'<SupplierPrepayment {self.prepayment_number}: {self.amount} {self.currency}>'

    @classmethod
    def generate_prepayment_number(cls):
        """生成预付编号，格式：SP + YYYYMMDD + 3位序号"""
        today = datetime.now().strftime('%Y%m%d')
        prefix = f'SP{today}'

        # 查找今天最后一个编号
        last_record = cls.query.filter(
            cls.prepayment_number.like(f'{prefix}%')
        ).order_by(cls.prepayment_number.desc()).first()

        if last_record:
            try:
                last_number = int(last_record.prepayment_number[-3:])
                new_number = str(last_number + 1).zfill(3)
            except ValueError:
                new_number = '001'
        else:
            new_number = '001'

        return f'{prefix}{new_number}'

    @property
    def used_amount(self):
        """已使用金额"""
        return self.amount - self.balance_amount

    @property
    def usage_percentage(self):
        """使用百分比"""
        if self.amount == 0:
            return 0
        return round((self.used_amount / self.amount) * 100, 2)

    @property
    def status_display(self):
        """状态显示"""
        status_map = {
            'draft': '草稿',
            'confirmed': '已确认',
            'partial_used': '部分使用',
            'consumed': '已用完',
            'cancelled': '已取消'
        }
        return status_map.get(self.status, self.status)

    @property
    def payment_method_display(self):
        """支付方式显示"""
        method_map = {
            'bank_transfer': '银行转账',
            'credit_card': '信用卡',
            'cash': '现金',
            'paynow': 'PayNow',
            'other': '其他'
        }
        return method_map.get(self.payment_method, self.payment_method)

    def update_status(self):
        """根据余额更新状态"""
        if self.status in ('cancelled', 'draft'):
            return

        if self.balance_amount <= 0:
            self.status = 'consumed'
        elif self.balance_amount < self.amount:
            self.status = 'partial_used'
        elif self.balance_amount == self.amount:
            # 余额完全恢复，状态回到confirmed
            self.status = 'confirmed'

    def use_amount(self, amount):
        """
        使用预付金额
        返回: (实际使用金额, 是否成功)
        """
        if self.status not in ('confirmed', 'partial_used'):
            return Decimal('0'), False

        amount = Decimal(str(amount))
        if amount <= 0:
            return Decimal('0'), False

        # 计算实际可用金额
        actual_use = min(amount, self.balance_amount)
        self.balance_amount -= actual_use
        self.update_status()

        return actual_use, True

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'prepayment_number': self.prepayment_number,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.company_name if self.supplier else None,
            'amount': float(self.amount),
            'balance_amount': float(self.balance_amount),
            'used_amount': float(self.used_amount),
            'usage_percentage': self.usage_percentage,
            'currency': self.currency,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'payment_method_display': self.payment_method_display,
            'status': self.status,
            'status_display': self.status_display,
            'remarks': self.remarks,
            'reference': self.reference,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PrepaymentUsage(db.Model):
    """预付账款使用明细表 - 记录每次从预付账户扣减"""
    __tablename__ = 'prepayment_usages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 关联预付记录
    prepayment_id = db.Column(db.Integer, db.ForeignKey('supplier_prepayments.id'), nullable=False, comment='预付记录ID')

    # 关联EO（可选，如果是通过EO使用）
    eo_id = db.Column(db.Integer, db.ForeignKey('project_eos.id'), nullable=True, comment='关联EO ID')

    # 关联REF（可选）
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=True, comment='关联REF ID')

    # 使用信息
    amount = db.Column(db.Numeric(12, 2), nullable=False, comment='使用金额')
    usage_date = db.Column(db.Date, nullable=False, comment='使用日期')
    description = db.Column(db.String(200), nullable=True, comment='使用说明')

    # 日记账关联
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('project_journal_entries.id'),
                                 nullable=True, comment='日记账分录ID')

    # 状态
    status = db.Column(db.Enum('pending', 'confirmed', 'reversed'),
                       default='pending', nullable=False, comment='状态')

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    eo = db.relationship('ProjectEO', backref=db.backref('prepayment_usages', lazy='dynamic'))
    ref = db.relationship('ProjectRef', backref=db.backref('prepayment_usages', lazy='dynamic'))

    def __repr__(self):
        return f'<PrepaymentUsage {self.id}: {self.amount}>'

    @property
    def status_display(self):
        """状态显示"""
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'reversed': '已冲销'
        }
        return status_map.get(self.status, self.status)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'prepayment_id': self.prepayment_id,
            'prepayment_number': self.prepayment.prepayment_number if self.prepayment else None,
            'eo_id': self.eo_id,
            'ref_id': self.ref_id,
            'amount': float(self.amount),
            'usage_date': self.usage_date.isoformat() if self.usage_date else None,
            'description': self.description,
            'status': self.status,
            'status_display': self.status_display,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
