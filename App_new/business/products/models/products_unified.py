# -*- coding: utf-8 -*-
"""
统一产品主表
所有产品类型共用的核心字段
"""

from datetime import datetime
from App_new.exts import db


class ProductCategory:
    """产品大类"""
    TOUR = 'tour'           # 旅游线路（跟团游/自由行/定制游/当地游）
    VISA = 'visa'           # 签证
    TICKET = 'ticket'       # 门票/当地玩乐
    CAR = 'car'             # 用车
    CRUISE = 'cruise'       # 邮轮
    HOTEL = 'hotel'         # 酒店
    FLIGHT = 'flight'       # 机票
    INSURANCE = 'insurance' # 保险

    CHOICES = [
        (TOUR, '旅游线路'),
        (VISA, '签证'),
        (TICKET, '门票/玩乐'),
        (CAR, '用车'),
        (CRUISE, '邮轮'),
        (HOTEL, '酒店'),
        (FLIGHT, '机票'),
        (INSURANCE, '保险'),
    ]

    @classmethod
    def get_label(cls, value):
        """获取类别中文名"""
        for code, label in cls.CHOICES:
            if code == value:
                return label
        return value


class ProductSubCategory:
    """产品子类"""
    # 旅游线路子类
    TOUR_GROUP = 'group_tour'       # 跟团游
    TOUR_FREE = 'free_tour'         # 自由行
    TOUR_CUSTOM = 'custom_tour'     # 定制游
    TOUR_LOCAL = 'local_tour'       # 当地游

    # 签证子类
    VISA_TOURIST = 'tourist_visa'   # 旅游签证
    VISA_BUSINESS = 'business_visa' # 商务签证
    VISA_STUDENT = 'student_visa'   # 学生签证

    # 门票子类
    TICKET_SCENIC = 'scenic'        # 景区门票
    TICKET_SHOW = 'show'            # 演出门票
    TICKET_ACTIVITY = 'activity'    # 活动体验

    # 用车子类
    CAR_PICKUP = 'airport_pickup'   # 接机
    CAR_DROPOFF = 'airport_dropoff' # 送机
    CAR_CHARTER = 'charter'         # 包车
    CAR_TRANSFER = 'transfer'       # 点对点接送

    # 酒店子类
    HOTEL_STANDARD = 'standard'     # 标准酒店
    HOTEL_RESORT = 'resort'         # 度假村
    HOTEL_APARTMENT = 'apartment'   # 公寓

    CHOICES = {
        ProductCategory.TOUR: [
            (TOUR_GROUP, '跟团游'),
            (TOUR_FREE, '自由行'),
            (TOUR_CUSTOM, '定制游'),
            (TOUR_LOCAL, '当地游'),
        ],
        ProductCategory.VISA: [
            (VISA_TOURIST, '旅游签证'),
            (VISA_BUSINESS, '商务签证'),
            (VISA_STUDENT, '学生签证'),
        ],
        ProductCategory.TICKET: [
            (TICKET_SCENIC, '景区门票'),
            (TICKET_SHOW, '演出门票'),
            (TICKET_ACTIVITY, '活动体验'),
        ],
        ProductCategory.CAR: [
            (CAR_PICKUP, '接机'),
            (CAR_DROPOFF, '送机'),
            (CAR_CHARTER, '包车'),
            (CAR_TRANSFER, '点对点接送'),
        ],
        ProductCategory.HOTEL: [
            (HOTEL_STANDARD, '标准酒店'),
            (HOTEL_RESORT, '度假村'),
            (HOTEL_APARTMENT, '公寓'),
        ],
    }


class ProductsUnified(db.Model):
    """
    统一产品主表
    所有产品类型（旅游/签证/门票/用车/邮轮/酒店/机票/保险）共用
    """
    __tablename__ = 'products_unified'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 基础信息 ==========
    product_code = db.Column(db.String(50), unique=True, nullable=False, comment='产品编号')
    product_name = db.Column(db.String(200), nullable=False, comment='产品名称')
    product_short_name = db.Column(db.String(100), comment='产品简称')

    # ========== 分类 ==========
    product_category = db.Column(db.String(50), nullable=False, index=True,
                                  comment='产品大类：tour/visa/ticket/car/cruise/hotel/flight/insurance')
    product_sub_category = db.Column(db.String(50), index=True, comment='产品子类')

    # ========== 销售信息 ==========
    sale_type = db.Column(db.String(20), default='service',
                          comment='销售类型：physical实体/electronic电子/service服务')
    product_status = db.Column(db.String(20), default='draft', index=True,
                               comment='状态：draft草稿/active上架/inactive下架')
    is_hot = db.Column(db.Boolean, default=False, index=True, comment='是否热卖')
    is_featured = db.Column(db.Boolean, default=False, index=True, comment='是否推荐')
    is_new = db.Column(db.Boolean, default=False, comment='是否新品')
    sort_order = db.Column(db.Integer, default=0, comment='排序权重')
    tags = db.Column(db.Text, comment='标签JSON数组')

    # ========== 供应商 ==========
    supplier_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id'), index=True, comment='供应商公司ID')

    # ========== 地理位置 ==========
    country = db.Column(db.String(100), index=True, comment='国家')
    city = db.Column(db.String(100), index=True, comment='城市')
    departure_city = db.Column(db.String(100), comment='出发城市（旅游/邮轮）')
    destination = db.Column(db.String(200), comment='目的地')

    # ========== 基础定价 ==========
    base_price = db.Column(db.Numeric(12, 2), comment='基础售价')
    cost_price = db.Column(db.Numeric(12, 2), comment='成本价')
    original_price = db.Column(db.Numeric(12, 2), comment='原价（划线价）')
    currency = db.Column(db.String(10), default='SGD', comment='币种')

    # ========== 图片资源 ==========
    cover_image = db.Column(db.String(500), comment='封面图路径')
    gallery_images = db.Column(db.Text, comment='图片库JSON数组')
    video_url = db.Column(db.String(500), comment='视频链接')

    # ========== 描述信息 ==========
    short_description = db.Column(db.String(500), comment='简短描述')
    description = db.Column(db.Text, comment='产品详细描述')
    highlights = db.Column(db.Text, comment='产品亮点')
    includes = db.Column(db.Text, comment='费用包含')
    excludes = db.Column(db.Text, comment='费用不含')
    important_notes = db.Column(db.Text, comment='重要提示')

    # ========== 有效期 ==========
    valid_from = db.Column(db.Date, comment='有效开始日期')
    valid_until = db.Column(db.Date, comment='有效结束日期')

    # ========== 扩展表关联 ==========
    # 用于关联各品类的扩展表（旅游/签证/门票/用车等）
    ext_table_id = db.Column(db.Integer, comment='扩展表记录ID')

    # ========== 统计信息 ==========
    view_count = db.Column(db.Integer, default=0, comment='浏览次数')
    sale_count = db.Column(db.Integer, default=0, comment='销售次数')
    favorite_count = db.Column(db.Integer, default=0, comment='收藏次数')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    created_by = db.Column(db.String(100), comment='创建人')
    updated_by = db.Column(db.String(100), comment='更新人')

    # ========== 关联关系 ==========
    supplier = db.relationship('CustomerCompany', backref=db.backref('unified_products', lazy='dynamic'), foreign_keys=[supplier_id])
    prices = db.relationship('ProductsPrice', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    rules = db.relationship('ProductsRule', backref='product', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ProductsUnified {self.product_code}: {self.product_name}>'

    @property
    def category_label(self):
        """获取产品大类中文名"""
        return ProductCategory.get_label(self.product_category)

    @property
    def is_valid(self):
        """检查产品是否在有效期内"""
        today = datetime.now().date()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        return True

    @property
    def display_price(self):
        """获取显示价格（优先使用促销价）"""
        # 查找当前有效的促销价格
        promo_price = self.prices.filter_by(
            price_type='promo',
            is_active=True
        ).first()

        if promo_price and promo_price.is_valid:
            return promo_price.selling_price

        return self.base_price

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'product_short_name': self.product_short_name,
            'product_category': self.product_category,
            'category_label': self.category_label,
            'product_sub_category': self.product_sub_category,
            'product_status': self.product_status,
            'is_hot': self.is_hot,
            'is_featured': self.is_featured,
            'supplier_id': self.supplier_id,
            'country': self.country,
            'city': self.city,
            'base_price': float(self.base_price) if self.base_price else None,
            'currency': self.currency,
            'cover_image': self.cover_image,
            'short_description': self.short_description,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'view_count': self.view_count,
            'sale_count': self.sale_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def to_detail_dict(self):
        """转换为详细字典（包含完整信息）"""
        data = self.to_dict()
        data.update({
            'cost_price': float(self.cost_price) if self.cost_price else None,
            'original_price': float(self.original_price) if self.original_price else None,
            'departure_city': self.departure_city,
            'destination': self.destination,
            'gallery_images': self.gallery_images,
            'video_url': self.video_url,
            'description': self.description,
            'highlights': self.highlights,
            'includes': self.includes,
            'excludes': self.excludes,
            'important_notes': self.important_notes,
            'tags': self.tags,
            'ext_table_id': self.ext_table_id,
        })
        return data

    @classmethod
    def generate_product_code(cls, category, prefix=None):
        """
        生成产品编号

        格式：前缀-年月-序号
        例如：TOU-2601-001, VIS-2601-002

        使用 business_types 表中的 product_code_prefix 字段
        """
        from App_new.shared.models.business_types import generate_product_code as gen_code

        # 将产品类别映射到业务类型代码
        category_to_business_type = {
            ProductCategory.TOUR: 'tour',
            ProductCategory.VISA: 'visa',
            ProductCategory.TICKET: 'ticket',
            ProductCategory.CAR: 'car',
            ProductCategory.CRUISE: 'cruise',
            ProductCategory.HOTEL: 'hotel',
            ProductCategory.FLIGHT: 'flight',
            ProductCategory.INSURANCE: 'insurance',
        }

        business_type_code = category_to_business_type.get(category, 'other')

        return gen_code(business_type_code, table_model=cls)
