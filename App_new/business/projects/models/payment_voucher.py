# -*- coding: utf-8 -*-
"""Payment Voucher 付款凭证模型"""

from App_new.exts import db
from datetime import datetime


class PaymentVoucher(db.Model):
    """付款凭证模型 - 用于记录结算批次"""
    __tablename__ = 'payment_vouchers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    voucher_no = db.Column(db.String(50), unique=True, nullable=False, comment='凭证号码')

    # 结算信息
    settle_date = db.Column(db.DateTime, default=datetime.utcnow, comment='结算日期')
    settled_by = db.Column(db.String(50), nullable=True, comment='结算人')

    # 汇总信息
    project_count = db.Column(db.Integer, default=0, comment='项目数量')
    total_selling = db.Column(db.Numeric(15, 2), default=0, comment='总销售金额')
    total_cost = db.Column(db.Numeric(15, 2), default=0, comment='总成本')
    total_profit = db.Column(db.Numeric(15, 2), default=0, comment='总利润')
    total_operator_profit = db.Column(db.Numeric(15, 2), default=0, comment='操作员利润合计')
    total_sales_profit = db.Column(db.Numeric(15, 2), default=0, comment='业务员利润合计')
    total_company_profit = db.Column(db.Numeric(15, 2), default=0, comment='公司利润合计')

    # 备注
    remarks = db.Column(db.Text, nullable=True, comment='备注')

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关联的项目
    projects = db.relationship('ProjectHeader', backref='payment_voucher', lazy='dynamic')

    def __repr__(self):
        return f'<PaymentVoucher {self.voucher_no}>'

    @classmethod
    def generate_voucher_no(cls):
        """生成凭证号码 格式: PV + 年月日 + 序号，如 PV20260110001"""
        today = datetime.now()
        date_str = today.strftime('%Y%m%d')
        prefix = f'PV{date_str}'

        # 查找当天最大序号
        last_voucher = cls.query.filter(
            cls.voucher_no.like(f'{prefix}%')
        ).order_by(cls.voucher_no.desc()).first()

        if last_voucher:
            try:
                last_seq = int(last_voucher.voucher_no[-3:])
                new_seq = last_seq + 1
            except ValueError:
                new_seq = 1
        else:
            new_seq = 1

        return f'{prefix}{new_seq:03d}'

    def to_dict(self):
        return {
            'id': self.id,
            'voucher_no': self.voucher_no,
            'settle_date': self.settle_date.isoformat() if self.settle_date else None,
            'settled_by': self.settled_by,
            'project_count': self.project_count,
            'total_selling': float(self.total_selling) if self.total_selling else 0,
            'total_cost': float(self.total_cost) if self.total_cost else 0,
            'total_profit': float(self.total_profit) if self.total_profit else 0,
            'total_operator_profit': float(self.total_operator_profit) if self.total_operator_profit else 0,
            'total_sales_profit': float(self.total_sales_profit) if self.total_sales_profit else 0,
            'total_company_profit': float(self.total_company_profit) if self.total_company_profit else 0,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
