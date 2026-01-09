# -*- coding: utf-8 -*-
"""
统一产品价格表
支持多种价格类型：标准价/促销价/会员价/渠道价等
"""

from datetime import datetime
from App_new.exts import db


class PriceType:
    """价格类型"""
    STANDARD = 'standard'   # 标准价
    PROMO = 'promo'         # 促销价
    MEMBER = 'member'       # 会员价
    AGENT = 'agent'         # 代理价
    GROUP = 'group'         # 团购价
    EARLY_BIRD = 'early'    # 早鸟价
    LAST_MINUTE = 'last'    # 尾单价

    CHOICES = [
        (STANDARD, '标准价'),
        (PROMO, '促销价'),
        (MEMBER, '会员价'),
        (AGENT, '代理价'),
        (GROUP, '团购价'),
        (EARLY_BIRD, '早鸟价'),
        (LAST_MINUTE, '尾单价'),
    ]


class PeopleType:
    """人群类型"""
    ADULT = 'adult'         # 成人
    CHILD = 'child'         # 儿童
    INFANT = 'infant'       # 婴儿
    SENIOR = 'senior'       # 老人
    STUDENT = 'student'     # 学生

    CHOICES = [
        (ADULT, '成人'),
        (CHILD, '儿童'),
        (INFANT, '婴儿'),
        (SENIOR, '老人'),
        (STUDENT, '学生'),
    ]


class ProductsPrice(db.Model):
    """
    统一产品价格表
    支持按人群、日期、数量等多维度定价
    """
    __tablename__ = 'products_price'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 关联产品 ==========
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, index=True, comment='关联产品ID')

    # ========== 价格类型 ==========
    price_type = db.Column(db.String(20), default='standard', index=True,
                           comment='价格类型：standard/promo/member/agent/group/early/last')
    price_name = db.Column(db.String(100), comment='价格名称（如：双十一特惠）')

    # ========== 人群类型 ==========
    people_type = db.Column(db.String(20), default='adult',
                            comment='人群类型：adult/child/infant/senior/student')

    # ========== 价格信息 ==========
    cost_price = db.Column(db.Numeric(12, 2), comment='成本价')
    selling_price = db.Column(db.Numeric(12, 2), nullable=False, comment='销售价')
    original_price = db.Column(db.Numeric(12, 2), comment='原价（划线价）')
    currency = db.Column(db.String(10), default='SGD', comment='币种')

    # ========== 数量阶梯价 ==========
    min_quantity = db.Column(db.Integer, default=1, comment='最小购买数量')
    max_quantity = db.Column(db.Integer, comment='最大购买数量')

    # ========== 有效期 ==========
    valid_from = db.Column(db.Date, comment='价格生效日期')
    valid_until = db.Column(db.Date, comment='价格失效日期')

    # ========== 适用日期（针对旅游产品的出发日期等）==========
    apply_date_from = db.Column(db.Date, comment='适用开始日期')
    apply_date_until = db.Column(db.Date, comment='适用结束日期')
    apply_weekdays = db.Column(db.String(20), comment='适用星期（如：1,2,3,4,5）')

    # ========== 状态 ==========
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    priority = db.Column(db.Integer, default=0, comment='优先级（数值越大优先级越高）')

    # ========== 备注 ==========
    remark = db.Column(db.String(500), comment='备注')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    def __repr__(self):
        return f'<ProductsPrice {self.id}: {self.price_type}-{self.people_type}>'

    @property
    def is_valid(self):
        """检查价格是否在有效期内"""
        today = datetime.now().date()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        return self.is_active

    @property
    def discount_rate(self):
        """计算折扣率"""
        if self.original_price and self.original_price > 0:
            return round((1 - float(self.selling_price) / float(self.original_price)) * 100, 1)
        return 0

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'price_type': self.price_type,
            'price_name': self.price_name,
            'people_type': self.people_type,
            'cost_price': float(self.cost_price) if self.cost_price else None,
            'selling_price': float(self.selling_price) if self.selling_price else None,
            'original_price': float(self.original_price) if self.original_price else None,
            'currency': self.currency,
            'min_quantity': self.min_quantity,
            'max_quantity': self.max_quantity,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'is_active': self.is_active,
            'is_valid': self.is_valid,
            'discount_rate': self.discount_rate,
        }

    @classmethod
    def get_effective_price(cls, product_id, people_type='adult', price_type='standard', quantity=1, apply_date=None):
        """
        获取有效价格

        Args:
            product_id: 产品ID
            people_type: 人群类型
            price_type: 价格类型
            quantity: 购买数量
            apply_date: 适用日期（如出发日期）

        Returns:
            ProductsPrice对象或None
        """
        today = datetime.now().date()
        apply_date = apply_date or today

        query = cls.query.filter(
            cls.product_id == product_id,
            cls.people_type == people_type,
            cls.is_active == True
        )

        # 价格类型筛选
        if price_type:
            query = query.filter(cls.price_type == price_type)

        # 有效期筛选
        query = query.filter(
            db.or_(cls.valid_from == None, cls.valid_from <= today),
            db.or_(cls.valid_until == None, cls.valid_until >= today)
        )

        # 适用日期筛选
        query = query.filter(
            db.or_(cls.apply_date_from == None, cls.apply_date_from <= apply_date),
            db.or_(cls.apply_date_until == None, cls.apply_date_until >= apply_date)
        )

        # 数量筛选
        query = query.filter(
            cls.min_quantity <= quantity,
            db.or_(cls.max_quantity == None, cls.max_quantity >= quantity)
        )

        # 按优先级排序，取最高优先级的价格
        return query.order_by(cls.priority.desc()).first()
