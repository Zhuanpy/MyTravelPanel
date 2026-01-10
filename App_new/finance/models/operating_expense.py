# -*- coding: utf-8 -*-
"""运营费用模型 - Operating Expense（付款给运营成本，不关联项目）"""

from App_new.exts import db
from datetime import datetime
from decimal import Decimal


class OperatingExpense(db.Model):
    """运营费用单 - 用于记录日常运营支出（租金、工资、水电等）"""
    __tablename__ = 'operating_expenses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    expense_number = db.Column(db.String(30), unique=True, nullable=False, comment='费用单编号')

    # 费用信息
    expense_date = db.Column(db.Date, nullable=False, comment='费用日期')
    expense_account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=False, comment='费用科目ID')

    # 金额信息
    amount = db.Column(db.Numeric(12, 2), nullable=False, comment='金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币')

    # 付款信息
    payment_method = db.Column(db.Enum('cash', 'bank_transfer', 'cheque', 'credit_card', 'other'),
                               default='bank_transfer', nullable=False, comment='付款方式')
    bank_account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=True, comment='付款银行科目ID')
    payment_reference = db.Column(db.String(100), nullable=True, comment='付款参考号')

    # 收款方信息
    payee_name = db.Column(db.String(100), nullable=True, comment='收款方名称')
    payee_account = db.Column(db.String(100), nullable=True, comment='收款方账号')

    # 描述和备注
    description = db.Column(db.String(200), nullable=False, comment='费用描述')
    remarks = db.Column(db.Text, nullable=True, comment='备注')

    # 附件
    attachment_path = db.Column(db.String(255), nullable=True, comment='附件路径')

    # 状态
    status = db.Column(db.Enum('draft', 'confirmed', 'paid', 'cancelled'),
                       default='draft', nullable=False, comment='状态')

    # 日记账关联
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=True, comment='日记账分录ID')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系 - 使用字符串形式指定外键，避免循环引用问题
    expense_account = db.relationship(
        'ChartOfAccount',
        foreign_keys='OperatingExpense.expense_account_id',
        backref=db.backref('expense_records', lazy='dynamic')
    )
    bank_account = db.relationship(
        'ChartOfAccount',
        foreign_keys='OperatingExpense.bank_account_id',
        backref=db.backref('bank_expense_records', lazy='dynamic')
    )
    journal_entry = db.relationship(
        'JournalEntry',
        backref=db.backref('operating_expense_record', uselist=False)
    )

    def __repr__(self):
        return f'<OperatingExpense {self.expense_number}: {self.amount} {self.currency}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'expense_number': self.expense_number,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'expense_account_id': self.expense_account_id,
            'expense_account_name': self.expense_account.name if self.expense_account else None,
            'expense_account_code': self.expense_account.code if self.expense_account else None,
            'amount': float(self.amount) if self.amount else 0,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'bank_account_id': self.bank_account_id,
            'bank_account_name': self.bank_account.name if self.bank_account else None,
            'payment_reference': self.payment_reference,
            'payee_name': self.payee_name,
            'payee_account': self.payee_account,
            'description': self.description,
            'remarks': self.remarks,
            'status': self.status,
            'journal_entry_id': self.journal_entry_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

    @staticmethod
    def generate_expense_number():
        """生成费用单编号，格式：OE-YYYYMMDD-XXXX"""
        today = datetime.now()
        prefix = f"OE-{today.strftime('%Y%m%d')}"

        # 查找今天最大的编号
        last_expense = OperatingExpense.query.filter(
            OperatingExpense.expense_number.like(f'{prefix}%')
        ).order_by(OperatingExpense.expense_number.desc()).first()

        if last_expense:
            last_num = int(last_expense.expense_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}-{new_num:04d}"

    @property
    def formatted_amount(self):
        """格式化金额显示"""
        return f"{self.currency} {float(self.amount):,.2f}"

    @property
    def status_display(self):
        """状态显示"""
        status_map = {
            'draft': 'Draft 草稿',
            'confirmed': 'Confirmed 已确认',
            'paid': 'Paid 已付款',
            'cancelled': 'Cancelled 已取消'
        }
        return status_map.get(self.status, self.status)

    @property
    def payment_method_display(self):
        """付款方式显示"""
        method_map = {
            'cash': 'Cash 现金',
            'bank_transfer': 'Bank Transfer 银行转账',
            'cheque': 'Cheque 支票',
            'credit_card': 'Credit Card 信用卡',
            'other': 'Other 其他'
        }
        return method_map.get(self.payment_method, self.payment_method)
