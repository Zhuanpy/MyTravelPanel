# -*- coding: utf-8 -*-
"""会计科目表模型 - Chart of Account"""

from App_new.exts import db
from datetime import datetime


class ChartOfAccount(db.Model):
    """会计科目表"""
    __tablename__ = 'project_chart_of_accounts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 科目基本信息
    code = db.Column(db.String(20), unique=True, nullable=False, comment='科目代码')
    name = db.Column(db.String(100), nullable=False, comment='科目名称')
    name_cn = db.Column(db.String(100), nullable=True, comment='科目中文名')

    # 科目类型: asset(资产), liability(负债), equity(权益), income(收入), expense(费用)
    account_type = db.Column(db.Enum('asset', 'liability', 'equity', 'income', 'expense'),
                             nullable=False, comment='科目类型')

    # 层级关系
    parent_id = db.Column(db.Integer, db.ForeignKey('project_chart_of_accounts.id'), nullable=True, comment='上级科目ID')
    level = db.Column(db.Integer, default=1, comment='科目层级 1=一级科目')

    # 科目属性
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    is_system = db.Column(db.Boolean, default=False, comment='是否系统预设科目')
    allow_manual_entry = db.Column(db.Boolean, default=True, comment='是否允许手工录入')

    # 余额方向: debit(借方), credit(贷方)
    balance_direction = db.Column(db.Enum('debit', 'credit'), nullable=False, comment='余额方向')

    # 币种
    currency = db.Column(db.String(3), default='SGD', comment='币种')

    # 描述
    description = db.Column(db.Text, nullable=True, comment='科目描述')

    # 排序
    sort_order = db.Column(db.Integer, default=0, comment='排序')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    parent = db.relationship('ChartOfAccount', remote_side=[id], backref='children')
    journal_lines = db.relationship('JournalEntryLine', back_populates='account', lazy='dynamic')

    def __repr__(self):
        return f'<ChartOfAccount {self.code} - {self.name}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'name_cn': self.name_cn,
            'account_type': self.account_type,
            'account_type_display': self.account_type_display,
            'parent_id': self.parent_id,
            'level': self.level,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'allow_manual_entry': self.allow_manual_entry,
            'balance_direction': self.balance_direction,
            'currency': self.currency,
            'description': self.description,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'full_code': self.full_code,
            'full_name': self.full_name
        }

    @property
    def account_type_display(self):
        """科目类型显示名称"""
        type_map = {
            'asset': 'Asset (资产)',
            'liability': 'Liability (负债)',
            'equity': 'Equity (权益)',
            'income': 'Income (收入)',
            'expense': 'Expense (费用)'
        }
        return type_map.get(self.account_type, self.account_type)

    @property
    def full_code(self):
        """完整科目代码（包含上级）"""
        if self.parent:
            return f"{self.parent.code}.{self.code}"
        return self.code

    @property
    def full_name(self):
        """完整科目名称（包含上级）"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @classmethod
    def get_by_code(cls, code):
        """根据科目代码获取科目"""
        return cls.query.filter_by(code=code, is_active=True).first()

    @classmethod
    def get_accounts_by_type(cls, account_type):
        """根据类型获取所有科目"""
        return cls.query.filter_by(account_type=account_type, is_active=True).order_by(cls.sort_order, cls.code).all()

    @classmethod
    def get_tree(cls):
        """获取科目树结构"""
        root_accounts = cls.query.filter_by(parent_id=None, is_active=True).order_by(cls.sort_order, cls.code).all()
        return [cls._build_tree_node(account) for account in root_accounts]

    @classmethod
    def _build_tree_node(cls, account):
        """构建树节点"""
        node = account.to_dict()
        node['children'] = [cls._build_tree_node(child) for child in account.children if child.is_active]
        return node

    @classmethod
    def init_default_accounts(cls):
        """初始化默认科目表"""
        default_accounts = [
            # 资产类 (1xxx)
            {'code': '1000', 'name': 'Assets', 'name_cn': '资产', 'account_type': 'asset', 'balance_direction': 'debit', 'level': 1, 'is_system': True},
            {'code': '1001', 'name': 'Cash', 'name_cn': '现金', 'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},
            {'code': '1002', 'name': 'Bank', 'name_cn': '银行存款', 'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},
            {'code': '1100', 'name': 'Accounts Receivable', 'name_cn': '应收账款', 'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},

            # 负债类 (2xxx)
            {'code': '2000', 'name': 'Liabilities', 'name_cn': '负债', 'account_type': 'liability', 'balance_direction': 'credit', 'level': 1, 'is_system': True},
            {'code': '2100', 'name': 'Accounts Payable', 'name_cn': '应付账款', 'account_type': 'liability', 'balance_direction': 'credit', 'level': 2, 'parent_code': '2000', 'is_system': True},

            # 权益类 (3xxx)
            {'code': '3000', 'name': 'Equity', 'name_cn': '权益', 'account_type': 'equity', 'balance_direction': 'credit', 'level': 1, 'is_system': True},
            {'code': '3100', 'name': 'Retained Earnings', 'name_cn': '留存收益', 'account_type': 'equity', 'balance_direction': 'credit', 'level': 2, 'parent_code': '3000', 'is_system': True},

            # 收入类 (4xxx)
            {'code': '4000', 'name': 'Income', 'name_cn': '收入', 'account_type': 'income', 'balance_direction': 'credit', 'level': 1, 'is_system': True},
            {'code': '4100', 'name': 'Sales Revenue', 'name_cn': '销售收入', 'account_type': 'income', 'balance_direction': 'credit', 'level': 2, 'parent_code': '4000', 'is_system': True},
            {'code': '4101', 'name': 'Flight Sales', 'name_cn': '机票销售收入', 'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': True},
            {'code': '4102', 'name': 'Tour Sales', 'name_cn': '旅游销售收入', 'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': True},
            {'code': '4103', 'name': 'Visa Sales', 'name_cn': '签证销售收入', 'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': True},
            {'code': '4104', 'name': 'Hotel Sales', 'name_cn': '酒店销售收入', 'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': True},
            {'code': '4105', 'name': 'Other Sales', 'name_cn': '其他销售收入', 'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': True},

            # 费用类 (5xxx)
            {'code': '5000', 'name': 'Expenses', 'name_cn': '费用', 'account_type': 'expense', 'balance_direction': 'debit', 'level': 1, 'is_system': True},
            {'code': '5100', 'name': 'Cost of Sales', 'name_cn': '销售成本', 'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '5000', 'is_system': True},
            {'code': '5101', 'name': 'Flight Cost', 'name_cn': '机票成本', 'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': True},
            {'code': '5102', 'name': 'Tour Cost', 'name_cn': '旅游成本', 'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': True},
            {'code': '5103', 'name': 'Visa Cost', 'name_cn': '签证成本', 'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': True},
            {'code': '5104', 'name': 'Hotel Cost', 'name_cn': '酒店成本', 'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': True},
            {'code': '5105', 'name': 'Other Cost', 'name_cn': '其他成本', 'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': True},
        ]

        # 第一轮：创建所有科目（不设置parent_id）
        code_to_account = {}
        for acc_data in default_accounts:
            existing = cls.query.filter_by(code=acc_data['code']).first()
            if not existing:
                parent_code = acc_data.pop('parent_code', None)
                account = cls(**acc_data)
                account._pending_parent_code = parent_code
                db.session.add(account)
                code_to_account[acc_data['code']] = account
            else:
                code_to_account[acc_data['code']] = existing

        db.session.flush()

        # 第二轮：设置parent_id
        for code, account in code_to_account.items():
            if hasattr(account, '_pending_parent_code') and account._pending_parent_code:
                parent = code_to_account.get(account._pending_parent_code)
                if parent:
                    account.parent_id = parent.id
                delattr(account, '_pending_parent_code')

        db.session.commit()
        return True
