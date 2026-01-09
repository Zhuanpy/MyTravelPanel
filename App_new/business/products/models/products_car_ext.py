# -*- coding: utf-8 -*-
"""
用车服务产品扩展表
存储用车服务特有的属性
"""

from datetime import datetime
from App_new.exts import db


class CarServiceType:
    """用车服务类型"""
    AIRPORT_PICKUP = 'airport_pickup'       # 接机
    AIRPORT_DROPOFF = 'airport_dropoff'     # 送机
    CHARTER = 'charter'                     # 包车
    TRANSFER = 'transfer'                   # 点对点接送
    HOURLY = 'hourly'                       # 按时租车
    DAILY = 'daily'                         # 按天租车

    CHOICES = [
        (AIRPORT_PICKUP, '接机'),
        (AIRPORT_DROPOFF, '送机'),
        (CHARTER, '包车'),
        (TRANSFER, '点对点接送'),
        (HOURLY, '按时租车'),
        (DAILY, '按天租车'),
    ]


class VehicleType:
    """车型"""
    SEDAN = 'sedan'             # 轿车
    SUV = 'suv'                 # SUV
    MPV = 'mpv'                 # MPV/商务车
    VAN = 'van'                 # 面包车
    BUS = 'bus'                 # 巴士
    LUXURY = 'luxury'           # 豪华车

    CHOICES = [
        (SEDAN, '轿车'),
        (SUV, 'SUV'),
        (MPV, '商务车'),
        (VAN, '面包车'),
        (BUS, '巴士'),
        (LUXURY, '豪华车'),
    ]


class ProductsCarExt(db.Model):
    """
    用车服务产品扩展表
    存储用车类产品的特有属性
    """
    __tablename__ = 'products_car_ext'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 关联主表 ==========
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, unique=True, comment='关联产品ID')

    # ========== 服务类型 ==========
    service_type = db.Column(db.String(30),
                             comment='服务类型：airport_pickup/airport_dropoff/charter/transfer/hourly/daily')

    # ========== 车辆信息 ==========
    vehicle_type = db.Column(db.String(20), comment='车型：sedan/suv/mpv/van/bus/luxury')
    vehicle_brand = db.Column(db.String(100), comment='车辆品牌')
    vehicle_model = db.Column(db.String(100), comment='车辆型号')
    vehicle_year = db.Column(db.Integer, comment='车辆年份')
    vehicle_color = db.Column(db.String(50), comment='车辆颜色')
    license_plate = db.Column(db.String(20), comment='车牌号')
    vehicle_images = db.Column(db.Text, comment='车辆图片JSON数组')

    # ========== 容量信息 ==========
    max_passengers = db.Column(db.Integer, comment='最大乘客数')
    max_luggage = db.Column(db.Integer, comment='最大行李数')
    max_carry_on = db.Column(db.Integer, comment='最大手提行李数')

    # ========== 服务范围 ==========
    service_area = db.Column(db.String(500), comment='服务区域')
    pickup_location = db.Column(db.String(500), comment='接车地点')
    dropoff_location = db.Column(db.String(500), comment='送达地点')
    service_airports = db.Column(db.Text, comment='服务机场JSON数组')

    # ========== 价格计算方式 ==========
    pricing_type = db.Column(db.String(20), default='fixed',
                             comment='计价方式：fixed固定/distance按里程/hourly按小时/daily按天')
    base_distance = db.Column(db.Integer, comment='基础里程（公里）')
    extra_distance_price = db.Column(db.Numeric(10, 2), comment='超出里程单价')
    base_hours = db.Column(db.Integer, comment='基础时长（小时）')
    extra_hour_price = db.Column(db.Numeric(10, 2), comment='超时单价')

    # ========== 时间限制 ==========
    min_duration_hours = db.Column(db.Integer, comment='最短服务时长（小时）')
    max_duration_hours = db.Column(db.Integer, comment='最长服务时长（小时）')
    operating_hours_start = db.Column(db.Time, comment='服务开始时间')
    operating_hours_end = db.Column(db.Time, comment='服务结束时间')
    night_surcharge_start = db.Column(db.Time, comment='夜间附加费开始时间')
    night_surcharge_end = db.Column(db.Time, comment='夜间附加费结束时间')
    night_surcharge_rate = db.Column(db.Numeric(5, 2), comment='夜间附加费率（百分比）')

    # ========== 司机信息 ==========
    driver_name = db.Column(db.String(100), comment='司机姓名')
    driver_phone = db.Column(db.String(50), comment='司机电话')
    driver_language = db.Column(db.String(100), comment='司机语言能力')
    driver_rating = db.Column(db.Numeric(3, 2), comment='司机评分')

    # ========== 服务内容 ==========
    includes_water = db.Column(db.Boolean, default=False, comment='是否提供矿泉水')
    includes_wifi = db.Column(db.Boolean, default=False, comment='是否提供WiFi')
    includes_child_seat = db.Column(db.Boolean, default=False, comment='是否提供儿童座椅')
    includes_flight_tracking = db.Column(db.Boolean, default=False, comment='是否跟踪航班')
    includes_meet_greet = db.Column(db.Boolean, default=False, comment='是否举牌接机')
    waiting_time_free = db.Column(db.Integer, comment='免费等待时间（分钟）')
    extra_waiting_price = db.Column(db.Numeric(10, 2), comment='超时等待费（每小时）')

    # ========== 附加服务 ==========
    extra_services = db.Column(db.Text, comment='附加服务JSON数组')
    special_requirements = db.Column(db.Text, comment='特殊要求说明')

    # ========== 取消政策 ==========
    free_cancel_hours = db.Column(db.Integer, comment='免费取消时限（小时）')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # ========== 关联关系 ==========
    product = db.relationship('ProductsUnified', backref=db.backref('car_ext', uselist=False))

    def __repr__(self):
        return f'<ProductsCarExt {self.id}: {self.service_type}>'

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'product_id': self.product_id,
            'service_type': self.service_type,
            'vehicle_type': self.vehicle_type,
            'vehicle_brand': self.vehicle_brand,
            'vehicle_model': self.vehicle_model,
            'max_passengers': self.max_passengers,
            'max_luggage': self.max_luggage,
            'service_area': self.service_area,
            'pickup_location': self.pickup_location,
            'dropoff_location': self.dropoff_location,
            'service_airports': json.loads(self.service_airports) if self.service_airports else None,
            'pricing_type': self.pricing_type,
            'base_distance': self.base_distance,
            'extra_distance_price': float(self.extra_distance_price) if self.extra_distance_price else None,
            'base_hours': self.base_hours,
            'extra_hour_price': float(self.extra_hour_price) if self.extra_hour_price else None,
            'operating_hours_start': self.operating_hours_start.strftime('%H:%M') if self.operating_hours_start else None,
            'operating_hours_end': self.operating_hours_end.strftime('%H:%M') if self.operating_hours_end else None,
            'driver_language': self.driver_language,
            'includes_water': self.includes_water,
            'includes_wifi': self.includes_wifi,
            'includes_child_seat': self.includes_child_seat,
            'includes_flight_tracking': self.includes_flight_tracking,
            'includes_meet_greet': self.includes_meet_greet,
            'waiting_time_free': self.waiting_time_free,
            'extra_services': json.loads(self.extra_services) if self.extra_services else None,
            'free_cancel_hours': self.free_cancel_hours,
        }

    def calculate_price(self, distance=None, hours=None, is_night=False):
        """
        计算服务价格

        Args:
            distance: 行程距离（公里）
            hours: 服务时长（小时）
            is_night: 是否夜间服务

        Returns:
            计算后的价格
        """
        # 获取基础价格
        if not self.product:
            return None

        base_price = float(self.product.base_price or 0)

        # 根据计价方式计算
        if self.pricing_type == 'distance' and distance:
            # 按里程计价
            extra_distance = max(0, distance - (self.base_distance or 0))
            extra_price = extra_distance * float(self.extra_distance_price or 0)
            base_price += extra_price

        elif self.pricing_type == 'hourly' and hours:
            # 按小时计价
            extra_hours = max(0, hours - (self.base_hours or 0))
            extra_price = extra_hours * float(self.extra_hour_price or 0)
            base_price += extra_price

        # 夜间附加费
        if is_night and self.night_surcharge_rate:
            base_price *= (1 + float(self.night_surcharge_rate) / 100)

        return round(base_price, 2)
