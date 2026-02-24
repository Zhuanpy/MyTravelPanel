# -*- coding: utf-8 -*-
"""
门票产品变体表
主产品（products_unified）的票种变体，如：普通门票、快捷通道、VIP门票等
"""

from datetime import datetime
from App_new.exts import db


class ProductsTicketVariant(db.Model):
    """
    门票变体表
    与 ProductsUnified 是多对一关系（一个景点有多种票）
    """
    __tablename__ = 'products_ticket_variant'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, index=True, comment='所属主产品ID')

    # ========== 变体信息 ==========
    variant_name = db.Column(db.String(200), nullable=False, comment='变体名称（中文）')
    variant_name_en = db.Column(db.String(200), comment='变体名称（英文）')
    description = db.Column(db.Text, comment='变体描述')
    sort_order = db.Column(db.Integer, default=0, comment='排序权重')
    is_active = db.Column(db.Boolean, default=True, comment='是否激活')

    # ========== 成人价格 ==========
    adult_selling_price = db.Column(db.Numeric(12, 2), comment='成人售价')
    adult_cost_price = db.Column(db.Numeric(12, 2), comment='成人成本价')

    # ========== 儿童价格 ==========
    child_selling_price = db.Column(db.Numeric(12, 2), comment='儿童售价')
    child_cost_price = db.Column(db.Numeric(12, 2), comment='儿童成本价')

    # ========== 票种附加信息 ==========
    delivery_type = db.Column(db.String(20), default='e_ticket', comment='取票方式')
    includes = db.Column(db.Text, comment='费用包含')
    excludes = db.Column(db.Text, comment='费用不含')
    important_notes = db.Column(db.Text, comment='重要提示')

    # ========== 其他 ==========
    currency = db.Column(db.String(10), default='SGD', comment='币种')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    def __repr__(self):
        return f'<ProductsTicketVariant {self.id}: {self.variant_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'variant_name': self.variant_name,
            'variant_name_en': self.variant_name_en,
            'description': self.description,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'adult_selling_price': float(self.adult_selling_price) if self.adult_selling_price else None,
            'adult_cost_price': float(self.adult_cost_price) if self.adult_cost_price else None,
            'child_selling_price': float(self.child_selling_price) if self.child_selling_price else None,
            'child_cost_price': float(self.child_cost_price) if self.child_cost_price else None,
            'currency': self.currency,
            'delivery_type': self.delivery_type,
            'includes': self.includes,
            'excludes': self.excludes,
            'important_notes': self.important_notes,
        }
