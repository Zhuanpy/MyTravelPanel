# -*- coding: utf-8 -*-
"""对账相关模型 - 银行对账、供应商对账等"""

from ...exts import db
from datetime import datetime
import json


class BankStatement(db.Model):
    """银行对账单模型"""
    __tablename__ = 'bank_statements'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    statement_number = db.Column(db.String(50), unique=True, nullable=False, comment='对账单号')
    bank_name = db.Column(db.String(100), nullable=False, comment='银行名称')
    account_number = db.Column(db.String(50), nullable=False, comment='银行账号')
    account_name = db.Column(db.String(100), nullable=False, comment='账户名称')
    
    # 对账期间
    statement_date = db.Column(db.Date, nullable=False, comment='对账日期')
    period_start = db.Column(db.Date, nullable=False, comment='对账期间开始')
    period_end = db.Column(db.Date, nullable=False, comment='对账期间结束')
    
    # 余额信息
    opening_balance = db.Column(db.Numeric(15, 2), nullable=False, comment='期初余额')
    closing_balance = db.Column(db.Numeric(15, 2), nullable=False, comment='期末余额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='币种')
    
    # 状态和备注
    status = db.Column(db.Enum('draft', 'processing', 'completed', 'cancelled'),
                       default='draft', nullable=False, comment='对账状态')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    transactions = db.relationship('BankTransaction', backref='statement', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<BankStatement {self.statement_number} - {self.bank_name}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'statement_number': self.statement_number,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_name': self.account_name,
            'statement_date': self.statement_date.isoformat() if self.statement_date else None,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'opening_balance': float(self.opening_balance) if self.opening_balance else 0,
            'closing_balance': float(self.closing_balance) if self.closing_balance else 0,
            'currency': self.currency,
            'status': self.status,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

    @property
    def total_debit_amount(self):
        """总借方金额"""
        return sum(t.amount for t in self.transactions if t.transaction_type == 'debit')

    @property
    def total_credit_amount(self):
        """总贷方金额"""
        return sum(t.amount for t in self.transactions if t.transaction_type == 'credit')

    @property
    def transaction_count(self):
        """交易笔数"""
        return len(self.transactions)


class BankTransaction(db.Model):
    """银行交易记录模型"""
    __tablename__ = 'bank_transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    statement_id = db.Column(db.Integer, db.ForeignKey('bank_statements.id'), nullable=False, comment='对账单ID')
    transaction_date = db.Column(db.Date, nullable=False, comment='交易日期')
    transaction_id = db.Column(db.String(100), nullable=True, comment='银行交易流水号')
    
    # 交易信息
    transaction_type = db.Column(db.Enum('debit', 'credit'), nullable=False, comment='交易类型：借方/贷方')
    amount = db.Column(db.Numeric(15, 2), nullable=False, comment='交易金额')
    balance = db.Column(db.Numeric(15, 2), nullable=True, comment='余额')
    description = db.Column(db.Text, nullable=True, comment='交易描述')
    
    # 对方信息
    counterparty_name = db.Column(db.String(200), nullable=True, comment='对方名称')
    counterparty_account = db.Column(db.String(50), nullable=True, comment='对方账号')
    
    # 对账状态
    reconciliation_status = db.Column(db.Enum('unmatched', 'matched', 'disputed'),
                                      default='unmatched', nullable=False, comment='对账状态')
    matched_receipt_id = db.Column(db.Integer, db.ForeignKey('project_receipts.id'), nullable=True, comment='匹配的收款记录ID')
    
    # 账务关联（REF/EO）与检索
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=True, comment='关联REF ID')
    eo_id = db.Column(db.Integer, db.ForeignKey('project_eos.id'), nullable=True, comment='关联EO ID')
    accounting_ref = db.Column(db.String(100), nullable=True, comment='账务参考编号(REF/EO 编号)')
    keyword = db.Column(db.String(255), nullable=True, index=True, comment='识别关键字')
    
    # 去重指纹（基于特征生成）
    tx_fingerprint = db.Column(db.String(64), unique=True, nullable=True, comment='去重指纹')
    
    # 使用者归属
    owner_label = db.Column(db.String(100), nullable=True, comment='归属标签：JE公司/LG公司/个人商用/个人消费等')
    owner_type = db.Column(db.Enum('company', 'personal', 'personal_business', 'other'),
                           default='other', nullable=False, comment='归属类型')
    
    # 备注信息
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    extra_info = db.Column(db.Text, nullable=True, comment='额外信息(JSON)')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    matched_receipt = db.relationship('ProjectReceipt', backref='bank_transactions')

    def __repr__(self):
        return f'<BankTransaction {self.transaction_date} - {self.amount}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'statement_id': self.statement_id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'transaction_id': self.transaction_id,
            'transaction_type': self.transaction_type,
            'amount': float(self.amount) if self.amount else 0,
            'balance': float(self.balance) if self.balance else None,
            'description': self.description,
            'counterparty_name': self.counterparty_name,
            'counterparty_account': self.counterparty_account,
            'reconciliation_status': self.reconciliation_status,
            'matched_receipt_id': self.matched_receipt_id,
            'ref_id': self.ref_id,
            'eo_id': self.eo_id,
            'accounting_ref': self.accounting_ref,
            'keyword': self.keyword,
            'tx_fingerprint': self.tx_fingerprint,
            'owner_label': self.owner_label,
            'owner_type': self.owner_type,
            'remarks': self.remarks,
            'extra_info': json.loads(self.extra_info) if self.extra_info else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def reconciliation_status_display(self):
        """对账状态显示文本"""
        status_map = {
            'unmatched': '未匹配',
            'matched': '已匹配',
            'disputed': '有争议'
        }
        return status_map.get(self.reconciliation_status, self.reconciliation_status)


class SupplierStatement(db.Model):
    """供应商对账单模型"""
    __tablename__ = 'supplier_statements'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    statement_number = db.Column(db.String(50), unique=True, nullable=False, comment='对账单号')
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False, comment='供应商ID')
    
    # 对账期间
    statement_date = db.Column(db.Date, nullable=False, comment='对账日期')
    period_start = db.Column(db.Date, nullable=False, comment='对账期间开始')
    period_end = db.Column(db.Date, nullable=False, comment='对账期间结束')
    
    # 金额信息
    total_amount = db.Column(db.Numeric(15, 2), nullable=False, comment='总金额')
    paid_amount = db.Column(db.Numeric(15, 2), default=0, comment='已付金额')
    unpaid_amount = db.Column(db.Numeric(15, 2), default=0, comment='未付金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='币种')
    
    # 状态和备注
    status = db.Column(db.Enum('draft', 'sent', 'confirmed', 'disputed', 'closed'),
                       default='draft', nullable=False, comment='对账状态')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    # supplier = db.relationship('Supplier', backref='statements')  # 暂时注释掉，避免循环导入
    items = db.relationship('SupplierStatementItem', backref='statement', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<SupplierStatement {self.statement_number}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'statement_number': self.statement_number,
            'supplier_id': self.supplier_id,
            'statement_date': self.statement_date.isoformat() if self.statement_date else None,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0,
            'unpaid_amount': float(self.unpaid_amount) if self.unpaid_amount else 0,
            'currency': self.currency,
            'status': self.status,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

    @property
    def status_display(self):
        """状态显示文本"""
        status_map = {
            'draft': '草稿',
            'sent': '已发送',
            'confirmed': '已确认',
            'disputed': '有争议',
            'closed': '已关闭'
        }
        return status_map.get(self.status, self.status)

    @property
    def payment_rate(self):
        """付款比例"""
        if self.total_amount and self.total_amount > 0:
            return (float(self.paid_amount) / float(self.total_amount)) * 100
        return 0


class SupplierStatementItem(db.Model):
    """供应商对账单明细模型"""
    __tablename__ = 'supplier_statement_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    statement_id = db.Column(db.Integer, db.ForeignKey('supplier_statements.id'), nullable=False, comment='对账单ID')
    eo_id = db.Column(db.Integer, db.ForeignKey('project_eos.id'), nullable=True, comment='关联EO ID')
    
    # 明细信息
    item_type = db.Column(db.Enum('eo', 'adjustment', 'payment'), nullable=False, comment='明细类型')
    description = db.Column(db.String(200), nullable=False, comment='描述')
    amount = db.Column(db.Numeric(15, 2), nullable=False, comment='金额')
    
    # 状态信息
    status = db.Column(db.Enum('pending', 'confirmed', 'disputed'),
                       default='pending', nullable=False, comment='状态')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    eo = db.relationship('ProjectEO', backref='statement_items')

    def __repr__(self):
        return f'<SupplierStatementItem {self.description} - {self.amount}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'statement_id': self.statement_id,
            'eo_id': self.eo_id,
            'item_type': self.item_type,
            'description': self.description,
            'amount': float(self.amount) if self.amount else 0,
            'status': self.status,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# finance相关模型...
