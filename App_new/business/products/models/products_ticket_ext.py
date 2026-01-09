# -*- coding: utf-8 -*-
"""
门票/玩乐产品扩展表
存储门票特有的属性
"""

from datetime import datetime
from App_new.exts import db


class TicketType:
    """门票类型"""
    SCENIC = 'scenic'           # 景区门票
    SHOW = 'show'               # 演出门票
    ACTIVITY = 'activity'       # 活动体验
    MUSEUM = 'museum'           # 博物馆
    THEME_PARK = 'theme_park'   # 主题乐园
    WATER_PARK = 'water_park'   # 水上乐园

    CHOICES = [
        (SCENIC, '景区门票'),
        (SHOW, '演出门票'),
        (ACTIVITY, '活动体验'),
        (MUSEUM, '博物馆'),
        (THEME_PARK, '主题乐园'),
        (WATER_PARK, '水上乐园'),
    ]


class TicketDelivery:
    """取票方式"""
    E_TICKET = 'e_ticket'       # 电子票
    PHYSICAL = 'physical'       # 实体票
    VOUCHER = 'voucher'         # 兑换券
    PICKUP = 'pickup'           # 现场取票

    CHOICES = [
        (E_TICKET, '电子票'),
        (PHYSICAL, '实体票'),
        (VOUCHER, '兑换券'),
        (PICKUP, '现场取票'),
    ]


class ProductsTicketExt(db.Model):
    """
    门票/玩乐产品扩展表
    存储门票类产品的特有属性
    """
    __tablename__ = 'products_ticket_ext'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 关联主表 ==========
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, unique=True, comment='关联产品ID')

    # ========== 门票类型 ==========
    ticket_type = db.Column(db.String(30), comment='门票类型：scenic/show/activity/museum/theme_park/water_park')

    # ========== 场馆信息 ==========
    venue_name = db.Column(db.String(200), comment='场馆名称')
    venue_address = db.Column(db.String(500), comment='场馆地址')
    venue_phone = db.Column(db.String(50), comment='场馆电话')
    latitude = db.Column(db.Numeric(10, 7), comment='纬度')
    longitude = db.Column(db.Numeric(10, 7), comment='经度')

    # ========== 开放时间 ==========
    opening_hours = db.Column(db.String(500), comment='开放时间说明')
    opening_time = db.Column(db.Time, comment='开门时间')
    closing_time = db.Column(db.Time, comment='关门时间')
    closed_days = db.Column(db.String(100), comment='闭馆日（如：周一）')

    # ========== 游玩信息 ==========
    duration_minutes = db.Column(db.Integer, comment='建议游玩时长（分钟）')
    best_time = db.Column(db.String(200), comment='最佳游玩时间')
    tips = db.Column(db.Text, comment='游玩攻略')

    # ========== 取票信息 ==========
    delivery_type = db.Column(db.String(20), default='e_ticket',
                              comment='取票方式：e_ticket/physical/voucher/pickup')
    delivery_info = db.Column(db.Text, comment='取票说明')
    entry_method = db.Column(db.String(200), comment='入园方式（如：扫码入园、换票入园）')
    ticket_validity = db.Column(db.String(200), comment='门票有效期说明')

    # ========== 演出信息（show类型）==========
    show_time = db.Column(db.String(500), comment='演出时间')
    show_duration = db.Column(db.Integer, comment='演出时长（分钟）')
    seat_type = db.Column(db.String(100), comment='座位类型')
    seat_map = db.Column(db.Text, comment='座位图URL')

    # ========== 活动信息（activity类型）==========
    activity_date = db.Column(db.Date, comment='活动日期')
    activity_time = db.Column(db.Time, comment='活动开始时间')
    meeting_point = db.Column(db.String(500), comment='集合地点')
    meeting_time = db.Column(db.String(100), comment='集合时间说明')

    # ========== 设施信息 ==========
    facilities = db.Column(db.Text, comment='设施介绍JSON')
    amenities = db.Column(db.Text, comment='配套设施（如：停车场、餐厅、商店）')

    # ========== 预约要求 ==========
    need_reservation = db.Column(db.Boolean, default=False, comment='是否需要预约')
    reservation_info = db.Column(db.Text, comment='预约说明')
    id_required = db.Column(db.Boolean, default=False, comment='是否需要身份证')

    # ========== 限制条件 ==========
    age_limit = db.Column(db.String(100), comment='年龄限制')
    height_limit = db.Column(db.String(100), comment='身高限制')
    health_requirement = db.Column(db.Text, comment='健康要求')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # ========== 关联关系 ==========
    product = db.relationship('ProductsUnified', backref=db.backref('ticket_ext', uselist=False))

    def __repr__(self):
        return f'<ProductsTicketExt {self.id}: {self.venue_name}>'

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'product_id': self.product_id,
            'ticket_type': self.ticket_type,
            'venue_name': self.venue_name,
            'venue_address': self.venue_address,
            'venue_phone': self.venue_phone,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'opening_hours': self.opening_hours,
            'opening_time': self.opening_time.strftime('%H:%M') if self.opening_time else None,
            'closing_time': self.closing_time.strftime('%H:%M') if self.closing_time else None,
            'closed_days': self.closed_days,
            'duration_minutes': self.duration_minutes,
            'best_time': self.best_time,
            'tips': self.tips,
            'delivery_type': self.delivery_type,
            'delivery_info': self.delivery_info,
            'entry_method': self.entry_method,
            'ticket_validity': self.ticket_validity,
            'show_time': self.show_time,
            'show_duration': self.show_duration,
            'seat_type': self.seat_type,
            'meeting_point': self.meeting_point,
            'meeting_time': self.meeting_time,
            'facilities': json.loads(self.facilities) if self.facilities else None,
            'amenities': self.amenities,
            'need_reservation': self.need_reservation,
            'reservation_info': self.reservation_info,
            'id_required': self.id_required,
            'age_limit': self.age_limit,
            'height_limit': self.height_limit,
            'health_requirement': self.health_requirement,
        }
