"""
订单相关模型
"""

from datetime import datetime, timedelta
from enum import Enum
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from ...exts import db


class OrderStatus(Enum):
    """订单状态枚举"""
    DRAFT = "draft"           # 草稿
    PENDING = "pending"       # 待处理
    CONFIRMED = "confirmed"   # 已确认
    IN_PROGRESS = "in_progress"  # 处理中
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消
    REFUNDED = "refunded"     # 已退款


class ServiceType(Enum):
    """服务类型枚举"""
    VISA = "visa"             # 签证服务
    FLIGHT = "flight"         # 机票预订
    HOTEL = "hotel"           # 酒店预订
    TOUR = "tour"             # 旅游套餐
    INSURANCE = "insurance"   # 旅游保险
    TRANSFER = "transfer"     # 接送服务


class Order(db.Model):
    """会员订单模型"""
    __tablename__ = 'member_orders'
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False)
    
    # 订单基本信息
    service_type = Column(String(20), nullable=False)  # 服务类型
    service_name = Column(String(200), nullable=False)  # 服务名称
    description = Column(Text)  # 服务描述
    
    # 订单状态
    status = Column(String(20), default=OrderStatus.DRAFT.value, nullable=False)
    priority = Column(String(20), default='normal')  # 优先级: low, normal, high, urgent
    
    # 价格信息
    base_price = Column(Numeric(10, 2), nullable=False, default=0)
    additional_fees = Column(Numeric(10, 2), default=0)  # 附加费用
    discount_amount = Column(Numeric(10, 2), default=0)  # 折扣金额
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(3), default='SGD')
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = Column(DateTime)  # 确认时间
    completed_at = Column(DateTime)  # 完成时间
    cancelled_at = Column(DateTime)  # 取消时间
    
    # 客户信息
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(120), nullable=False)
    customer_phone = Column(String(20))
    customer_address = Column(Text)
    
    # 特殊要求
    special_requirements = Column(Text)  # 特殊要求
    notes = Column(Text)  # 备注
    
    # 关联数据
    user = relationship('AuthUser', backref='orders')
    order_items = relationship('OrderItem', backref='order', cascade='all, delete-orphan')
    documents = relationship('OrderDocument', backref='order', cascade='all, delete-orphan')
    payments = relationship('Payment', backref='order', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.order_number}>'
    
    @property
    def status_display(self):
        """状态显示名称"""
        status_map = {
            OrderStatus.DRAFT.value: '草稿',
            OrderStatus.PENDING.value: '待处理',
            OrderStatus.CONFIRMED.value: '已确认',
            OrderStatus.IN_PROGRESS.value: '处理中',
            OrderStatus.COMPLETED.value: '已完成',
            OrderStatus.CANCELLED.value: '已取消',
            OrderStatus.REFUNDED.value: '已退款'
        }
        return status_map.get(self.status, self.status)
    
    @property
    def status_color(self):
        """状态颜色"""
        color_map = {
            OrderStatus.DRAFT.value: 'secondary',
            OrderStatus.PENDING.value: 'warning',
            OrderStatus.CONFIRMED.value: 'info',
            OrderStatus.IN_PROGRESS.value: 'primary',
            OrderStatus.COMPLETED.value: 'success',
            OrderStatus.CANCELLED.value: 'danger',
            OrderStatus.REFUNDED.value: 'dark'
        }
        return color_map.get(self.status, 'secondary')
    
    def calculate_total(self):
        """计算订单总金额"""
        self.total_amount = self.base_price + self.additional_fees - self.discount_amount
        return self.total_amount
    
    def can_cancel(self):
        """是否可以取消"""
        return self.status in [OrderStatus.DRAFT.value, OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]
    
    def can_modify(self):
        """是否可以修改"""
        return self.status in [OrderStatus.DRAFT.value, OrderStatus.PENDING.value]


class OrderItem(db.Model):
    """会员订单项目模型"""
    __tablename__ = 'member_order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('member_orders.id'), nullable=False)
    
    # 项目信息
    item_name = Column(String(200), nullable=False)
    item_description = Column(Text)
    item_type = Column(String(50))  # 项目类型
    
    # 数量和价格
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # 特殊属性
    properties = Column(JSON)  # 存储特殊属性，如护照信息、航班信息等
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OrderItem {self.item_name}>'
    
    def calculate_total(self):
        """计算项目总价"""
        self.total_price = self.quantity * self.unit_price
        return self.total_price


class OrderDocument(db.Model):
    """会员订单文档模型"""
    __tablename__ = 'member_order_documents'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('member_orders.id'), nullable=False)
    
    # 文档信息
    document_name = Column(String(200), nullable=False)
    document_type = Column(String(50), nullable=False)  # passport, photo, form, etc.
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # 文件大小（字节）
    mime_type = Column(String(100))  # MIME类型
    
    # 状态
    is_verified = Column(Boolean, default=False)  # 是否已验证
    verification_notes = Column(Text)  # 验证备注
    
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    
    def __repr__(self):
        return f'<OrderDocument {self.document_name}>'


class Payment(db.Model):
    """会员订单支付模型"""
    __tablename__ = 'member_order_payments'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('member_orders.id'), nullable=False)
    
    # 支付信息
    payment_method = Column(String(50), nullable=False)  # credit_card, bank_transfer, paypal, etc.
    payment_reference = Column(String(100))  # 支付参考号
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default='SGD')
    
    # 状态
    status = Column(String(20), default='pending')  # pending, completed, failed, refunded
    transaction_id = Column(String(100))  # 交易ID
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    def __repr__(self):
        return f'<Payment {self.payment_reference}>'


class ServiceTemplate(db.Model):
    """会员服务模板模型"""
    __tablename__ = 'member_service_templates'
    
    id = Column(Integer, primary_key=True)
    
    # 服务基本信息
    service_type = Column(String(20), nullable=False)
    service_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 价格信息
    base_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default='SGD')
    
    # 处理信息
    processing_time = Column(String(100))  # 处理时间描述
    requirements = Column(Text)  # 要求描述
    required_documents = Column(JSON)  # 必需文档列表
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # 是否推荐
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ServiceTemplate {self.service_name}>'
