# -*- coding: utf-8 -*-
"""
邮轮产品扩展表
存储邮轮特有的属性
"""

from datetime import datetime
from App_new.exts import db


class CabinType:
    """舱型"""
    INSIDE = 'inside'           # 内舱
    OCEAN_VIEW = 'ocean_view'   # 海景舱
    BALCONY = 'balcony'         # 阳台舱
    SUITE = 'suite'             # 套房
    MINI_SUITE = 'mini_suite'   # 迷你套房

    CHOICES = [
        (INSIDE, '内舱'),
        (OCEAN_VIEW, '海景舱'),
        (BALCONY, '阳台舱'),
        (SUITE, '套房'),
        (MINI_SUITE, '迷你套房'),
    ]


class ProductsCruiseExt(db.Model):
    """
    邮轮产品扩展表
    存储邮轮类产品的特有属性
    """
    __tablename__ = 'products_cruise_ext'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 关联主表 ==========
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, unique=True, comment='关联产品ID')

    # ========== 邮轮公司信息 ==========
    cruise_company = db.Column(db.String(100), comment='邮轮公司')
    cruise_brand = db.Column(db.String(100), comment='邮轮品牌')
    ship_name = db.Column(db.String(100), comment='船名')
    ship_name_en = db.Column(db.String(100), comment='船名英文')
    ship_tonnage = db.Column(db.Integer, comment='吨位')
    ship_length = db.Column(db.Numeric(8, 2), comment='船长（米）')
    ship_year = db.Column(db.Integer, comment='建造年份')
    ship_refurbished_year = db.Column(db.Integer, comment='翻新年份')
    total_cabins = db.Column(db.Integer, comment='总舱房数')
    total_passengers = db.Column(db.Integer, comment='最大载客量')
    total_crew = db.Column(db.Integer, comment='船员数量')
    ship_rating = db.Column(db.Numeric(3, 2), comment='邮轮评分')

    # ========== 航线信息 ==========
    route_name = db.Column(db.String(200), comment='航线名称')
    departure_port = db.Column(db.String(100), comment='登船港口')
    departure_port_en = db.Column(db.String(100), comment='登船港口英文')
    arrival_port = db.Column(db.String(100), comment='下船港口')
    arrival_port_en = db.Column(db.String(100), comment='下船港口英文')
    ports_of_call = db.Column(db.Text, comment='停靠港口JSON数组')
    route_description = db.Column(db.Text, comment='航线描述')
    route_map_url = db.Column(db.String(500), comment='航线图URL')

    # ========== 行程信息 ==========
    cruise_nights = db.Column(db.Integer, comment='航行晚数')
    cruise_days = db.Column(db.Integer, comment='航行天数')
    departure_date = db.Column(db.Date, comment='出发日期')
    departure_time = db.Column(db.Time, comment='出发时间')
    arrival_date = db.Column(db.Date, comment='到达日期')
    arrival_time = db.Column(db.Time, comment='到达时间')
    itinerary = db.Column(db.Text, comment='详细行程JSON')

    # ========== 舱位信息 ==========
    cabin_type = db.Column(db.String(30), comment='舱型：inside/ocean_view/balcony/suite/mini_suite')
    cabin_category = db.Column(db.String(50), comment='舱位等级')
    cabin_name = db.Column(db.String(100), comment='舱位名称')
    deck_number = db.Column(db.String(20), comment='甲板层数')
    cabin_size = db.Column(db.Numeric(8, 2), comment='舱房面积（平方米）')
    balcony_size = db.Column(db.Numeric(8, 2), comment='阳台面积（平方米）')
    max_occupancy = db.Column(db.Integer, comment='最大入住人数')
    bed_configuration = db.Column(db.String(200), comment='床型配置')
    cabin_amenities = db.Column(db.Text, comment='舱房设施JSON')
    cabin_images = db.Column(db.Text, comment='舱房图片JSON数组')

    # ========== 餐饮信息 ==========
    meal_plan = db.Column(db.String(100), comment='餐饮安排')
    dining_venues = db.Column(db.Text, comment='餐厅信息JSON')
    special_dining = db.Column(db.Text, comment='特色餐厅JSON')
    drinks_package = db.Column(db.String(100), comment='饮品套餐')

    # ========== 娱乐设施 ==========
    entertainment = db.Column(db.Text, comment='娱乐设施JSON')
    spa_wellness = db.Column(db.Text, comment='水疗健身JSON')
    kids_facilities = db.Column(db.Text, comment='儿童设施JSON')
    pools = db.Column(db.Text, comment='泳池信息JSON')
    casino = db.Column(db.Boolean, default=False, comment='是否有赌场')
    theater = db.Column(db.Boolean, default=False, comment='是否有剧院')

    # ========== 岸上观光 ==========
    shore_excursions = db.Column(db.Text, comment='岸上观光JSON')

    # ========== 费用说明 ==========
    port_fees = db.Column(db.Numeric(10, 2), comment='港口费')
    gratuities = db.Column(db.Numeric(10, 2), comment='小费')
    includes = db.Column(db.Text, comment='费用包含')
    excludes = db.Column(db.Text, comment='费用不含')

    # ========== 预订须知 ==========
    booking_notes = db.Column(db.Text, comment='预订须知')
    cancellation_policy = db.Column(db.Text, comment='取消政策')
    dress_code = db.Column(db.Text, comment='着装要求')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # ========== 关联关系 ==========
    product = db.relationship('ProductsUnified', backref=db.backref('cruise_ext', uselist=False))

    def __repr__(self):
        return f'<ProductsCruiseExt {self.id}: {self.ship_name}>'

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'product_id': self.product_id,
            'cruise_company': self.cruise_company,
            'cruise_brand': self.cruise_brand,
            'ship_name': self.ship_name,
            'ship_name_en': self.ship_name_en,
            'ship_tonnage': self.ship_tonnage,
            'ship_rating': float(self.ship_rating) if self.ship_rating else None,
            'route_name': self.route_name,
            'departure_port': self.departure_port,
            'arrival_port': self.arrival_port,
            'ports_of_call': json.loads(self.ports_of_call) if self.ports_of_call else None,
            'cruise_nights': self.cruise_nights,
            'cruise_days': self.cruise_days,
            'departure_date': self.departure_date.isoformat() if self.departure_date else None,
            'cabin_type': self.cabin_type,
            'cabin_category': self.cabin_category,
            'cabin_name': self.cabin_name,
            'deck_number': self.deck_number,
            'cabin_size': float(self.cabin_size) if self.cabin_size else None,
            'max_occupancy': self.max_occupancy,
            'meal_plan': self.meal_plan,
            'entertainment': json.loads(self.entertainment) if self.entertainment else None,
            'shore_excursions': json.loads(self.shore_excursions) if self.shore_excursions else None,
            'port_fees': float(self.port_fees) if self.port_fees else None,
            'gratuities': float(self.gratuities) if self.gratuities else None,
        }
