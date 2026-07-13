# -*- coding: utf-8 -*-
"""股东借款模型"""

from datetime import datetime
from App_new.exts import db


class ShareholderLoan(db.Model):
    """股东借款记录"""
    __tablename__ = 'shareholder_loans'

    id = db.Column(db.Integer, primary_key=True)

    # 借款信息
    loan_number = db.Column(db.String(50), unique=True, nullable=False, comment='借款编号')
    amount = db.Column(db.Numeric(12, 2), nullable=False, comment='借款金额')
    loan_date = db.Column(db.Date, nullable=False, comment='借款日期')
    description = db.Column(db.String(200), comment='借款说明')
    remarks = db.Column(db.Text, comment='备注')

    # 还款跟踪
    repaid_amount = db.Column(db.Numeric(12, 2), default=0, comment='已还金额')
    status = db.Column(db.String(20), default='active', comment='状态: draft/active/partial/repaid/cancelled')

    # 关联会计分录
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('project_journal_entries.id'), comment='关联会计分录')
    bank_account_id = db.Column(db.Integer, db.ForeignKey('project_chart_of_accounts.id'), comment='存入银行账户')

    # 核对状态（银行对账用）
    is_reconciled = db.Column(db.Boolean, default=False, comment='是否已与银行记录核对')
    reconciled_at = db.Column(db.DateTime, comment='核对时间')
    reconciled_by = db.Column(db.String(50), comment='核对人')

    # 审计字段
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)

    # 关系
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])
    bank_account = db.relationship('ChartOfAccount', foreign_keys=[bank_account_id])
    repayment_details = db.relationship('ShareholderLoanRepaymentDetail', back_populates='loan', lazy='dynamic')

    @property
    def remaining_amount(self):
        """未还金额"""
        return float(self.amount) - float(self.repaid_amount or 0)

    @property
    def status_display(self):
        """状态显示"""
        status_map = {
            'draft': '待确认',
            'active': '未还',
            'partial': '部分归还',
            'repaid': '已还清',
            'cancelled': '已冲销'
        }
        return status_map.get(self.status, self.status)

    @property
    def is_draft(self):
        """草稿态：未过账，可自由修改删除"""
        return self.status == 'draft'

    def update_status(self):
        """根据已还金额更新状态

        草稿与已冲销为终态，不参与已还金额推导。
        """
        if self.status in ('draft', 'cancelled'):
            return

        repaid = float(self.repaid_amount or 0)
        total = float(self.amount)

        if repaid >= total:
            self.status = 'repaid'
        elif repaid > 0:
            self.status = 'partial'
        else:
            self.status = 'active'

    @classmethod
    def generate_loan_number(cls):
        """生成借款编号"""
        today = datetime.now()
        prefix = f"SL{today.strftime('%Y%m%d')}"

        # 查找今天最大的编号
        last_loan = cls.query.filter(
            cls.loan_number.like(f"{prefix}%")
        ).order_by(cls.loan_number.desc()).first()

        if last_loan:
            last_seq = int(last_loan.loan_number[-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1

        return f"{prefix}{new_seq:04d}"


class ShareholderLoanRepayment(db.Model):
    """股东借款还款记录"""
    __tablename__ = 'shareholder_loan_repayments'

    id = db.Column(db.Integer, primary_key=True)

    # 还款信息
    repayment_number = db.Column(db.String(50), unique=True, nullable=False, comment='还款编号')
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, comment='还款总金额')
    repayment_date = db.Column(db.Date, nullable=False, comment='还款日期')
    description = db.Column(db.String(200), comment='还款说明')
    remarks = db.Column(db.Text, comment='备注')

    # 状态
    status = db.Column(db.String(20), default='posted', comment='状态: draft/posted/cancelled')

    # 关联会计分录
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('project_journal_entries.id'), comment='关联会计分录')
    bank_account_id = db.Column(db.Integer, db.ForeignKey('project_chart_of_accounts.id'), comment='从银行账户支付')

    # 核对状态（银行对账用）
    is_reconciled = db.Column(db.Boolean, default=False, comment='是否已与银行记录核对')
    reconciled_at = db.Column(db.DateTime, comment='核对时间')
    reconciled_by = db.Column(db.String(50), comment='核对人')

    # 审计字段
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.String(50))

    # 关系
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])
    bank_account = db.relationship('ChartOfAccount', foreign_keys=[bank_account_id])
    details = db.relationship('ShareholderLoanRepaymentDetail', back_populates='repayment', lazy='dynamic')

    @property
    def status_display(self):
        """状态显示"""
        status_map = {
            'draft': '待确认',
            'posted': '已确认',
            'cancelled': '已冲销'
        }
        return status_map.get(self.status, self.status)

    @property
    def is_draft(self):
        """草稿态：未过账，未扣减借款已还金额"""
        return self.status == 'draft'

    @classmethod
    def generate_repayment_number(cls):
        """生成还款编号"""
        today = datetime.now()
        prefix = f"SR{today.strftime('%Y%m%d')}"

        # 查找今天最大的编号
        last_repayment = cls.query.filter(
            cls.repayment_number.like(f"{prefix}%")
        ).order_by(cls.repayment_number.desc()).first()

        if last_repayment:
            last_seq = int(last_repayment.repayment_number[-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1

        return f"{prefix}{new_seq:04d}"


class ShareholderLoanRepaymentDetail(db.Model):
    """还款明细 - 记录每次还款分配到哪些借款"""
    __tablename__ = 'shareholder_loan_repayment_details'

    id = db.Column(db.Integer, primary_key=True)

    # 关联
    repayment_id = db.Column(db.Integer, db.ForeignKey('shareholder_loan_repayments.id'), nullable=False)
    loan_id = db.Column(db.Integer, db.ForeignKey('shareholder_loans.id'), nullable=False)

    # 金额
    amount = db.Column(db.Numeric(12, 2), nullable=False, comment='本次归还金额')

    # 关系
    repayment = db.relationship('ShareholderLoanRepayment', back_populates='details')
    loan = db.relationship('ShareholderLoan', back_populates='repayment_details')
