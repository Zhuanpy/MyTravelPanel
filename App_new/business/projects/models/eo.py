# -*- coding: utf-8 -*-
"""EO相关模型 - 项目EO订单"""

from App_new.exts import db
from datetime import datetime


class ProjectEO(db.Model):
    """项目EO表"""
    __tablename__ = 'project_eos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False, comment='REF明细ID')
    eo_number = db.Column(db.String(30), unique=True, nullable=False, comment='EO编号（格式化显示）')

    # 外部系统信息
    external_system = db.Column(db.String(50), nullable=True, comment='外部系统名称')
    external_status = db.Column(db.String(50), nullable=True, comment='外部系统状态')
    external_reference = db.Column(db.String(100), nullable=True, comment='外部系统参考号')

    # 状态信息
    status = db.Column(db.Enum('draft', 'confirmed', 'paid', 'cancelled'),
                       default='draft', nullable=False, comment='状态')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    # supplier = db.relationship('Supplier', backref='eos')  # 暂时注释掉，避免循环导入
    ref = db.relationship('ProjectRef', back_populates='eos')

    def __repr__(self):
        return f'<ProjectEO {self.eo_number}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'ref_id': self.ref_id,
            'eo_number': self.eo_number,
            'external_system': self.external_system,
            'external_status': self.external_status,
            'external_reference': self.external_reference,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def is_external_synced(self):
        """检查是否与外部系统同步"""
        return bool(self.external_system and self.external_status and self.external_reference)

    @property
    def formatted_amount(self):
        """格式化金额显示（使用关联的REF成本价格）"""
        if not self.ref:
            return "SGD 0.00"
        currency = self.ref.currency if self.ref.currency else 'SGD'
        amount = float(self.ref.cost_price) if self.ref.cost_price else 0.0
        return f"{currency} {amount:,.2f}"
    
    @property
    def amount(self):
        """获取金额（从关联的REF获取）"""
        return self.ref.cost_price if self.ref and self.ref.cost_price else None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 如果没有设置eo_number，自动生成一个临时编号
        if not self.eo_number:
            # 生成一个临时编号，保存时会被替换
            self.eo_number = 'TEMP'
    
