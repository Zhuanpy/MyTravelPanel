# -*- coding: utf-8 -*-
"""
统一产品规则表
包含预订规则、取消规则、退改规则等
"""

from datetime import datetime
from App_new.exts import db


class RuleType:
    """规则类型"""
    BOOKING = 'booking'         # 预订规则
    CANCEL = 'cancel'           # 取消规则
    REFUND = 'refund'           # 退款规则
    CHANGE = 'change'           # 改期规则
    INVENTORY = 'inventory'     # 库存规则
    LIMIT = 'limit'             # 限购规则

    CHOICES = [
        (BOOKING, '预订规则'),
        (CANCEL, '取消规则'),
        (REFUND, '退款规则'),
        (CHANGE, '改期规则'),
        (INVENTORY, '库存规则'),
        (LIMIT, '限购规则'),
    ]


class ProductsRule(db.Model):
    """
    统一产品规则表
    管理产品的预订、取消、退改等各类规则
    """
    __tablename__ = 'products_rule'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 关联产品 ==========
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, index=True, comment='关联产品ID')

    # ========== 规则类型 ==========
    rule_type = db.Column(db.String(20), nullable=False, index=True,
                          comment='规则类型：booking/cancel/refund/change/inventory/limit')
    rule_name = db.Column(db.String(100), comment='规则名称')

    # ========== 预订规则字段 ==========
    advance_days = db.Column(db.Integer, comment='提前预订天数')
    advance_hours = db.Column(db.Integer, comment='提前预订小时数')
    min_participants = db.Column(db.Integer, default=1, comment='最少成团人数')
    max_participants = db.Column(db.Integer, comment='最大参团人数')

    # ========== 取消/退款规则字段 ==========
    cancel_days_before = db.Column(db.Integer, comment='取消需提前天数')
    cancel_fee_rate = db.Column(db.Numeric(5, 2), comment='取消费率（百分比）')
    cancel_fee_fixed = db.Column(db.Numeric(12, 2), comment='固定取消费')
    refund_days = db.Column(db.Integer, comment='退款处理天数')
    is_refundable = db.Column(db.Boolean, default=True, comment='是否可退款')

    # ========== 改期规则字段 ==========
    change_days_before = db.Column(db.Integer, comment='改期需提前天数')
    change_fee_rate = db.Column(db.Numeric(5, 2), comment='改期费率（百分比）')
    change_fee_fixed = db.Column(db.Numeric(12, 2), comment='固定改期费')
    max_change_times = db.Column(db.Integer, default=1, comment='最大改期次数')
    is_changeable = db.Column(db.Boolean, default=True, comment='是否可改期')

    # ========== 库存规则字段 ==========
    total_stock = db.Column(db.Integer, comment='总库存')
    daily_stock = db.Column(db.Integer, comment='日库存')
    alert_stock = db.Column(db.Integer, comment='库存预警值')

    # ========== 限购规则字段 ==========
    limit_per_order = db.Column(db.Integer, comment='每单限购数量')
    limit_per_user = db.Column(db.Integer, comment='每人限购数量')
    limit_per_day = db.Column(db.Integer, comment='每日限购数量')

    # ========== 阶梯规则（JSON格式）==========
    # 例如取消规则：[{"days": 7, "rate": 0}, {"days": 3, "rate": 30}, {"days": 1, "rate": 50}, {"days": 0, "rate": 100}]
    tiered_rules = db.Column(db.Text, comment='阶梯规则JSON')

    # ========== 有效期 ==========
    valid_from = db.Column(db.Date, comment='规则生效日期')
    valid_until = db.Column(db.Date, comment='规则失效日期')

    # ========== 状态 ==========
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    priority = db.Column(db.Integer, default=0, comment='优先级')

    # ========== 描述 ==========
    description = db.Column(db.Text, comment='规则描述')
    remark = db.Column(db.String(500), comment='备注')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    def __repr__(self):
        return f'<ProductsRule {self.id}: {self.rule_type}>'

    @property
    def is_valid(self):
        """检查规则是否在有效期内"""
        today = datetime.now().date()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        return self.is_active

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'product_id': self.product_id,
            'rule_type': self.rule_type,
            'rule_name': self.rule_name,
            'advance_days': self.advance_days,
            'advance_hours': self.advance_hours,
            'min_participants': self.min_participants,
            'max_participants': self.max_participants,
            'cancel_days_before': self.cancel_days_before,
            'cancel_fee_rate': float(self.cancel_fee_rate) if self.cancel_fee_rate else None,
            'cancel_fee_fixed': float(self.cancel_fee_fixed) if self.cancel_fee_fixed else None,
            'is_refundable': self.is_refundable,
            'change_days_before': self.change_days_before,
            'change_fee_rate': float(self.change_fee_rate) if self.change_fee_rate else None,
            'is_changeable': self.is_changeable,
            'total_stock': self.total_stock,
            'daily_stock': self.daily_stock,
            'limit_per_order': self.limit_per_order,
            'limit_per_user': self.limit_per_user,
            'tiered_rules': json.loads(self.tiered_rules) if self.tiered_rules else None,
            'is_active': self.is_active,
            'is_valid': self.is_valid,
            'description': self.description,
        }

    def calculate_cancel_fee(self, order_amount, days_before_departure):
        """
        计算取消费用

        Args:
            order_amount: 订单金额
            days_before_departure: 距离出发天数

        Returns:
            取消费用金额
        """
        import json

        # 如果不可退款
        if not self.is_refundable:
            return order_amount

        # 优先使用阶梯规则
        if self.tiered_rules:
            try:
                tiers = json.loads(self.tiered_rules)
                # 按天数降序排列
                tiers = sorted(tiers, key=lambda x: x.get('days', 0), reverse=True)

                for tier in tiers:
                    if days_before_departure >= tier.get('days', 0):
                        rate = tier.get('rate', 0)
                        return float(order_amount) * rate / 100
            except (json.JSONDecodeError, TypeError):
                pass

        # 使用简单规则
        if self.cancel_days_before and days_before_departure >= self.cancel_days_before:
            return 0  # 满足提前天数要求，无取消费

        # 计算取消费
        if self.cancel_fee_fixed:
            return float(self.cancel_fee_fixed)
        elif self.cancel_fee_rate:
            return float(order_amount) * float(self.cancel_fee_rate) / 100

        return 0

    @classmethod
    def get_active_rule(cls, product_id, rule_type):
        """
        获取产品的有效规则

        Args:
            product_id: 产品ID
            rule_type: 规则类型

        Returns:
            ProductsRule对象或None
        """
        today = datetime.now().date()

        return cls.query.filter(
            cls.product_id == product_id,
            cls.rule_type == rule_type,
            cls.is_active == True,
            db.or_(cls.valid_from == None, cls.valid_from <= today),
            db.or_(cls.valid_until == None, cls.valid_until >= today)
        ).order_by(cls.priority.desc()).first()
