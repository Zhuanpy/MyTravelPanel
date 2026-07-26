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

    # ===== 跟踪线1：供应商退款（航司/地接等是否已把钱退给我们）=====
    supplier_name = db.Column(db.String(100), nullable=True, comment='供应商名称')
    supplier_refund_status = db.Column(db.Enum('pending', 'partial', 'received', 'na'),
                                       default='pending', nullable=False,
                                       comment='供应商退款状态: 未收到/部分收到/已收到/不涉及')
    supplier_refund_amount = db.Column(db.Numeric(10, 2), default=0, nullable=True, comment='已收到的供应商退款金额')
    supplier_refund_date = db.Column(db.Date, nullable=True, comment='收到供应商退款日期')
    supplier_refund_remarks = db.Column(db.String(255), nullable=True, comment='供应商退款备注')

    # ===== 跟踪线2：退给客户（我们是否已把钱退还给客户）=====
    customer_refund_status = db.Column(db.Enum('pending', 'partial', 'paid'),
                                       default='pending', nullable=False,
                                       comment='退客户状态: 未退款/部分退款/已退款')
    customer_refund_amount = db.Column(db.Numeric(10, 2), default=0, nullable=True, comment='已退给客户的金额')
    customer_refund_date = db.Column(db.Date, nullable=True, comment='退给客户日期')
    customer_refund_remarks = db.Column(db.String(255), nullable=True, comment='退客户备注')

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
            'supplier_name': self.supplier_name,
            'supplier_refund_status': self.supplier_refund_status,
            'supplier_refund_amount': float(self.supplier_refund_amount) if self.supplier_refund_amount else 0,
            'supplier_refund_date': self.supplier_refund_date.isoformat() if self.supplier_refund_date else None,
            'supplier_refund_remarks': self.supplier_refund_remarks,
            'customer_refund_status': self.customer_refund_status,
            'customer_refund_amount': float(self.customer_refund_amount) if self.customer_refund_amount else 0,
            'customer_refund_date': self.customer_refund_date.isoformat() if self.customer_refund_date else None,
            'customer_refund_remarks': self.customer_refund_remarks,
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

    # ---------- 供应商退款（收）----------
    @property
    def supplier_refund_status_display(self):
        """供应商退款状态中文显示"""
        return {
            'pending': '未收到',
            'partial': '部分收到',
            'received': '已收到',
            'na': '不涉及',
        }.get(self.supplier_refund_status, self.supplier_refund_status)

    @property
    def supplier_refund_badge(self):
        """供应商退款状态对应的 Bootstrap 徽章样式"""
        return {
            'pending': 'bg-warning text-dark',
            'partial': 'bg-info text-dark',
            'received': 'bg-success',
            'na': 'bg-light text-muted border',
        }.get(self.supplier_refund_status, 'bg-secondary')

    # ---------- 退给客户（付）----------
    @property
    def customer_refund_status_display(self):
        """退客户状态中文显示"""
        return {
            'pending': '未退款',
            'partial': '部分退款',
            'paid': '已退款',
        }.get(self.customer_refund_status, self.customer_refund_status)

    @property
    def customer_refund_badge(self):
        """退客户状态对应的 Bootstrap 徽章样式"""
        return {
            'pending': 'bg-danger',
            'partial': 'bg-info text-dark',
            'paid': 'bg-success',
        }.get(self.customer_refund_status, 'bg-secondary')

    @property
    def customer_refund_outstanding(self):
        """还欠客户多少（退款总额 - 已退给客户金额），仅对已确认退款有意义"""
        if self.status != 'confirmed':
            return 0.0
        return round(float(self.amount or 0) - float(self.customer_refund_amount or 0), 2)

    @property
    def delete_block_reason(self):
        """已发生实际收付的退款不允许删除，返回原因（可删除时返回 None）

        供应商已退款给我们、或已退款给客户（含部分），都意味着钱已动，
        删除会造成账目丢失；需先把对应状态改回「未收到 / 未退款」再删。
        """
        reasons = []
        if self.supplier_refund_status in ('received', 'partial'):
            reasons.append(f'供应商退款：{self.supplier_refund_status_display}')
        if self.customer_refund_status in ('paid', 'partial'):
            reasons.append(f'退客户：{self.customer_refund_status_display}')
        return '、'.join(reasons) if reasons else None

    @property
    def can_delete(self):
        """是否允许删除"""
        return self.delete_block_reason is None

    @property
    def supplier_refund_outstanding(self):
        """供应商还差多少没退给我们（退款总额 - 已收金额）；不涉及供应商时为 0"""
        if self.status != 'confirmed' or self.supplier_refund_status == 'na':
            return 0.0
        return round(float(self.amount or 0) - float(self.supplier_refund_amount or 0), 2)


class ProjectRefundItem(db.Model):
    """退款明细表（一条退款下的多张发票明细）"""
    __tablename__ = 'project_refund_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    refund_id = db.Column(db.Integer, db.ForeignKey('project_refunds.id', ondelete='CASCADE'),
                          nullable=False, comment='退款记录ID')
    invoice_id = db.Column(db.Integer, db.ForeignKey('project_invoices.id'), nullable=False, comment='发票ID')

    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, comment='该发票本次退款金额')
    remarks = db.Column(db.String(255), nullable=True, comment='明细备注')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    refund = db.relationship('ProjectRefund', back_populates='items')
    invoice = db.relationship('ProjectInvoice')

    def __repr__(self):
        return f'<ProjectRefundItem refund={self.refund_id} invoice={self.invoice_id}: {self.amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'refund_id': self.refund_id,
            'invoice_id': self.invoice_id,
            'amount': float(self.amount) if self.amount else 0,
            'remarks': self.remarks,
        }

    @classmethod
    def get_invoice_refunded(cls, invoice_id, exclude_refund_id=None):
        """获取某发票已退款总额（仅统计已确认的退款，可排除指定退款用于编辑场景）"""
        from sqlalchemy import func
        q = db.session.query(func.sum(cls.amount)).join(
            ProjectRefund, cls.refund_id == ProjectRefund.id
        ).filter(
            cls.invoice_id == invoice_id,
            ProjectRefund.status == 'confirmed'
        )
        if exclude_refund_id:
            q = q.filter(ProjectRefund.id != exclude_refund_id)
        return float(q.scalar() or 0)
