# -*- coding: utf-8 -*-
"""结算单模型 - Settlement Batch"""

from App_new.exts import db
from datetime import datetime
from decimal import Decimal


class SettlementBatch(db.Model):
    """结算单 - 记录每次批量结算的信息"""
    __tablename__ = 'settlement_batches'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_number = db.Column(db.String(30), unique=True, nullable=False, comment='结算单号')

    # 结算信息
    settlement_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment='结算日期')
    settled_by = db.Column(db.String(50), nullable=False, comment='结算人')

    # 汇总数据
    project_count = db.Column(db.Integer, nullable=False, default=0, comment='项目数量')
    total_profit = db.Column(db.Numeric(15, 2), nullable=False, default=0, comment='总利润')
    total_operator_profit = db.Column(db.Numeric(15, 2), nullable=False, default=0, comment='操作员利润合计')
    total_sales_profit = db.Column(db.Numeric(15, 2), nullable=False, default=0, comment='业务员利润合计')
    total_company_profit = db.Column(db.Numeric(15, 2), nullable=False, default=0, comment='公司利润合计')

    # 状态和备注
    status = db.Column(db.String(20), default='confirmed', nullable=False, comment='状态(confirmed/cancelled)')
    remarks = db.Column(db.Text, nullable=True, comment='备注')

    # 公司结算（分成发放）状态
    # 和 status 是两件事：status 说这张单据算不算数，这里说钱有没有发到员工手上。
    # 结算单确认后员工分成才算出来，实际转账通常晚几天，所以要单独记一笔。
    payout_status = db.Column(db.String(20), default='pending', nullable=False,
                              comment='公司结算状态(pending待结算/paid已结算)')
    payout_date = db.Column(db.DateTime, nullable=True, comment='公司结算日期')
    payout_by = db.Column(db.String(50), nullable=True, comment='公司结算操作人')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    projects = db.relationship('ProjectHeader', backref='settlement_batch', lazy='dynamic')

    @property
    def is_paid_out(self):
        """分成是否已发放给员工"""
        return self.payout_status == 'paid'

    @staticmethod
    def generate_batch_number():
        """生成结算单号，格式：SB-YYYYMMDD-XXX"""
        today = datetime.now()
        prefix = f"SB-{today.strftime('%Y%m%d')}"

        last_batch = SettlementBatch.query.filter(
            SettlementBatch.batch_number.like(f'{prefix}%')
        ).order_by(SettlementBatch.batch_number.desc()).first()

        if last_batch:
            last_num = int(last_batch.batch_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}-{new_num:03d}"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'batch_number': self.batch_number,
            'settlement_date': self.settlement_date.isoformat() if self.settlement_date else None,
            'settled_by': self.settled_by,
            'project_count': self.project_count,
            'total_profit': float(self.total_profit) if self.total_profit else 0,
            'total_operator_profit': float(self.total_operator_profit) if self.total_operator_profit else 0,
            'total_sales_profit': float(self.total_sales_profit) if self.total_sales_profit else 0,
            'total_company_profit': float(self.total_company_profit) if self.total_company_profit else 0,
            'status': self.status,
            'payout_status': self.payout_status,
            'payout_date': self.payout_date.isoformat() if self.payout_date else None,
            'payout_by': self.payout_by,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<SettlementBatch {self.batch_number}>'
