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

    def __repr__(self):
        return f'<ProjectReceipt {self.receipt_number}: {self.amount} {self.currency}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'receipt_number': self.receipt_number,
            'ref_id': self.ref_id,
            'header_id': self.header_id,
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
        # 1. 直接关联的REF级别收款记录
        ref_receipts = cls.query.filter_by(ref_id=ref_id, status='confirmed').all()
        total_received = sum(float(r.amount) for r in ref_receipts)

        # 2. 项目级别收款记录中分配给该REF的金额
        project_receipts = cls.query.filter_by(header_id=header_id, ref_id=None, status='confirmed').all()
        for project_receipt in project_receipts:
            if project_receipt.extra_info:
                try:
                    distribution_info = json.loads(project_receipt.extra_info)
                    if 'distribution' in distribution_info:
                        for dist in distribution_info['distribution']:
                            if dist['ref_id'] == ref_id:
                                total_received += dist['amount']
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

        return total_received

    @classmethod
    def get_project_unpaid_amount(cls, header_id):
        """获取项目的总未收款金额"""
        from .project import ProjectHeader  # 避免循环导入
        header = ProjectHeader.query.get(header_id)
        if not header:
            return 0

        # 计算所有REF的未收款总额
        total_unpaid = 0
        for ref in header.refs:
            if ref.selling_price:
                # 计算该REF的已收款总额
                # 1. 直接关联的REF级别收款记录
                ref_receipts = cls.query.filter_by(ref_id=ref.id, status='confirmed').all()
                ref_received = sum(float(r.amount) for r in ref_receipts)

                # 2. 项目级别收款记录中分配给该REF的金额
                project_receipts = cls.query.filter_by(header_id=header_id, ref_id=None, status='confirmed').all()
                for project_receipt in project_receipts:
                    if project_receipt.extra_info:
                        try:
                            distribution_info = json.loads(project_receipt.extra_info)
                            if 'distribution' in distribution_info:
                                for dist in distribution_info['distribution']:
                                    if dist['ref_id'] == ref.id:
                                        ref_received += dist['amount']
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass

                ref_unpaid = float(ref.selling_price) - ref_received
                if ref_unpaid > 0:
                    total_unpaid += ref_unpaid

        return total_unpaid

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