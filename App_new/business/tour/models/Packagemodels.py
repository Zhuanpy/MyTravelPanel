from datetime import datetime
from datetime import date
from App_new.exts import db  # 确保你已正确导入 db 对象
from sqlalchemy import Date
from flask_sqlalchemy import SQLAlchemy


class Product(db.Model):

    __tablename__ = 'travelproducts'  # 可选：定义表名

    id = db.Column(db.Integer, primary_key=True)  # 主键
    city_name = db.Column(db.String(100), nullable=False)  # 新增城市名字
    company_name = db.Column(db.String(100), nullable=False)  # 公司名字
    product_name = db.Column(db.String(100), nullable=False)  # 产品名字
    created_at = db.Column(Date, default=datetime.utcnow().date)  # 创建时间，默认当前时间
    valid_until = db.Column(Date)  # 有效期
    
    # 旅游产品基本信息
    product_type = db.Column(db.String(50), nullable=True, comment='产品类型：跟团游/自由行/定制游')
    duration_days = db.Column(db.Integer, nullable=True, comment='行程天数')
    departure_city = db.Column(db.String(100), nullable=True, comment='出发城市')
    destination_city = db.Column(db.String(100), nullable=True, comment='目的地城市')
    min_pax = db.Column(db.Integer, nullable=True, comment='最少成团人数')
    max_pax = db.Column(db.Integer, nullable=True, comment='最大成团人数')
    suitable_season = db.Column(db.String(200), nullable=True, comment='适合季节')
    difficulty_level = db.Column(db.String(50), nullable=True, comment='难度等级：简单/中等/困难')
    product_status = db.Column(db.String(50), default='active', comment='产品状态：active/inactive/draft')
    
    # 价格预算信息
    base_price = db.Column(db.Float, nullable=True, comment='基础价格')
    single_room_supplement = db.Column(db.Float, nullable=True, comment='单房差')
    child_price = db.Column(db.Float, nullable=True, comment='儿童价格')
    infant_price = db.Column(db.Float, nullable=True, comment='婴儿价格')
    currency = db.Column(db.String(10), default='SGD', comment='货币单位')
    
    # 详细描述
    product_description = db.Column(db.Text, nullable=True, comment='产品描述')
    highlights = db.Column(db.Text, nullable=True, comment='产品亮点')
    included_services = db.Column(db.Text, nullable=True, comment='包含服务')
    excluded_services = db.Column(db.Text, nullable=True, comment='不包含服务')
    important_notes = db.Column(db.Text, nullable=True, comment='重要提示')
    
    # 联系信息
    contact_person = db.Column(db.String(100), nullable=True, comment='联系人')
    contact_phone = db.Column(db.String(50), nullable=True, comment='联系电话')
    contact_email = db.Column(db.String(100), nullable=True, comment='联系邮箱')
    
    # 更新时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    def __init__(self, city_name: str, company_name: str, product_name: str, created_at: date, valid_until: date,
                 product_type=None, duration_days=None, departure_city=None, destination_city=None,
                 min_pax=None, max_pax=None, suitable_season=None, difficulty_level=None,
                 base_price=None, single_room_supplement=None, child_price=None, infant_price=None,
                 product_description=None, highlights=None, included_services=None, excluded_services=None,
                 important_notes=None, contact_person=None, contact_phone=None, contact_email=None):
        self.id = None  # id由数据库自动生成
        self.city_name = city_name
        self.company_name = company_name
        self.product_name = product_name
        self.created_at = created_at
        self.valid_until = valid_until
        self.product_type = product_type
        self.duration_days = duration_days
        self.departure_city = departure_city
        self.destination_city = destination_city
        self.min_pax = min_pax
        self.max_pax = max_pax
        self.suitable_season = suitable_season
        self.difficulty_level = difficulty_level
        self.base_price = base_price
        self.single_room_supplement = single_room_supplement
        self.child_price = child_price
        self.infant_price = infant_price
        self.product_description = product_description
        self.highlights = highlights
        self.included_services = included_services
        self.excluded_services = excluded_services
        self.important_notes = important_notes
        self.contact_person = contact_person
        self.contact_phone = contact_phone
        self.contact_email = contact_email

    @classmethod
    def add_product(cls, city_name: str, company_name: str, product_name: str, created_at: date,
                    valid_until: date, **kwargs) -> 'Product':
        """添加新产品到数据库。

        Args:
            city_name (str): 城市名称。
            company_name (str): 公司名称。
            product_name (str): 产品名称。
            created_at (date): 创建时间。
            valid_until (date): 产品有效期。
            **kwargs: 其他产品属性。

        Returns:
            Product: 返回新创建的产品实例。
        """
        # 创建新产品实例
        new_product = cls(city_name=city_name, company_name=company_name,
                          product_name=product_name, created_at=created_at,
                          valid_until=valid_until, **kwargs)

        # 将新产品添加到会话
        db.session.add(new_product)

        # 提交到数据库
        db.session.commit()

        return new_product

    @staticmethod
    def product_exists(city_name: str, company_name: str, product_name: str):
        # 查询数据库以检查产品是否存在
        return db.session.query(Product).filter_by(
            city_name=city_name,
            company_name=company_name,
            product_name=product_name
        ).first() is not None

    def to_dict(self):
        """将产品转换为字典格式"""
        return {
            'id': self.id,
            'city_name': self.city_name,
            'company_name': self.company_name,
            'product_name': self.product_name,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'valid_until': self.valid_until.strftime('%Y-%m-%d') if self.valid_until else None,
            'product_type': self.product_type,
            'duration_days': self.duration_days,
            'departure_city': self.departure_city,
            'destination_city': self.destination_city,
            'min_pax': self.min_pax,
            'max_pax': self.max_pax,
            'suitable_season': self.suitable_season,
            'difficulty_level': self.difficulty_level,
            'base_price': self.base_price,
            'single_room_supplement': self.single_room_supplement,
            'child_price': self.child_price,
            'infant_price': self.infant_price,
            'currency': self.currency,
            'product_description': self.product_description,
            'highlights': self.highlights,
            'included_services': self.included_services,
            'excluded_services': self.excluded_services,
            'important_notes': self.important_notes,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'product_status': self.product_status,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


# 新增：产品行程详情表
class ProductItinerary(db.Model):
    """产品行程详情模型"""
    __tablename__ = 'product_itinerary'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('travelproducts.id'), nullable=False, comment='产品ID')
    day_number = db.Column(db.Integer, nullable=False, comment='第几天')
    day_title = db.Column(db.String(200), nullable=False, comment='日期标题')
    morning_activity = db.Column(db.Text, nullable=True, comment='上午活动')
    afternoon_activity = db.Column(db.Text, nullable=True, comment='下午活动')
    evening_activity = db.Column(db.Text, nullable=True, comment='晚上活动')
    meals = db.Column(db.String(200), nullable=True, comment='用餐安排')
    accommodation = db.Column(db.String(200), nullable=True, comment='住宿安排')
    transport = db.Column(db.String(200), nullable=True, comment='交通安排')
    highlights = db.Column(db.Text, nullable=True, comment='当日亮点')
    notes = db.Column(db.Text, nullable=True, comment='注意事项')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关联关系
    product = db.relationship('Product', backref=db.backref('itineraries', lazy='dynamic', order_by='ProductItinerary.day_number'))

    def __repr__(self):
        return f'<ProductItinerary Day {self.day_number}: {self.day_title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'day_number': self.day_number,
            'day_title': self.day_title,
            'morning_activity': self.morning_activity,
            'afternoon_activity': self.afternoon_activity,
            'evening_activity': self.evening_activity,
            'meals': self.meals,
            'accommodation': self.accommodation,
            'transport': self.transport,
            'highlights': self.highlights,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


# 新增：产品价格变体表
class ProductPriceVariant(db.Model):
    """产品价格变体模型（不同日期、不同人数的价格）"""
    __tablename__ = 'product_price_variant'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('travelproducts.id'), nullable=False, comment='产品ID')
    variant_name = db.Column(db.String(100), nullable=False, comment='变体名称')
    start_date = db.Column(db.Date, nullable=True, comment='开始日期')
    end_date = db.Column(db.Date, nullable=True, comment='结束日期')
    min_pax = db.Column(db.Integer, nullable=True, comment='最少人数')
    max_pax = db.Column(db.Integer, nullable=True, comment='最多人数')
    adult_price = db.Column(db.Float, nullable=False, comment='成人价格')
    child_price = db.Column(db.Float, nullable=True, comment='儿童价格')
    infant_price = db.Column(db.Float, nullable=True, comment='婴儿价格')
    single_room_supplement = db.Column(db.Float, nullable=True, comment='单房差')
    currency = db.Column(db.String(10), default='SGD', comment='货币单位')
    is_active = db.Column(db.Boolean, default=True, comment='是否激活')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关联关系
    product = db.relationship('Product', backref=db.backref('price_variants', lazy='dynamic'))

    def __repr__(self):
        return f'<ProductPriceVariant {self.variant_name}: {self.adult_price} {self.currency}>'

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'variant_name': self.variant_name,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'min_pax': self.min_pax,
            'max_pax': self.max_pax,
            'adult_price': self.adult_price,
            'child_price': self.child_price,
            'infant_price': self.infant_price,
            'single_room_supplement': self.single_room_supplement,
            'currency': self.currency,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class ProductCity(db.Model):

    __tablename__ = 'travel_products_city'  # 可选：定义表名
    id = db.Column(db.Integer, primary_key=True)  # 主键
    country_name = db.Column(db.String(100))  # 新增国家名字
    city_name = db.Column(db.String(100))  # 新增城市名字
    display_name = db.Column(db.String(100))  # 显示名字

    @classmethod
    def get_country_name_by_city(cls, city_name):
        """
        通过城市名获取第一个匹配的国家名
        :param city_name: 城市名称
        :return: 匹配的国家名称，如果找不到返回 None
        """
        result = cls.query.filter_by(city_name=city_name).first()
        if result:
            return result.country_name

        return None


class TourProduct(db.Model):
    __tablename__ = 'tour_products'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    itinerary = db.Column(db.Text, nullable=False)
    included = db.Column(db.Text, nullable=False)
    not_included = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(50))  # 例如: "3天2晚"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TourProduct {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'itinerary': self.itinerary,
            'included': self.included,
            'not_included': self.not_included,
            'price': self.price,
            'duration': self.duration,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class CompanyInfo(db.Model):
    __tablename__ = 'company_info'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    company_description = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    logo_path = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CompanyInfo {self.company_name}>'