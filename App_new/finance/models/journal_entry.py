# -*- coding: utf-8 -*-
"""日记账分录模型 - Journal Entry"""

from App_new.exts import db
from datetime import datetime, date
from decimal import Decimal


class JournalEntry(db.Model):
    """日记账分录主表"""
    __tablename__ = 'project_journal_entries'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 分录编号
    entry_number = db.Column(db.String(30), unique=True, nullable=False, comment='分录编号')

    # 分录日期
    entry_date = db.Column(db.Date, nullable=False, comment='分录日期')

    # 来源类型: invoice(发票), receipt(收款), eo(EO付款), manual(手工录入), operating_expense(运营费用)
    source_type = db.Column(db.Enum('invoice', 'receipt', 'eo', 'manual', 'operating_expense'),
                            nullable=False, comment='来源类型')

    # 来源单据ID
    source_id = db.Column(db.Integer, nullable=True, comment='来源单据ID')

    # 来源单据编号（方便查询）
    source_number = db.Column(db.String(50), nullable=True, comment='来源单据编号')

    # 关联项目
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=True, comment='项目ID')

    # 描述/摘要
    description = db.Column(db.String(500), nullable=True, comment='摘要')

    # 币种
    currency = db.Column(db.String(3), default='SGD', comment='币种')

    # 总金额（借方=贷方）
    total_amount = db.Column(db.Numeric(12, 2), default=0, comment='总金额')

    # 状态: draft(草稿), posted(已过账), reversed(已冲销)
    status = db.Column(db.Enum('draft', 'posted', 'reversed'),
                       default='draft', nullable=False, comment='状态')

    # 过账日期
    posted_at = db.Column(db.DateTime, nullable=True, comment='过账时间')
    posted_by = db.Column(db.String(50), nullable=True, comment='过账人')

    # 冲销信息
    reversed_entry_id = db.Column(db.Integer, db.ForeignKey('project_journal_entries.id'), nullable=True, comment='冲销分录ID')
    reversed_at = db.Column(db.DateTime, nullable=True, comment='冲销时间')

    # 备注
    remarks = db.Column(db.Text, nullable=True, comment='备注')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    lines = db.relationship('JournalEntryLine', back_populates='entry', cascade='all, delete-orphan',
                            order_by='JournalEntryLine.line_no')
    header = db.relationship('ProjectHeader', backref='journal_entries')
    reversed_entry = db.relationship('JournalEntry', remote_side=[id], backref='reversing_entries')

    def __repr__(self):
        return f'<JournalEntry {self.entry_number}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'entry_number': self.entry_number,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'source_type': self.source_type,
            'source_type_display': self.source_type_display,
            'source_id': self.source_id,
            'source_number': self.source_number,
            'header_id': self.header_id,
            'description': self.description,
            'currency': self.currency,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'status': self.status,
            'status_display': self.status_display,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'posted_by': self.posted_by,
            'reversed_entry_id': self.reversed_entry_id,
            'reversed_at': self.reversed_at.isoformat() if self.reversed_at else None,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'lines': [line.to_dict() for line in self.lines],
            'is_balanced': self.is_balanced,
            'total_debit': float(self.total_debit),
            'total_credit': float(self.total_credit)
        }

    @property
    def source_type_display(self):
        """来源类型显示名称"""
        type_map = {
            'invoice': 'Invoice (发票)',
            'receipt': 'Receipt (收款)',
            'eo': 'EO (付款)',
            'manual': 'Manual (手工)',
            'operating_expense': 'Operating Expense (运营费用)'
        }
        return type_map.get(self.source_type, self.source_type)

    @property
    def status_display(self):
        """状态显示名称"""
        status_map = {
            'draft': 'Draft (草稿)',
            'posted': 'Posted (已过账)',
            'reversed': 'Reversed (已冲销)'
        }
        return status_map.get(self.status, self.status)

    @property
    def total_debit(self):
        """借方总额"""
        return sum(line.debit or Decimal('0') for line in self.lines)

    @property
    def total_credit(self):
        """贷方总额"""
        return sum(line.credit or Decimal('0') for line in self.lines)

    @property
    def is_balanced(self):
        """检查借贷是否平衡"""
        return abs(self.total_debit - self.total_credit) < Decimal('0.01')

    def post(self, user=None):
        """过账"""
        if not self.is_balanced:
            raise ValueError("Journal entry is not balanced")
        if self.status != 'draft':
            raise ValueError("Only draft entries can be posted")

        self.status = 'posted'
        self.posted_at = datetime.utcnow()
        self.posted_by = user
        self.total_amount = self.total_debit

    def reverse(self, user=None, entry_date=None):
        """冲销分录"""
        if self.status != 'posted':
            raise ValueError("Only posted entries can be reversed")

        # 创建冲销分录
        reverse_entry = JournalEntry(
            entry_number=self._generate_entry_number(),
            entry_date=entry_date or date.today(),
            source_type='manual',
            source_id=self.id,
            source_number=f'REV-{self.entry_number}',
            header_id=self.header_id,
            description=f'Reversal of {self.entry_number}',
            currency=self.currency,
            status='posted',
            posted_at=datetime.utcnow(),
            posted_by=user,
            created_by=user,
            remarks=f'Reversal entry for {self.entry_number}'
        )

        # 创建冲销分录行（借贷互换）
        for line in self.lines:
            reverse_line = JournalEntryLine(
                line_no=line.line_no,
                account_id=line.account_id,
                debit=line.credit,  # 借贷互换
                credit=line.debit,
                memo=f'Reversal: {line.memo}' if line.memo else 'Reversal'
            )
            reverse_entry.lines.append(reverse_line)

        reverse_entry.total_amount = reverse_entry.total_debit

        # 更新原分录状态
        self.status = 'reversed'
        self.reversed_entry_id = reverse_entry.id
        self.reversed_at = datetime.utcnow()

        db.session.add(reverse_entry)
        return reverse_entry

    @classmethod
    def _generate_entry_number(cls):
        """生成分录编号"""
        today = date.today()
        prefix = f"JE{today.strftime('%Y%m%d')}"

        # 查找今天最后一个编号
        last_entry = cls.query.filter(
            cls.entry_number.like(f'{prefix}%')
        ).order_by(cls.entry_number.desc()).first()

        if last_entry:
            last_num = int(last_entry.entry_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}{new_num:04d}"

    @classmethod
    def create_from_invoice(cls, invoice, user=None):
        """从发票创建分录
        借: 应收账款
        贷: 销售收入
        """
        from .chart_of_account import ChartOfAccount

        entry = cls(
            entry_number=cls._generate_entry_number(),
            entry_date=invoice.invoice_date or date.today(),
            source_type='invoice',
            source_id=invoice.id,
            source_number=invoice.invoice_number,
            header_id=invoice.header_id,
            description=f'Invoice {invoice.invoice_number}',
            currency=invoice.currency or 'SGD',
            created_by=user
        )

        # 应收账款 (借)
        ar_account = ChartOfAccount.get_by_code('1100')
        if ar_account:
            entry.lines.append(JournalEntryLine(
                line_no=1,
                account_id=ar_account.id,
                debit=invoice.amount,
                credit=Decimal('0'),
                memo=f'AR for Invoice {invoice.invoice_number}'
            ))

        # 销售收入 (贷) - 根据业务类型选择科目
        income_account = ChartOfAccount.get_by_code('4100')  # 默认销售收入
        if income_account:
            entry.lines.append(JournalEntryLine(
                line_no=2,
                account_id=income_account.id,
                debit=Decimal('0'),
                credit=invoice.amount,
                memo=f'Revenue for Invoice {invoice.invoice_number}'
            ))

        entry.total_amount = invoice.amount
        return entry

    @classmethod
    def create_from_receipt(cls, receipt, user=None):
        """从收款创建分录
        借: 银行存款
        贷: 应收账款
        """
        from .chart_of_account import ChartOfAccount

        entry = cls(
            entry_number=cls._generate_entry_number(),
            entry_date=receipt.payment_date or date.today(),
            source_type='receipt',
            source_id=receipt.id,
            source_number=receipt.receipt_number,
            header_id=receipt.header_id,
            description=f'Receipt {receipt.receipt_number}',
            currency=receipt.currency or 'SGD',
            created_by=user
        )

        # 银行存款 (借)
        bank_account = ChartOfAccount.get_by_code('1002')
        if bank_account:
            entry.lines.append(JournalEntryLine(
                line_no=1,
                account_id=bank_account.id,
                debit=receipt.amount,
                credit=Decimal('0'),
                memo=f'Bank deposit for Receipt {receipt.receipt_number}'
            ))

        # 应收账款 (贷)
        ar_account = ChartOfAccount.get_by_code('1100')
        if ar_account:
            entry.lines.append(JournalEntryLine(
                line_no=2,
                account_id=ar_account.id,
                debit=Decimal('0'),
                credit=receipt.amount,
                memo=f'AR reduction for Receipt {receipt.receipt_number}'
            ))

        entry.total_amount = receipt.amount
        return entry

    @classmethod
    def create_from_eo(cls, eo, user=None):
        """从EO付款创建分录
        借: 成本费用
        贷: 银行存款/应付账款
        """
        from .chart_of_account import ChartOfAccount

        if not eo.pay_amount:
            return None

        entry = cls(
            entry_number=cls._generate_entry_number(),
            entry_date=eo.paid_date or date.today(),
            source_type='eo',
            source_id=eo.id,
            source_number=eo.eo_number,
            header_id=eo.ref.header_id if eo.ref else None,
            description=f'EO Payment {eo.eo_number}',
            currency=eo.ref.currency if eo.ref else 'SGD',
            created_by=user
        )

        # 成本费用 (借)
        cost_account = ChartOfAccount.get_by_code('5100')  # 默认销售成本
        if cost_account:
            entry.lines.append(JournalEntryLine(
                line_no=1,
                account_id=cost_account.id,
                debit=eo.pay_amount,
                credit=Decimal('0'),
                memo=f'Cost for EO {eo.eo_number}'
            ))

        # 银行存款 (贷)
        bank_account = ChartOfAccount.get_by_code('1002')
        if bank_account:
            entry.lines.append(JournalEntryLine(
                line_no=2,
                account_id=bank_account.id,
                debit=Decimal('0'),
                credit=eo.pay_amount,
                memo=f'Payment for EO {eo.eo_number}'
            ))

        entry.total_amount = eo.pay_amount
        return entry

    @classmethod
    def create_from_eo_with_prepayment(cls, eo, prepayment_account_id, user=None):
        """从EO付款创建分录（使用预付账款）
        借: 成本费用
        贷: 预付账款
        """
        from .chart_of_account import ChartOfAccount

        if not eo.pay_amount:
            return None

        entry = cls(
            entry_number=cls._generate_entry_number(),
            entry_date=eo.paid_date or date.today(),
            source_type='eo',
            source_id=eo.id,
            source_number=eo.eo_number,
            header_id=eo.ref.header_id if eo.ref else None,
            description=f'EO Payment (Prepayment) {eo.eo_number}',
            currency=eo.ref.currency if eo.ref else 'SGD',
            created_by=user
        )

        # 成本费用 (借)
        cost_account = ChartOfAccount.get_by_code('5100')  # 默认销售成本
        if cost_account:
            entry.lines.append(JournalEntryLine(
                line_no=1,
                account_id=cost_account.id,
                debit=eo.pay_amount,
                credit=Decimal('0'),
                memo=f'Cost for EO {eo.eo_number}'
            ))

        # 预付账款 (贷) - 使用传入的预付账款科目
        if prepayment_account_id:
            entry.lines.append(JournalEntryLine(
                line_no=2,
                account_id=prepayment_account_id,
                debit=Decimal('0'),
                credit=eo.pay_amount,
                memo=f'Prepayment used for EO {eo.eo_number}'
            ))
        else:
            # 如果没有指定预付账款科目，使用默认的1201
            prepayment_account = ChartOfAccount.get_by_code('1201')
            if prepayment_account:
                entry.lines.append(JournalEntryLine(
                    line_no=2,
                    account_id=prepayment_account.id,
                    debit=Decimal('0'),
                    credit=eo.pay_amount,
                    memo=f'Prepayment used for EO {eo.eo_number}'
                ))

        entry.total_amount = eo.pay_amount
        return entry


class JournalEntryLine(db.Model):
    """日记账分录明细"""
    __tablename__ = 'project_journal_entry_lines'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 分录主表
    entry_id = db.Column(db.Integer, db.ForeignKey('project_journal_entries.id'), nullable=False, comment='分录ID')

    # 行号
    line_no = db.Column(db.Integer, default=1, comment='行号')

    # 科目
    account_id = db.Column(db.Integer, db.ForeignKey('project_chart_of_accounts.id'), nullable=False, comment='科目ID')

    # 借方金额
    debit = db.Column(db.Numeric(12, 2), default=0, comment='借方金额')

    # 贷方金额
    credit = db.Column(db.Numeric(12, 2), default=0, comment='贷方金额')

    # 备注
    memo = db.Column(db.String(200), nullable=True, comment='备注')

    # 关联关系
    entry = db.relationship('JournalEntry', back_populates='lines')
    account = db.relationship('ChartOfAccount', back_populates='journal_lines')

    def __repr__(self):
        return f'<JournalEntryLine {self.entry_id}-{self.line_no}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'entry_id': self.entry_id,
            'line_no': self.line_no,
            'account_id': self.account_id,
            'account_code': self.account.code if self.account else None,
            'account_name': self.account.name if self.account else None,
            'debit': float(self.debit) if self.debit else 0,
            'credit': float(self.credit) if self.credit else 0,
            'memo': self.memo
        }

    @property
    def amount(self):
        """获取金额（借方为正，贷方为负）"""
        return (self.debit or Decimal('0')) - (self.credit or Decimal('0'))
