# -*- coding: utf-8 -*-
"""Invoice相关模型 - 项目发票/账单记录（应收AR）"""

from App_new.exts import db
from datetime import datetime
import json


class ProjectInvoice(db.Model):
    """项目发票/账单表 - 对客收入单，用来收钱"""
    __tablename__ = 'project_invoices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False, comment='发票编号')
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=False, comment='项目主表ID')

    # 发票信息
    invoice_date = db.Column(db.Date, nullable=False, comment='发票日期')
    due_date = db.Column(db.Date, nullable=True, comment='到期日期')
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='发票金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币类型')
    
    # 发票类型
    invoice_type = db.Column(db.Enum('full', 'partial', 'deposit', 'final'),
                            default='full', nullable=False, comment='发票类型: full-全额, partial-分期, deposit-定金, final-尾款')

    # 客户信息
    customer_name = db.Column(db.String(100), nullable=True, comment='客户名称')
    customer_company = db.Column(db.String(100), nullable=True, comment='客户公司')
    customer_email = db.Column(db.String(100), nullable=True, comment='客户邮箱')
    customer_phone = db.Column(db.String(50), nullable=True, comment='客户电话')
    customer_address = db.Column(db.Text, nullable=True, comment='客户地址')

    # 发票状态：confirmed-已确认, cancelled-已取消
    status = db.Column(db.Enum('confirmed', 'cancelled'),
                       default='confirmed', nullable=False, comment='发票状态')

    # 付款状态：unpaid-未付款, partial_paid-部分付款, paid-已付款
    payment_status = db.Column(db.Enum('unpaid', 'partial_paid', 'paid'),
                               default='unpaid', nullable=False, comment='付款状态')
    paid_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False, comment='已付金额')

    # 关联的REF（JSON格式存储，一张发票可对应多个REF）
    ref_ids = db.Column(db.Text, nullable=True, comment='关联的REF ID列表(JSON)')
    
    # 发票明细（JSON格式存储）
    invoice_items = db.Column(db.Text, nullable=True, comment='发票明细项(JSON)')

    # 备注和附加信息
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    terms = db.Column(db.Text, nullable=True, comment='付款条款')
    extra_info = db.Column(db.Text, nullable=True, comment='额外信息(JSON)')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True, comment='发送时间')
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    header = db.relationship('ProjectHeader', backref='invoices')

    def __repr__(self):
        return f'<ProjectInvoice {self.invoice_number}: {self.amount} {self.currency}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'header_id': self.header_id,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'amount': float(self.amount) if self.amount else 0,
            'currency': self.currency,
            'invoice_type': self.invoice_type,
            'customer_name': self.customer_name,
            'customer_company': self.customer_company,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'customer_address': self.customer_address,
            'status': self.status,
            'payment_status': self.payment_status,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0,
            'ref_ids': json.loads(self.ref_ids) if self.ref_ids else [],
            'invoice_items': json.loads(self.invoice_items) if self.invoice_items else [],
            'remarks': self.remarks,
            'terms': self.terms,
            'extra_info': json.loads(self.extra_info) if self.extra_info else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_by': self.created_by
        }

    @classmethod
    def generate_invoice_number(cls):
        """生成发票编号，从10000开始递增"""
        from sqlalchemy import func, text

        # 查找最大的纯数字发票编号（使用MySQL的REGEXP）
        last_invoice = cls.query.filter(
            cls.invoice_number.op('REGEXP')('^[0-9]+$')
        ).order_by(func.cast(cls.invoice_number, db.Integer).desc()).first()

        if last_invoice:
            try:
                last_number = int(last_invoice.invoice_number)
                return str(last_number + 1)
            except ValueError:
                pass

        # 如果没有纯数字编号，从10000开始
        return '10000'

    @property
    def invoice_type_display(self):
        """发票类型显示文本"""
        type_map = {
            'full': '全额发票',
            'partial': '分期发票',
            'deposit': '定金发票',
            'final': '尾款发票'
        }
        return type_map.get(self.invoice_type, self.invoice_type)

    @property
    def status_display(self):
        """发票状态显示文本"""
        status_map = {
            'confirmed': 'Confirmed',
            'cancelled': 'Cancelled'
        }
        return status_map.get(self.status, self.status)

    @property
    def payment_status_display(self):
        """付款状态显示文本"""
        status_map = {
            'unpaid': 'Unpaid',
            'partial_paid': 'Partial Paid',
            'paid': 'Paid'
        }
        return status_map.get(self.payment_status, self.payment_status)

    @property
    def unpaid_amount(self):
        """计算未付金额"""
        return float(self.amount or 0) - float(self.paid_amount or 0)

    @property
    def is_overdue(self):
        """检查是否逾期"""
        if self.status == 'cancelled' or self.payment_status == 'paid':
            return False
        if self.due_date and self.due_date < datetime.now().date():
            return True
        return False

    @property
    def related_refs(self):
        """获取关联的REF对象列表"""
        if not self.ref_ids:
            return []
        try:
            ref_id_list = json.loads(self.ref_ids)
            from .ref import ProjectRef
            return ProjectRef.query.filter(ProjectRef.id.in_(ref_id_list)).all()
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def items_list(self):
        """获取发票明细列表"""
        if not self.invoice_items:
            return []
        try:
            return json.loads(self.invoice_items)
        except (json.JSONDecodeError, TypeError):
            return []

    def update_payment_status(self):
        """根据已付金额更新付款状态"""
        if self.status == 'cancelled':
            return

        amount = float(self.amount or 0)
        paid = float(self.paid_amount or 0)

        if paid >= amount:
            self.payment_status = 'paid'
        elif paid > 0:
            self.payment_status = 'partial_paid'
        else:
            self.payment_status = 'unpaid'

    @classmethod
    def get_header_total_invoiced(cls, header_id):
        """获取项目的总发票金额"""
        from sqlalchemy import func
        result = db.session.query(func.sum(cls.amount)).filter(
            cls.header_id == header_id,
            cls.status != 'cancelled'
        ).scalar()
        return float(result) if result else 0

    @classmethod
    def get_header_total_paid(cls, header_id):
        """获取项目的总已付金额"""
        from sqlalchemy import func
        result = db.session.query(func.sum(cls.paid_amount)).filter(
            cls.header_id == header_id,
            cls.status != 'cancelled'
        ).scalar()
        return float(result) if result else 0

    @classmethod
    def get_header_unpaid_amount(cls, header_id):
        """获取项目的总未付金额"""
        return cls.get_header_total_invoiced(header_id) - cls.get_header_total_paid(header_id)

    @classmethod
    def get_company_unpaid_invoices(cls, company_id):
        """
        获取公司的所有未付/部分付款发票

        Args:
            company_id: 公司ID

        Returns:
            list: 未付发票列表
        """
        from .project import ProjectHeader

        # 通过 ProjectHeader 查找该公司的所有项目
        headers = ProjectHeader.query.filter_by(company_id=company_id).all()
        header_ids = [h.id for h in headers]

        if not header_ids:
            return []

        # 查找这些项目的未付发票（已确认且未全额付款）
        invoices = cls.query.filter(
            cls.header_id.in_(header_ids),
            cls.status == 'confirmed',
            cls.payment_status.in_(['unpaid', 'partial_paid'])
        ).order_by(cls.invoice_date.asc()).all()

        return invoices

    @property
    def company_id_via_header(self):
        """获取发票对应的公司ID（通过项目header）"""
        if self.header and self.header.company_id:
            return self.header.company_id
        return None

    @property
    def company_name_via_header(self):
        """获取发票对应的公司名称（通过项目header）"""
        if self.header and self.header.company:
            return self.header.company.company_name
        return self.customer_company  # 回退到文本字段


class InvoiceItem(db.Model):
    """发票明细项表"""
    __tablename__ = 'invoice_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('project_invoices.id'), nullable=False, comment='发票ID')
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=True, comment='关联REF ID')
    
    description = db.Column(db.String(200), nullable=False, comment='项目描述')
    quantity = db.Column(db.Integer, default=1, nullable=False, comment='数量')
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, comment='单价')
    total_price = db.Column(db.Numeric(10, 2), nullable=False, comment='总价')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    invoice = db.relationship('ProjectInvoice', backref='items')
    ref = db.relationship('ProjectRef', backref='invoice_items')

    def __repr__(self):
        return f'<InvoiceItem {self.description}: {self.total_price}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'ref_id': self.ref_id,
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'total_price': float(self.total_price) if self.total_price else 0,
            'remarks': self.remarks
        }

