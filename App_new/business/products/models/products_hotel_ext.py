# -*- coding: utf-8 -*-
"""
酒店产品扩展表
存储酒店特有的属性
"""

from datetime import datetime
from App_new.exts import db


class HotelStarRating:
    """酒店星级"""
    TWO_STAR = 2
    THREE_STAR = 3
    FOUR_STAR = 4
    FIVE_STAR = 5
    LUXURY = 6  # 超豪华

    CHOICES = [
        (TWO_STAR, '二星级'),
        (THREE_STAR, '三星级'),
        (FOUR_STAR, '四星级'),
        (FIVE_STAR, '五星级'),
        (LUXURY, '超豪华'),
    ]


class RoomType:
    """房型"""
    STANDARD = 'standard'       # 标准间
    SUPERIOR = 'superior'       # 高级房
    DELUXE = 'deluxe'           # 豪华房
    SUITE = 'suite'             # 套房
    FAMILY = 'family'           # 家庭房
    VILLA = 'villa'             # 别墅

    CHOICES = [
        (STANDARD, '标准间'),
        (SUPERIOR, '高级房'),
        (DELUXE, '豪华房'),
        (SUITE, '套房'),
        (FAMILY, '家庭房'),
        (VILLA, '别墅'),
    ]


class BedType:
    """床型"""
    SINGLE = 'single'           # 单人床
    DOUBLE = 'double'           # 双人床
    QUEEN = 'queen'             # 大床
    KING = 'king'               # 特大床
    TWIN = 'twin'               # 双床
    TRIPLE = 'triple'           # 三床

    CHOICES = [
        (SINGLE, '单人床'),
        (DOUBLE, '双人床'),
        (QUEEN, '大床'),
        (KING, '特大床'),
        (TWIN, '双床'),
        (TRIPLE, '三床'),
    ]


class ProductsHotelExt(db.Model):
    """
    酒店产品扩展表
    存储酒店类产品的特有属性
    """
    __tablename__ = 'products_hotel_ext'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 关联主表 ==========
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, unique=True, comment='关联产品ID')

    # ========== 酒店基本信息 ==========
    hotel_name = db.Column(db.String(200), comment='酒店名称')
    hotel_name_en = db.Column(db.String(200), comment='酒店英文名')
    hotel_brand = db.Column(db.String(100), comment='酒店品牌')
    hotel_chain = db.Column(db.String(100), comment='酒店集团')
    star_rating = db.Column(db.Integer, comment='星级：2/3/4/5/6')
    hotel_type = db.Column(db.String(50), comment='酒店类型：商务/度假/精品/民宿')
    hotel_rating = db.Column(db.Numeric(3, 2), comment='用户评分')
    total_rooms = db.Column(db.Integer, comment='总房间数')

    # ========== 位置信息 ==========
    hotel_address = db.Column(db.String(500), comment='酒店地址')
    hotel_address_en = db.Column(db.String(500), comment='酒店英文地址')
    district = db.Column(db.String(100), comment='所在区域')
    latitude = db.Column(db.Numeric(10, 7), comment='纬度')
    longitude = db.Column(db.Numeric(10, 7), comment='经度')
    nearby_attractions = db.Column(db.Text, comment='周边景点JSON')
    transportation = db.Column(db.Text, comment='交通信息')

    # ========== 房型信息 ==========
    room_type = db.Column(db.String(30), comment='房型：standard/superior/deluxe/suite/family/villa')
    room_name = db.Column(db.String(100), comment='房间名称')
    room_name_en = db.Column(db.String(100), comment='房间英文名')
    room_size = db.Column(db.Numeric(8, 2), comment='房间面积（平方米）')
    floor_range = db.Column(db.String(50), comment='楼层范围')
    room_view = db.Column(db.String(100), comment='房间景观：城市/海景/花园/泳池')
    bed_type = db.Column(db.String(20), comment='床型：single/double/queen/king/twin')
    bed_count = db.Column(db.Integer, default=1, comment='床数量')
    max_occupancy = db.Column(db.Integer, comment='最大入住人数')
    max_adults = db.Column(db.Integer, comment='最大成人数')
    max_children = db.Column(db.Integer, comment='最大儿童数')
    extra_bed_available = db.Column(db.Boolean, default=False, comment='是否可加床')
    extra_bed_price = db.Column(db.Numeric(10, 2), comment='加床费用')

    # ========== 早餐信息 ==========
    breakfast_included = db.Column(db.Boolean, default=False, comment='是否含早')
    breakfast_type = db.Column(db.String(50), comment='早餐类型：中式/西式/自助')
    breakfast_price = db.Column(db.Numeric(10, 2), comment='早餐单价')
    breakfast_for = db.Column(db.Integer, comment='含早人数')

    # ========== 入住规则 ==========
    check_in_time = db.Column(db.Time, comment='入住时间')
    check_out_time = db.Column(db.Time, comment='退房时间')
    early_check_in = db.Column(db.Boolean, default=False, comment='是否可提前入住')
    late_check_out = db.Column(db.Boolean, default=False, comment='是否可延迟退房')
    min_nights = db.Column(db.Integer, default=1, comment='最少入住晚数')
    max_nights = db.Column(db.Integer, comment='最多入住晚数')

    # ========== 房间设施 ==========
    room_amenities = db.Column(db.Text, comment='房间设施JSON')
    bathroom_amenities = db.Column(db.Text, comment='浴室设施JSON')
    has_wifi = db.Column(db.Boolean, default=True, comment='是否有WiFi')
    wifi_free = db.Column(db.Boolean, default=True, comment='WiFi是否免费')
    has_air_conditioning = db.Column(db.Boolean, default=True, comment='是否有空调')
    has_minibar = db.Column(db.Boolean, default=False, comment='是否有迷你吧')
    has_safe = db.Column(db.Boolean, default=False, comment='是否有保险箱')
    has_tv = db.Column(db.Boolean, default=True, comment='是否有电视')
    has_bathtub = db.Column(db.Boolean, default=False, comment='是否有浴缸')
    smoking_allowed = db.Column(db.Boolean, default=False, comment='是否可吸烟')

    # ========== 酒店设施 ==========
    hotel_facilities = db.Column(db.Text, comment='酒店设施JSON')
    has_pool = db.Column(db.Boolean, default=False, comment='是否有泳池')
    has_gym = db.Column(db.Boolean, default=False, comment='是否有健身房')
    has_spa = db.Column(db.Boolean, default=False, comment='是否有水疗')
    has_restaurant = db.Column(db.Boolean, default=False, comment='是否有餐厅')
    has_bar = db.Column(db.Boolean, default=False, comment='是否有酒吧')
    has_parking = db.Column(db.Boolean, default=False, comment='是否有停车场')
    parking_free = db.Column(db.Boolean, default=False, comment='停车是否免费')
    has_airport_shuttle = db.Column(db.Boolean, default=False, comment='是否有机场接送')

    # ========== 政策信息 ==========
    pets_allowed = db.Column(db.Boolean, default=False, comment='是否允许宠物')
    children_policy = db.Column(db.Text, comment='儿童政策')
    cancellation_policy = db.Column(db.Text, comment='取消政策')
    deposit_policy = db.Column(db.Text, comment='押金政策')
    payment_methods = db.Column(db.Text, comment='支付方式JSON')

    # ========== 联系信息 ==========
    hotel_phone = db.Column(db.String(50), comment='酒店电话')
    hotel_email = db.Column(db.String(100), comment='酒店邮箱')
    hotel_website = db.Column(db.String(200), comment='酒店官网')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # ========== 关联关系 ==========
    product = db.relationship('ProductsUnified', backref=db.backref('hotel_ext', uselist=False))

    def __repr__(self):
        return f'<ProductsHotelExt {self.id}: {self.hotel_name}>'

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'product_id': self.product_id,
            'hotel_name': self.hotel_name,
            'hotel_name_en': self.hotel_name_en,
            'hotel_brand': self.hotel_brand,
            'star_rating': self.star_rating,
            'hotel_type': self.hotel_type,
            'hotel_rating': float(self.hotel_rating) if self.hotel_rating else None,
            'hotel_address': self.hotel_address,
            'district': self.district,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'room_type': self.room_type,
            'room_name': self.room_name,
            'room_size': float(self.room_size) if self.room_size else None,
            'bed_type': self.bed_type,
            'max_occupancy': self.max_occupancy,
            'breakfast_included': self.breakfast_included,
            'breakfast_type': self.breakfast_type,
            'check_in_time': self.check_in_time.strftime('%H:%M') if self.check_in_time else None,
            'check_out_time': self.check_out_time.strftime('%H:%M') if self.check_out_time else None,
            'room_amenities': json.loads(self.room_amenities) if self.room_amenities else None,
            'hotel_facilities': json.loads(self.hotel_facilities) if self.hotel_facilities else None,
            'has_wifi': self.has_wifi,
            'has_pool': self.has_pool,
            'has_gym': self.has_gym,
            'has_parking': self.has_parking,
            'cancellation_policy': self.cancellation_policy,
        }
