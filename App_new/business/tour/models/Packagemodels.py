from datetime import datetime
from datetime import date
from App_new.exts import db  # 确保你已正确导入 db 对象
from sqlalchemy import Date
from flask_sqlalchemy import SQLAlchemy


class Product(db.Model):
    """旅游产品模板库（供应商提供的标准产品）"""
    __tablename__ = 'package_products'

    id = db.Column(db.Integer, primary_key=True)
    
    # 供应商关联（指向 customer_companies 表）
    supplier_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id'), nullable=True, comment='供应商公司ID')
    
    # 产品编号和名称
    product_code = db.Column(db.String(50), unique=True, nullable=True, comment='产品编号')
    product_name = db.Column(db.String(200), nullable=False, comment='产品名字')
    
    # 地理信息
    city_id = db.Column(db.Integer, db.ForeignKey('travel_products_city.id'), nullable=True, comment='城市ID')
    city_name = db.Column(db.String(100), nullable=True, comment='城市名字（冗余字段，方便查询）')
    departure_city = db.Column(db.String(100), nullable=True, comment='出发城市')
    destination_city = db.Column(db.String(100), nullable=True, comment='目的地城市')
    
    # 产品基本信息
    product_type = db.Column(db.String(50), nullable=True, comment='产品类型：跟团游/自由行/定制游/当地游')
    duration_days = db.Column(db.Integer, nullable=True, comment='行程天数')
    
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
    included_services = db.Column(db.Text, nullable=True, comment='包含服务')
    excluded_services = db.Column(db.Text, nullable=True, comment='不包含服务')
    important_notes = db.Column(db.Text, nullable=True, comment='重要提示')
    
    # 图片
    cover_image = db.Column(db.String(500), nullable=True, comment='封面图')
    gallery_images = db.Column(db.Text, nullable=True, comment='图片库（JSON数组）')
    
    # 供应商文件（PDF/Word等）
    supplier_document = db.Column(db.String(500), nullable=True, comment='供应商产品说明文件路径')
    supplier_document_name = db.Column(db.String(200), nullable=True, comment='供应商文件原始名称')
    
    # 状态管理
    product_status = db.Column(db.String(50), default='active', comment='产品状态：active/inactive/draft')
    is_featured = db.Column(db.Boolean, default=False, comment='是否精选')
    
    # 有效期
    valid_from = db.Column(Date, nullable=True, comment='有效开始日期')
    valid_until = db.Column(Date, nullable=True, comment='有效结束日期')
    created_at = db.Column(Date, default=datetime.utcnow().date, comment='创建时间')
    
    # 版本管理（可选）
    version = db.Column(db.Integer, default=1, comment='版本号')
    parent_product_id = db.Column(db.Integer, db.ForeignKey('package_products.id'), nullable=True, comment='父产品ID')
    
    # 更新时间和创建人
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    created_by = db.Column(db.String(100), nullable=True, comment='创建人')
    
    # 关联关系
    supplier = db.relationship('CustomerCompany', backref=db.backref('travel_products', lazy='dynamic'), foreign_keys=[supplier_id])
    parent_product = db.relationship('Product', remote_side=[id], backref='versions', foreign_keys=[parent_product_id])
    city = db.relationship('ProductCity', backref=db.backref('products', lazy='dynamic'), foreign_keys=[city_id])
    
    @property
    def display_company_name(self):
        """获取显示用的公司名称"""
        if self.supplier:
            return self.supplier.name
        return '未设置供应商'
    
    @property
    def country(self):
        """智能获取国家（从城市关联获取）"""
        if self.city:
            return self.city.country_name
        return '未知'

    def __init__(self, product_name: str, **kwargs):
        """初始化产品实例"""
        self.product_name = product_name
        
        # 设置可选字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @staticmethod
    def generate_product_code():
        """生成唯一的产品编号，格式：PKG-YYYYMMDD-XXXX"""
        from datetime import datetime
        import random
        import string
        
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 生成随机4位字母数字组合
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        code = f'PKG-{date_str}-{random_suffix}'
        
        # 检查是否已存在，如果存在则重新生成
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            existing = db.session.query(Product).filter_by(product_code=code).first()
            if not existing:
                return code
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code = f'PKG-{date_str}-{random_suffix}'
            attempt += 1
        
        # 如果10次都重复，使用时间戳
        timestamp = datetime.now().strftime('%H%M%S')
        return f'PKG-{date_str}-{timestamp}'

    @classmethod
    def add_product(cls, city_name: str, supplier_id: int, product_name: str, created_at: date,
                    valid_until: date, **kwargs) -> 'Product':
        """添加新产品到数据库。

        Args:
            city_name (str): 城市名称。
            supplier_id (int): 供应商ID。
            product_name (str): 产品名称。
            created_at (date): 创建时间。
            valid_until (date): 产品有效期。
            **kwargs: 其他产品属性。

        Returns:
            Product: 返回新创建的产品实例。
        """
        # 创建新产品实例
        new_product = cls(city_name=city_name, supplier_id=supplier_id,
                          product_name=product_name, created_at=created_at,
                          valid_until=valid_until, **kwargs)

        # 将新产品添加到会话
        db.session.add(new_product)

        # 提交到数据库
        db.session.commit()

        return new_product

    @staticmethod
    def product_exists(product_name: str, supplier_id: int = None):
        """检查产品是否存在"""
        query = db.session.query(Product).filter_by(product_name=product_name)
        if supplier_id:
            query = query.filter_by(supplier_id=supplier_id)
        return query.first() is not None

    def to_dict(self):
        """将产品转换为字典格式"""
        import json
        
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.display_company_name,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'company_name': self.display_company_name,
            'country': self.country,
            'city_id': self.city_id,
            'city_name': self.city_name,
            'departure_city': self.departure_city,
            'destination_city': self.destination_city,
            'product_type': self.product_type,
            'duration_days': self.duration_days,
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
            'included_services': self.included_services,
            'excluded_services': self.excluded_services,
            'important_notes': self.important_notes,
            'cover_image': self.cover_image,
            'gallery_images': json.loads(self.gallery_images) if self.gallery_images else [],
            'supplier_document': self.supplier_document,
            'supplier_document_name': self.supplier_document_name,
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
    __tablename__ = 'package_itinerary'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('package_products.id'), nullable=False, comment='产品ID')
    day_number = db.Column(db.Integer, nullable=False, comment='第几天')
    day_title = db.Column(db.String(200), nullable=True, comment='当日标题')
    content = db.Column(db.Text, nullable=True, comment='行程正文内容')
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
            'content': self.content,
            'image1': self.image1,
            'image2': self.image2,
            'image3': self.image3,
            'images': self.images,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


# 新增：产品价格变体表
class ProductPriceVariant(db.Model):
    """产品价格变体模型（支持表格式价格：不同房型、不同人数）"""
    __tablename__ = 'package_price_variant'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('package_products.id'), nullable=False, comment='产品ID')
    variant_name = db.Column(db.String(100), nullable=False, comment='变体名称(如Promo/Extension Night)')
    start_date = db.Column(db.Date, nullable=True, comment='开始日期')
    end_date = db.Column(db.Date, nullable=True, comment='结束日期')
    min_pax = db.Column(db.Integer, nullable=True, comment='最少人数')
    max_pax = db.Column(db.Integer, nullable=True, comment='最多人数')
    
    # 房型价格
    single_price = db.Column(db.Float, nullable=True, comment='Single单人房价格')
    twin_price = db.Column(db.Float, nullable=True, comment='Twin双人房价格')
    third_pax_price = db.Column(db.Float, nullable=True, comment='3rd Pax第三人价格')
    child_no_bed_price = db.Column(db.Float, nullable=True, comment='Child no Bed儿童不占床价格')
    
    # 兼容旧字段
    adult_price = db.Column(db.Float, nullable=True, comment='成人价格(兼容)')
    child_price = db.Column(db.Float, nullable=True, comment='儿童价格(兼容)')
    infant_price = db.Column(db.Float, nullable=True, comment='婴儿价格')
    single_room_supplement = db.Column(db.Float, nullable=True, comment='单房差')
    
    currency = db.Column(db.String(10), default='SGD', comment='货币单位')

    # 成本价格
    cost_single_price = db.Column(db.Float, nullable=True, comment='Single成本')
    cost_twin_price = db.Column(db.Float, nullable=True, comment='Twin成本')
    cost_third_pax_price = db.Column(db.Float, nullable=True, comment='3rd Pax成本')
    cost_child_no_bed_price = db.Column(db.Float, nullable=True, comment='Child no Bed成本')

    # 利润设置
    profit_per_person = db.Column(db.Float, nullable=True, comment='每人利润金额')

    is_primary = db.Column(db.Boolean, default=False, comment='是否主要价格')
    is_active = db.Column(db.Boolean, default=True, comment='是否激活')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关联关系
    product = db.relationship('Product', backref=db.backref('price_variants', lazy='dynamic'))

    def __repr__(self):
        return f'<ProductPriceVariant {self.variant_name}: {self.currency}>'

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'variant_name': self.variant_name,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'min_pax': self.min_pax,
            'max_pax': self.max_pax,
            'single_price': self.single_price,
            'twin_price': self.twin_price,
            'third_pax_price': self.third_pax_price,
            'child_no_bed_price': self.child_no_bed_price,
            'adult_price': self.adult_price,
            'child_price': self.child_price,
            'infant_price': self.infant_price,
            'single_room_supplement': self.single_room_supplement,
            'currency': self.currency,
            'cost_single_price': self.cost_single_price,
            'cost_twin_price': self.cost_twin_price,
            'cost_third_pax_price': self.cost_third_pax_price,
            'cost_child_no_bed_price': self.cost_child_no_bed_price,
            'profit_per_person': self.profit_per_person,
            'is_primary': self.is_primary,
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
    company_name = db.Column(db.String(100), nullable=False, comment='公司英文名/全称')
    company_name_cn = db.Column(db.String(100), nullable=True, comment='公司中文名')
    company_short_name = db.Column(db.String(50), nullable=True, comment='公司简称')
    company_description = db.Column(db.Text, nullable=False, comment='公司简介')
    phone = db.Column(db.String(20), nullable=False, comment='联系电话')
    email = db.Column(db.String(100), nullable=False, comment='电子邮箱')
    address = db.Column(db.Text, nullable=False, comment='公司地址')
    logo_path = db.Column(db.String(200), nullable=True, comment='Logo路径')
    stamp_path = db.Column(db.String(200), nullable=True, comment='电子章路径')
    website = db.Column(db.String(200), nullable=True, comment='公司网址')
    ta_license = db.Column(db.String(50), nullable=True, comment='TA License Number')
    uen = db.Column(db.String(20), nullable=True, comment='UEN (Unique Entity Number)')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    def __repr__(self):
        return f'<CompanyInfo {self.company_name_cn or self.company_name}>'


class HomeBanner(db.Model):
    """首页轮播图/横幅管理"""
    __tablename__ = 'home_banners'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=True, comment='图片标题')
    description = db.Column(db.String(255), nullable=True, comment='图片描述')
    image_path = db.Column(db.String(500), nullable=False, comment='图片路径')
    link_url = db.Column(db.String(500), nullable=True, comment='点击跳转链接')
    sort_order = db.Column(db.Integer, default=0, comment='排序顺序，数字越小越靠前')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    created_by = db.Column(db.String(100), nullable=True, comment='创建人')
    
    def __repr__(self):
        return f'<HomeBanner {self.id}: {self.title or "无标题"}>'
    
    @classmethod
    def get_active_banners(cls):
        """获取所有启用的轮播图，按排序顺序"""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order.asc(), cls.id.asc()).all()
    
    @classmethod
    def get_all_banners(cls):
        """获取所有轮播图（包括禁用的）"""
        return cls.query.order_by(cls.sort_order.asc(), cls.id.asc()).all()


# 图片库关联表（多对多关系）
product_images = db.Table('product_images',
    db.Column('product_id', db.Integer, db.ForeignKey('package_products.id'), primary_key=True, comment='产品ID'),
    db.Column('image_id', db.Integer, db.ForeignKey('image_library.id'), primary_key=True, comment='图片ID'),
    db.Column('image_type', db.String(20), default='gallery', comment='图片类型：cover/gallery'),
    db.Column('sort_order', db.Integer, default=0, comment='排序顺序'),
    db.Column('created_at', db.DateTime, default=datetime.utcnow, comment='关联创建时间')
)


class ImageLibrary(db.Model):
    """图片库模型 - 存储共享图片"""
    __tablename__ = 'image_library'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True, comment='图片标题/描述')
    image_path = db.Column(db.String(500), nullable=False, comment='图片路径（相对于static）')
    tags = db.Column(db.String(200), nullable=True, comment='标签（逗号分隔）')
    category = db.Column(db.String(50), nullable=True, comment='分类：tour/product/destination/other')
    file_size = db.Column(db.Integer, nullable=True, comment='文件大小（字节）')
    width = db.Column(db.Integer, nullable=True, comment='图片宽度')
    height = db.Column(db.Integer, nullable=True, comment='图片高度')
    
    # 统计信息
    usage_count = db.Column(db.Integer, default=0, comment='使用次数')
    
    # 状态
    is_active = db.Column(db.Boolean, default=True, comment='是否激活')
    
    # 元数据
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    created_by = db.Column(db.String(100), nullable=True, comment='创建人')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    products = db.relationship('Product', secondary=product_images, backref=db.backref('library_images', lazy='dynamic'))
    
    def increment_usage(self):
        """增加使用次数"""
        self.usage_count = (self.usage_count or 0) + 1
        db.session.commit()
    
    def decrement_usage(self):
        """减少使用次数"""
        self.usage_count = max(0, (self.usage_count or 0) - 1)
        db.session.commit()
    
    @property
    def full_path(self):
        """获取完整路径"""
        return f"static/{self.image_path}"
    
    @classmethod
    def get_active_images(cls):
        """获取激活的图片"""
        return cls.query.filter_by(is_active=True).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def search_by_tags(cls, tags):
        """根据标签搜索"""
        tag_list = [tag.strip() for tag in tags.split(',')]
        query = cls.query.filter_by(is_active=True)
        for tag in tag_list:
            query = query.filter(cls.tags.contains(tag))
        return query.all()
    
    @classmethod
    def get_by_category(cls, category):
        """根据分类获取"""
        return cls.query.filter_by(is_active=True, category=category).order_by(cls.created_at.desc()).all()