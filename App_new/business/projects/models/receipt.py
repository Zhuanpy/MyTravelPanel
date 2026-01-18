# -*- coding: utf-8 -*-
"""收款相关模型 - 项目收款记录"""

from App_new.exts import db
from datetime import datetime
import json


class ProjectReceipt(db.Model):
    """项目收款记录表"""
    __tablename__ = 'project_receipts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    receipt_number = db.Column(db.String(30), unique=True, nullable=False, comment='收款单号')
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=True, comment='REF明细ID（可选）')
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=False, comment='项目主表ID')
    invoice_id = db.Column(db.Integer, db.ForeignKey('project_invoices.id'), nullable=True, comment='关联发票ID')

    # 收款信息
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='收款金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币类型')
    payment_method = db.Column(db.Enum('cash', 'bank_transfer', 'credit_card', 'cheque', 'other'),
                               nullable=False, comment='付款方式')
    payment_date = db.Column(db.Date, nullable=False, comment='收款日期')

    # 收款人信息
    payer_name = db.Column(db.String(100), nullable=True, comment='付款人姓名')
    payer_contact = db.Column(db.String(50), nullable=True, comment='付款人联系方式')
    payer_company = db.Column(db.String(100), nullable=True, comment='付款人公司')

    # 银行信息（如果是银行转账）
    bank_name = db.Column(db.String(100), nullable=True, comment='银行名称')
    account_number = db.Column(db.String(50), nullable=True, comment='账号')
    transaction_id = db.Column(db.String(100), nullable=True, comment='交易流水号')

    # 状态和备注
    status = db.Column(db.Enum('pending', 'confirmed', 'cancelled'),
                       default='pending', nullable=False, comment='收款状态')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    extra_info = db.Column(db.Text, nullable=True, comment='额外信息(JSON格式，用于存储分配信息等)')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    # 关联关系
    ref = db.relationship('ProjectRef', backref='receipts')
    header = db.relationship('ProjectHeader', backref='receipts')
    invoice = db.relationship('ProjectInvoice', backref='receipts')

    def __repr__(self):
        return f'<ProjectReceipt {self.receipt_number}: {self.amount} {self.currency}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'receipt_number': self.receipt_number,
            'ref_id': self.ref_id,
            'header_id': self.header_id,
            'invoice_id': self.invoice_id,
            'amount': float(self.amount) if self.amount else 0,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payer_name': self.payer_name,
            'payer_contact': self.payer_contact,
            'payer_company': self.payer_company,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'remarks': self.remarks,
            'extra_info': json.loads(self.extra_info) if self.extra_info else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

    @classmethod
    def generate_receipt_number(cls):
        """生成收款单号"""
        # 格式: RC + 年月日 + 3位序号, 例如: RC20240702001

        today = datetime.now().strftime('%Y%m%d')
        prefix = f'RC{today}'

        # 查找今天最后一个收款单号
        last_receipt = cls.query.filter(
            cls.receipt_number.like(f'{prefix}%')
        ).order_by(cls.receipt_number.desc()).first()

        if last_receipt:
            # 提取序号部分
            try:
                last_number = int(last_receipt.receipt_number[-3:])
                new_number = str(last_number + 1).zfill(3)
            except ValueError:
                new_number = '001'
        else:
            new_number = '001'

        return f'{prefix}{new_number}'

    @property
    def payment_method_display(self):
        """付款方式显示文本"""
        method_map = {
            'cash': '现金',
            'bank_transfer': '银行转账',
            'credit_card': '信用卡',
            'cheque': '支票',
            'other': '其他'
        }
        return method_map.get(self.payment_method, self.payment_method)

    @property
    def status_display(self):
        """状态显示文本"""
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'cancelled': '已取消'
        }
        return status_map.get(self.status, self.status)

    @property
    def receipt_type(self):
        """收款类型：项目级别或REF级别"""
        return '项目级别' if self.ref_id is None else 'REF级别'

    @classmethod
    def get_ref_total_received(cls, ref_id, header_id):
        """获取REF的实际已收款总额（包括项目级别收款记录的分配）"""
        from .invoice import ProjectInvoice
        from .ref import ProjectRef

        # 1. 直接关联的REF级别收款记录
        ref_receipts = cls.query.filter_by(ref_id=ref_id, status='confirmed').all()
        total_received = sum(float(r.amount) for r in ref_receipts)

        # 获取当前 REF 的销售价格
        current_ref = ProjectRef.query.get(ref_id)
        current_ref_selling = float(current_ref.selling_price or 0) if current_ref else 0

        # 2. 项目级别收款记录中分配给该REF的金额
        project_receipts = cls.query.filter_by(header_id=header_id, ref_id=None, status='confirmed').all()
        for project_receipt in project_receipts:
            if project_receipt.extra_info:
                try:
                    distribution_info = json.loads(project_receipt.extra_info)

                    # 旧格式：distribution 数组包含 ref_id
                    if 'distribution' in distribution_info:
                        for dist in distribution_info['distribution']:
                            if isinstance(dist, dict) and dist.get('ref_id') == ref_id:
                                total_received += dist.get('amount', 0)

                    # 新格式：allocations 是 {invoice_id: amount} 字典
                    # 需要通过发票的 ref_ids 来判断是否属于这个 REF，按销售额比例分配
                    if 'allocations' in distribution_info:
                        for inv_id_str, amount in distribution_info['allocations'].items():
                            try:
                                inv_id = int(inv_id_str) if isinstance(inv_id_str, str) else inv_id_str
                                invoice = ProjectInvoice.query.get(inv_id)
                                if invoice and invoice.ref_ids:
                                    ref_id_list = json.loads(invoice.ref_ids) if isinstance(invoice.ref_ids, str) else invoice.ref_ids
                                    ref_id_int_list = [int(r) for r in ref_id_list]
                                    if ref_id in ref_id_int_list:
                                        # 按销售额比例分配
                                        total_selling = sum(
                                            float(ProjectRef.query.get(rid).selling_price or 0)
                                            for rid in ref_id_int_list
                                            if ProjectRef.query.get(rid)
                                        )
                                        if total_selling > 0 and current_ref_selling > 0:
                                            proportion = current_ref_selling / total_selling
                                            total_received += float(amount) * proportion
                            except (ValueError, json.JSONDecodeError, TypeError):
                                pass
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

        # 3. 通过 ReceiptInvoiceAllocation 表分配的金额
        # 只处理项目级别收款（ref_id=None），避免与REF级别收款重复计算
        allocations = ReceiptInvoiceAllocation.query.join(
            cls, ReceiptInvoiceAllocation.receipt_id == cls.id
        ).filter(
            cls.header_id == header_id,
            cls.ref_id == None,  # 只查询项目级别收款
            cls.status == 'confirmed'
        ).all()

        for alloc in allocations:
            invoice = ProjectInvoice.query.get(alloc.invoice_id)
            if invoice and invoice.ref_ids:
                try:
                    ref_id_list = json.loads(invoice.ref_ids) if isinstance(invoice.ref_ids, str) else invoice.ref_ids
                    ref_id_int_list = [int(r) for r in ref_id_list]
                    if ref_id in ref_id_int_list:
                        # 按销售额比例分配
                        total_selling = sum(
                            float(ProjectRef.query.get(rid).selling_price or 0)
                            for rid in ref_id_int_list
                            if ProjectRef.query.get(rid)
                        )
                        if total_selling > 0 and current_ref_selling > 0:
                            proportion = current_ref_selling / total_selling
                            total_received += float(alloc.allocated_amount) * proportion
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

        return total_received

    @classmethod
    def get_project_unpaid_amount(cls, header_id):
        """获取项目的总未收款金额"""
        from .project import ProjectHeader  # 避免循环导入
        header = ProjectHeader.query.get(header_id)
        if not header:
            return 0

        # 计算项目总销售额
        total_selling = sum(float(ref.selling_price or 0) for ref in header.refs)

        # 计算项目总收款额（直接统计所有已确认收款）
        total_received = sum(
            float(r.amount or 0)
            for r in cls.query.filter_by(header_id=header_id, status='confirmed').all()
        )

        # 未收款 = 总销售 - 总收款
        unpaid = total_selling - total_received
        return max(0, unpaid)  # 不返回负数

    @classmethod
    def can_create_project_receipt(cls, header_id, amount):
        """检查是否可以创建项目级别收款"""
        unpaid_amount = cls.get_project_unpaid_amount(header_id)
        return float(amount) <= unpaid_amount

    @classmethod
    def distribute_project_receipt(cls, header_id, amount, distribution_method='auto'):
        """
        分配项目级别收款到各个REF

        Args:
            header_id: 项目ID
            amount: 收款金额
            distribution_method: 分配方式 ('auto', 'manual')

        Returns:
            dict: 分配结果
        """
        from .project import ProjectHeader  # 避免循环导入
        header = ProjectHeader.query.get(header_id)
        if not header:
            return {'success': False, 'message': '项目不存在'}

        # 检查收款金额是否超过未收款总额
        total_unpaid = cls.get_project_unpaid_amount(header_id)
        if float(amount) > total_unpaid:
            return {'success': False, 'message': f'收款金额({amount})不能超过未收款总额({total_unpaid})'}

        # 获取所有有未收款的REF（按ID顺序排序，从上到下）
        unpaid_refs = []
        # 先获取所有REF并按ID排序
        all_refs = sorted(header.refs, key=lambda r: r.id)
        
        for ref in all_refs:
            if ref.selling_price:
                # 使用辅助方法计算已收款（包括项目级别分配）
                ref_received = cls.get_ref_total_received(ref.id, header_id)
                ref_unpaid = float(ref.selling_price) - ref_received
                
                if ref_unpaid > 0.01:  # 只包含有未收款的REF（考虑浮点数误差）
                    unpaid_refs.append({
                        'ref': ref,
                        'unpaid': ref_unpaid
                    })

        if not unpaid_refs:
            return {'success': False, 'message': '没有需要收款的REF'}

        # 按分配方式计算分配金额
        distribution = []
        remaining_amount = float(amount)
        total_unpaid = sum(ref['unpaid'] for ref in unpaid_refs)

        # 验证收款金额不能超过总未收款
        if remaining_amount > total_unpaid:
            return {
                'success': False,
                'message': f'收款金额({remaining_amount:.2f})不能超过总未收款金额({total_unpaid:.2f})'
            }

        if distribution_method == 'auto' or distribution_method == 'proportional':
            # 按未收款比例自动分配（保持向后兼容）
            # 按比例分配
            for i, ref_info in enumerate(unpaid_refs):
                if remaining_amount <= 0:
                    break

                if i == len(unpaid_refs) - 1:
                    # 最后一个REF，分配剩余所有金额
                    allocated = remaining_amount
                else:
                    # 按比例分配，但不超过该REF的未收款金额
                    allocated = min(ref_info['unpaid'], remaining_amount * (ref_info['unpaid'] / total_unpaid))

                if allocated > 0:
                    distribution.append({
                        'ref_id': ref_info['ref'].id,
                        'amount': round(allocated, 2),
                        'method': 'auto'
                    })
                    remaining_amount -= allocated
                    remaining_amount = round(remaining_amount, 2)  # 避免浮点数精度问题
        
        elif distribution_method == 'sequential':
            # 从上到下按REF顺序结算（新逻辑）
            # 按REF的ID顺序排序（从上到下）
            unpaid_refs.sort(key=lambda x: x['ref'].id)
            
            for ref_info in unpaid_refs:
                if remaining_amount <= 0.01:  # 考虑浮点数误差
                    break
                
                ref_unpaid = ref_info['unpaid']
                if ref_unpaid > 0.01:  # 只处理有未收款的REF
                    # 优先分配给当前REF，直到付清
                    allocated = min(ref_unpaid, remaining_amount)
                    
                    if allocated > 0.01:
                        distribution.append({
                            'ref_id': ref_info['ref'].id,
                            'amount': round(allocated, 2),
                            'method': 'sequential'
                        })
                        remaining_amount -= allocated
                        remaining_amount = round(remaining_amount, 2)  # 避免浮点数精度问题
            
            # 如果还有剩余金额，说明收款超过了总未收款
            if remaining_amount > 0.01:
                return {
                    'success': False,
                    'message': f'收款金额({float(amount):.2f})超过总未收款金额({total_unpaid:.2f})，剩余未分配：{remaining_amount:.2f}'
                }
        
        else:
            # 未知的分配方式，默认按顺序分配
            unpaid_refs.sort(key=lambda x: x['ref'].id)
            
            for ref_info in unpaid_refs:
                if remaining_amount <= 0.01:
                    break
                
                ref_unpaid = ref_info['unpaid']
                if ref_unpaid > 0.01:
                    allocated = min(ref_unpaid, remaining_amount)
                    
                    if allocated > 0.01:
                        distribution.append({
                            'ref_id': ref_info['ref'].id,
                            'amount': round(allocated, 2),
                            'method': distribution_method or 'sequential'
                        })
                        remaining_amount -= allocated
                        remaining_amount = round(remaining_amount, 2)
            
            # 如果还有剩余金额，说明收款超过了总未收款
            if remaining_amount > 0.01:
                return {
                    'success': False,
                    'message': f'收款金额({float(amount):.2f})超过总未收款金额({total_unpaid:.2f})，剩余未分配：{remaining_amount:.2f}'
                }

        return {
            'success': True,
            'distribution': distribution,
            'remaining_amount': round(remaining_amount, 2),
            'total_unpaid': total_unpaid
        }

    @classmethod
    def get_invoice_total_received(cls, invoice_id):
        """获取发票的已收款总额"""
        from sqlalchemy import func
        result = db.session.query(func.sum(cls.amount)).filter(
            cls.invoice_id == invoice_id,
            cls.status == 'confirmed'
        ).scalar()
        return float(result) if result else 0

    @classmethod
    def update_invoice_paid_amount(cls, invoice_id):
        """更新发票的已付金额（根据关联的收款记录计算）"""
        if not invoice_id:
            return

        from .invoice import ProjectInvoice

        invoice = ProjectInvoice.query.get(invoice_id)
        if not invoice or invoice.status == 'cancelled':
            return

        # 计算该发票关联的所有确认收款总额
        total_received = cls.get_invoice_total_received(invoice_id)

        # 更新发票的 paid_amount
        invoice.paid_amount = total_received

        # 更新发票付款状态
        amount = float(invoice.amount or 0)
        if amount <= 0:
            # 金额为0的发票直接标记为已付
            invoice.payment_status = 'paid'
        elif total_received >= amount:
            invoice.payment_status = 'paid'
        elif total_received > 0:
            invoice.payment_status = 'partial_paid'
        else:
            invoice.payment_status = 'unpaid'

    @classmethod
    def get_invoice_allocated_amount(cls, invoice_id):
        """获取发票通过分配表已分配的收款总额"""
        from sqlalchemy import func
        # 使用显式 join 条件，确保正确关联
        result = db.session.query(func.sum(ReceiptInvoiceAllocation.allocated_amount)).filter(
            ReceiptInvoiceAllocation.invoice_id == invoice_id
        ).join(
            cls, ReceiptInvoiceAllocation.receipt_id == cls.id
        ).filter(
            cls.status == 'confirmed'
        ).scalar()
        return float(result) if result else 0

    @classmethod
    def update_invoice_paid_amount_from_allocations(cls, invoice_id):
        """根据分配表更新发票的已付金额"""
        if not invoice_id:
            return

        from .invoice import ProjectInvoice

        invoice = ProjectInvoice.query.get(invoice_id)
        if not invoice or invoice.status == 'cancelled':
            return

        # 计算该发票的所有分配总额
        total_allocated = cls.get_invoice_allocated_amount(invoice_id)

        # 兼容旧的直接关联方式
        direct_total = cls.get_invoice_total_received(invoice_id)

        # 取较大值（兼容新旧方式）
        total_received = max(total_allocated, direct_total)

        # 更新发票的 paid_amount
        invoice.paid_amount = total_received

        # 更新发票付款状态
        amount = float(invoice.amount or 0)
        if amount <= 0:
            # 金额为0的发票直接标记为已付
            invoice.payment_status = 'paid'
        elif total_received >= amount:
            invoice.payment_status = 'paid'
        elif total_received > 0:
            invoice.payment_status = 'partial_paid'
        else:
            invoice.payment_status = 'unpaid'

        # 确保更改被持久化
        db.session.flush()

    @classmethod
    def update_ref_payment_status(cls, ref_id):
        """更新REF的payment_status（根据收款情况）

        Args:
            ref_id: REF的ID

        Returns:
            str: 更新后的状态，如果未更新则返回None
        """
        if not ref_id:
            return None

        from .ref import ProjectRef

        project_ref = ProjectRef.query.get(ref_id)
        if not project_ref:
            return None

        # 计算未付金额
        unpaid = project_ref.unpaid_amount
        old_status = project_ref.payment_status

        if unpaid <= 0:
            # 已全额付款
            if project_ref.payment_status != 'paid':
                project_ref.payment_status = 'paid'
                return 'paid'
        elif project_ref.selling_price and float(project_ref.selling_price) > 0:
            # 检查是否有部分付款
            total_received = cls.get_ref_total_received(ref_id, project_ref.header_id)
            if total_received > 0 and project_ref.payment_status == 'unpaid':
                project_ref.payment_status = 'partial'
                return 'partial'

        return None

    @classmethod
    def update_header_refs_payment_status(cls, header_id):
        """更新项目下所有REF的payment_status

        Args:
            header_id: 项目ID

        Returns:
            dict: 更新结果 {'paid': count, 'partial': count}
        """
        from .project import ProjectHeader

        header = ProjectHeader.query.get(header_id)
        if not header:
            return {'paid': 0, 'partial': 0}

        result = {'paid': 0, 'partial': 0}

        for ref in header.refs:
            new_status = cls.update_ref_payment_status(ref.id)
            if new_status == 'paid':
                result['paid'] += 1
            elif new_status == 'partial':
                result['partial'] += 1

        return result

    @classmethod
    def distribute_to_invoices(cls, amount, invoice_ids, distribution_method='sequential'):
        """
        将收款金额分配到多张发票

        Args:
            amount: 收款总金额
            invoice_ids: 发票ID列表
            distribution_method: 分配方式 ('sequential'-顺序, 'proportional'-按比例)

        Returns:
            dict: 分配结果
        """
        from .invoice import ProjectInvoice

        allocations = {}
        remaining = float(amount)

        # 获取各发票未付金额
        invoices_unpaid = []
        total_unpaid = 0
        for inv_id in invoice_ids:
            invoice = ProjectInvoice.query.get(inv_id)
            if invoice and invoice.status not in ['cancelled', 'paid']:
                unpaid = invoice.unpaid_amount
                if unpaid > 0:
                    invoices_unpaid.append({'invoice': invoice, 'unpaid': unpaid})
                    total_unpaid += unpaid

        if not invoices_unpaid:
            return {'success': False, 'message': '没有可分配的未付发票', 'allocations': {}}

        if remaining > total_unpaid + 0.01:
            return {
                'success': False,
                'message': f'收款金额({remaining:.2f})超过选中发票未付总额({total_unpaid:.2f})',
                'allocations': {}
            }

        if distribution_method == 'sequential':
            # 顺序分配：按发票日期从早到晚依次付清
            invoices_unpaid.sort(key=lambda x: x['invoice'].invoice_date or datetime.min)

            for item in invoices_unpaid:
                if remaining <= 0.01:
                    break
                allocated = min(item['unpaid'], remaining)
                allocations[item['invoice'].id] = round(allocated, 2)
                remaining -= allocated
                remaining = round(remaining, 2)

        elif distribution_method == 'proportional':
            # 按比例分配
            for i, item in enumerate(invoices_unpaid):
                if remaining <= 0.01:
                    break
                if i == len(invoices_unpaid) - 1:
                    allocated = remaining
                else:
                    allocated = min(item['unpaid'], remaining * (item['unpaid'] / total_unpaid))
                allocations[item['invoice'].id] = round(allocated, 2)
                remaining -= allocated
                remaining = round(remaining, 2)

        return {
            'success': True,
            'allocations': allocations,
            'total_allocated': sum(allocations.values()),
            'remaining': remaining
        }


class ReceiptInvoiceAllocation(db.Model):
    """收款-发票分配表（多对多关联）"""
    __tablename__ = 'receipt_invoice_allocations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey('project_receipts.id', ondelete='CASCADE'),
                          nullable=False, comment='收款记录ID')
    invoice_id = db.Column(db.Integer, db.ForeignKey('project_invoices.id', ondelete='CASCADE'),
                          nullable=False, comment='发票ID')

    # 分配金额
    allocated_amount = db.Column(db.Numeric(10, 2), nullable=False, comment='分配到该发票的金额')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    receipt = db.relationship('ProjectReceipt', backref=db.backref('invoice_allocations',
                              cascade='all, delete-orphan', lazy='dynamic'))
    invoice = db.relationship('ProjectInvoice', backref=db.backref('receipt_allocations',
                              cascade='all, delete-orphan', lazy='dynamic'))

    # 唯一约束
    __table_args__ = (
        db.UniqueConstraint('receipt_id', 'invoice_id', name='uq_receipt_invoice'),
    )

    def __repr__(self):
        return f'<ReceiptInvoiceAllocation R{self.receipt_id}->INV{self.invoice_id}: {self.allocated_amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'receipt_id': self.receipt_id,
            'invoice_id': self.invoice_id,
            'allocated_amount': float(self.allocated_amount) if self.allocated_amount else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }