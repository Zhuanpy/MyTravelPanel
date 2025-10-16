from datetime import datetime
from datetime import date
from App_new.exts import db  # 确保你已正确导入 db 对象
from sqlalchemy import Date
from flask_sqlalchemy import SQLAlchemy


class Product(db.Model):
    """旅游产品模板库（供应商提供的标准产品）"""
    __tablename__ = 'travelproducts'

    id = db.Column(db.Integer, primary_key=True)
    
    # 供应商关联
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=True, comment='供应商ID')
    
    # 产品编号和名称
    product_code = db.Column(db.String(50), unique=True, nullable=True, comment='产品编号')
    product_name = db.Column(db.String(200), nullable=False, comment='产品名字')
    company_name = db.Column(db.String(100), nullable=True, comment='公司名字（兼容旧数据）')
    
    # 地理信息
    country = db.Column(db.String(100), nullable=True, comment='国家')
    city_name = db.Column(db.String(100), nullable=True, comment='城市名字')
    departure_city = db.Column(db.String(100), nullable=True, comment='出发城市')
    destination_city = db.Column(db.String(100), nullable=True, comment='目的地城市')
    
    # 产品基本信息
    product_type = db.Column(db.String(50), nullable=True, comment='产品类型：跟团游/自由行/定制游/当地游')
    duration_days = db.Column(db.Integer, nullable=True, comment='行程天数')
    duration_nights = db.Column(db.Integer, nullable=True, comment='住宿晚数')
    
    # 人数限制
    min_pax = db.Column(db.Integer, default=1, comment='最少成团人数')
    max_pax = db.Column(db.Integer, nullable=True, comment='最大成团人数')
    
    # 适用条件
    suitable_season = db.Column(db.String(200), nullable=True, comment='适合季节')
    difficulty_level = db.Column(db.String(50), nullable=True, comment='难度等级：简单/中等/困难')
    tags = db.Column(db.Text, nullable=True, comment='标签（JSON格式）：蜜月/亲子/豪华/经济')
    
    # 价格信息（参考价）
    base_price = db.Column(db.Float, nullable=True, comment='基础价格（成人）')
    child_price = db.Column(db.Float, nullable=True, comment='儿童价格')
    infant_price = db.Column(db.Float, nullable=True, comment='婴儿价格')
    single_room_supplement = db.Column(db.Float, nullable=True, comment='单房差')
    currency = db.Column(db.String(10), default='SGD', comment='货币单位')
    
    # 详细描述
    product_description = db.Column(db.Text, nullable=True, comment='产品描述')
    highlights = db.Column(db.Text, nullable=True, comment='产品亮点')
    included_services = db.Column(db.Text, nullable=True, comment='包含服务')
    excluded_services = db.Column(db.Text, nullable=True, comment='不包含服务')
    important_notes = db.Column(db.Text, nullable=True, comment='重要提示')
    
    # 图片
    cover_image = db.Column(db.String(500), nullable=True, comment='封面图')
    gallery_images = db.Column(db.Text, nullable=True, comment='图片库（JSON数组）')
    
    # 联系信息
    contact_person = db.Column(db.String(100), nullable=True, comment='联系人')
    contact_phone = db.Column(db.String(50), nullable=True, comment='联系电话')
    contact_email = db.Column(db.String(100), nullable=True, comment='联系邮箱')
    
    # 状态管理
    product_status = db.Column(db.String(50), default='active', comment='产品状态：active/inactive/draft')
    is_featured = db.Column(db.Boolean, default=False, comment='是否精选')
    
    # 有效期
    valid_from = db.Column(Date, nullable=True, comment='有效开始日期')
    valid_until = db.Column(Date, nullable=True, comment='有效结束日期')
    created_at = db.Column(Date, default=datetime.utcnow().date, comment='创建时间')
    
    # 版本管理（可选）
    version = db.Column(db.Integer, default=1, comment='版本号')
    parent_product_id = db.Column(db.Integer, db.ForeignKey('travelproducts.id'), nullable=True, comment='父产品ID')
    
    # 更新时间和创建人
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    created_by = db.Column(db.String(100), nullable=True, comment='创建人')
    
    # 关联关系
    supplier = db.relationship('Supplier', backref=db.backref('travel_products', lazy='dynamic'), foreign_keys=[supplier_id])
    parent_product = db.relationship('Product', remote_side=[id], backref='versions', foreign_keys=[parent_product_id])

    def __init__(self, product_name: str, **kwargs):
        """初始化产品实例"""
        self.product_name = product_name
        
        # 设置可选字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

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
        import json
        
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else self.company_name,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'company_name': self.company_name,
            'country': self.country,
            'city_name': self.city_name,
            'departure_city': self.departure_city,
            'destination_city': self.destination_city,
            'product_type': self.product_type,
            'duration_days': self.duration_days,
            'duration_nights': self.duration_nights,
            'min_pax': self.min_pax,
            'max_pax': self.max_pax,
            'suitable_season': self.suitable_season,
            'difficulty_level': self.difficulty_level,
            'tags': json.loads(self.tags) if self.tags else [],
            'base_price': self.base_price,
            'child_price': self.child_price,
            'infant_price': self.infant_price,
            'single_room_supplement': self.single_room_supplement,
            'currency': self.currency,
            'product_description': self.product_description,
            'highlights': self.highlights,
            'included_services': self.included_services,
            'excluded_services': self.excluded_services,
            'important_notes': self.important_notes,
            'cover_image': self.cover_image,
            'gallery_images': json.loads(self.gallery_images) if self.gallery_images else [],
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'product_status': self.product_status,
            'is_featured': self.is_featured,
            'valid_from': self.valid_from.strftime('%Y-%m-%d') if self.valid_from else None,
            'valid_until': self.valid_until.strftime('%Y-%m-%d') if self.valid_until else None,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'version': self.version,
            'parent_product_id': self.parent_product_id,
            'created_by': self.created_by,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


# 新增：产品行程详情表（参考 tour_itinerary）
class ProductItinerary(db.Model):
    """产品行程详情模型（参考 tour_itinerary，支持图片上传）"""
    __tablename__ = 'product_itinerary'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('travelproducts.id'), nullable=False, comment='产品ID')
    day_number = db.Column(db.Integer, nullable=False, comment='第几天')
    day_title = db.Column(db.Text, nullable=False, comment='行程安排')
    image1 = db.Column(db.String(500), nullable=True, comment='图片1路径')
    image2 = db.Column(db.String(500), nullable=True, comment='图片2路径')
    image3 = db.Column(db.String(500), nullable=True, comment='图片3路径')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关联关系
    product = db.relationship('Product', backref=db.backref('itineraries', lazy='dynamic', order_by='ProductItinerary.day_number'))

    def __repr__(self):
        return f'<ProductItinerary Day {self.day_number}>'
    
    @property
    def images(self):
        """获取所有图片路径列表"""
        images = []
        if self.image1:
            images.append(self.image1)
        if self.image2:
            images.append(self.image2)
        if self.image3:
            images.append(self.image3)
        return images
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'day_number': self.day_number,
            'day_title': self.day_title,
            'image1': self.image1,
            'image2': self.image2,
            'image3': self.image3,
            'images': self.images,
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
    country = db.Column(db.String(100), nullable=True, comment='国家')
    city = db.Column(db.String(100), nullable=True, comment='城市')
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
            'country': self.country,
            'city': self.city,
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