"""
购物车模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from ...exts import db


class CartItem(db.Model):
    """会员购物车项目"""
    __tablename__ = 'member_cart_items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False, index=True)

    # 产品关联
    product_id = Column(Integer, nullable=False, comment='主产品ID')
    variant_id = Column(Integer, nullable=False, comment='票种变体ID')

    # 数量
    adult_qty = Column(Integer, default=1, comment='成人数量')
    child_qty = Column(Integer, default=0, comment='儿童数量')

    # 快照价格（加入时的价格，结算时重新校验）
    adult_price = Column(Numeric(12, 2), nullable=False, default=0, comment='成人单价快照')
    child_price = Column(Numeric(12, 2), nullable=False, default=0, comment='儿童单价快照')
    currency = Column(String(10), default='SGD')

    # 游玩日期（可选，结算时填）
    visit_date = Column(String(20), comment='游玩日期')

    # 快照信息：产品名、变体名、图片、地点等
    properties = Column(JSON, comment='产品快照信息')

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    user = relationship('AuthUser', backref='cart_items')

    @property
    def line_total(self):
        """该行小计"""
        adult = float(self.adult_price or 0) * (self.adult_qty or 0)
        child = float(self.child_price or 0) * (self.child_qty or 0)
        return adult + child

    @property
    def total_pax(self):
        """总人数"""
        return (self.adult_qty or 0) + (self.child_qty or 0)

    def __repr__(self):
        return f'<CartItem {self.id} user={self.user_id} variant={self.variant_id}>'
