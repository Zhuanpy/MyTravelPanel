# -*- coding: utf-8 -*-
"""银行交易匹配关联模型"""

from App_new.exts import db
from datetime import datetime


class BankTransactionMatch(db.Model):
    """
    银行交易匹配关联表
    支持多对多匹配：
    - 一笔银行转账 → 多个收款/EO
    - 多笔银行转账 → 一个收款/EO
    """
    __tablename__ = 'bank_transaction_matches'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('bank_transactions.id', ondelete='CASCADE'),
                              nullable=False, comment='银行交易ID')
    match_type = db.Column(db.Enum('receipt', 'eo', 'payment', 'prepayment', 'loan_borrow', 'loan_repay'), nullable=False,
                          comment='匹配类型：receipt=收款，eo=EO，payment=付款，prepayment=预付款，loan_borrow=股东借款，loan_repay=股东还款')
    match_id = db.Column(db.Integer, nullable=False,
                        comment='匹配记录ID（收款ID或EO ID）')
    allocated_amount = db.Column(db.Numeric(12, 2), nullable=False,
                                comment='分配金额')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    transaction = db.relationship('BankTransaction', backref=db.backref('matches', lazy='dynamic'))

    def __repr__(self):
        return f'<BankTransactionMatch {self.id}: tx={self.transaction_id} -> {self.match_type}:{self.match_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'match_type': self.match_type,
            'match_id': self.match_id,
            'allocated_amount': float(self.allocated_amount) if self.allocated_amount else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }

    @classmethod
    def get_receipt_matches(cls, receipt_id):
        """获取收款的所有匹配记录"""
        return cls.query.filter_by(match_type='receipt', match_id=receipt_id).all()

    @classmethod
    def get_eo_matches(cls, eo_id):
        """获取EO的所有匹配记录"""
        return cls.query.filter_by(match_type='eo', match_id=eo_id).all()

    @classmethod
    def get_payment_matches(cls, payment_id):
        """获取付款的所有匹配记录"""
        return cls.query.filter_by(match_type='payment', match_id=payment_id).all()

    @classmethod
    def get_prepayment_matches(cls, prepayment_id):
        """获取预付款的所有匹配记录"""
        return cls.query.filter_by(match_type='prepayment', match_id=prepayment_id).all()

    @classmethod
    def get_transaction_matches(cls, transaction_id):
        """获取银行交易的所有匹配记录"""
        return cls.query.filter_by(transaction_id=transaction_id).all()

    @classmethod
    def get_receipt_matched_amount(cls, receipt_id):
        """获取收款已匹配的总金额"""
        result = db.session.query(
            db.func.coalesce(db.func.sum(cls.allocated_amount), 0)
        ).filter_by(match_type='receipt', match_id=receipt_id).scalar()
        return float(result) if result else 0

    @classmethod
    def get_eo_matched_amount(cls, eo_id):
        """获取EO已匹配的总金额"""
        result = db.session.query(
            db.func.coalesce(db.func.sum(cls.allocated_amount), 0)
        ).filter_by(match_type='eo', match_id=eo_id).scalar()
        return float(result) if result else 0

    @classmethod
    def get_transaction_matched_amount(cls, transaction_id):
        """获取银行交易已匹配的总金额"""
        result = db.session.query(
            db.func.coalesce(db.func.sum(cls.allocated_amount), 0)
        ).filter_by(transaction_id=transaction_id).scalar()
        return float(result) if result else 0

    @classmethod
    def is_receipt_fully_matched(cls, receipt_id, receipt_amount):
        """检查收款是否已完全匹配"""
        matched = cls.get_receipt_matched_amount(receipt_id)
        return abs(matched - float(receipt_amount)) < 0.01

    @classmethod
    def is_eo_fully_matched(cls, eo_id, eo_amount):
        """检查EO是否已完全匹配"""
        matched = cls.get_eo_matched_amount(eo_id)
        return abs(matched - float(eo_amount)) < 0.01

    @classmethod
    def is_transaction_fully_matched(cls, transaction_id, transaction_amount):
        """检查银行交易是否已完全匹配"""
        matched = cls.get_transaction_matched_amount(transaction_id)
        return abs(matched - float(transaction_amount)) < 0.01
