"""
业务类型模型 - 新架构版本
支持不同业务模块的相互引用和扩展
"""

from ...exts import db
from datetime import datetime
from sqlalchemy.dialects.mysql import TEXT

class BusinessType(db.Model):
    """业务类型主表"""
    __tablename__ = 'business_types'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, comment='业务类型代码')
    name = db.Column(db.String(100), nullable=False, comment='业务类型名称')
    name_en = db.Column(db.String(100), comment='英文名称')
    product_code_prefix = db.Column(db.String(5), comment='产品编号前缀（3位英文大写）')
    description = db.Column(db.Text, comment='描述')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<BusinessType {self.code}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'name_en': self.name_en,
            'product_code_prefix': self.product_code_prefix,
            'description': self.description,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_product_code_prefix(cls, code):
        """获取业务类型的产品编号前缀"""
        bt = cls.query.filter_by(code=code, is_active=True).first()
        if bt and bt.product_code_prefix:
            return bt.product_code_prefix
        # 返回默认前缀映射
        default_prefixes = {
            'tour': 'TOU',
            'tour_package': 'TOU',
            'land_tour': 'TOU',
            'visa': 'VIS',
            'ticket': 'TKT',
            'attraction': 'TKT',
            'car': 'CAR',
            'transfer': 'CAR',
            'cruise': 'CRU',
            'ferry': 'CRU',
            'hotel': 'HTL',
            'flight': 'FLT',
            'insurance': 'INS',
            'rail_coach': 'TRN',
            'transport': 'TRP',
            'voucher': 'VOU',
            'service_fee': 'SVC',
            'other': 'OTH',
        }
        return default_prefixes.get(code, 'PRD')
    
    @classmethod
    def init_default_types(cls):
        """初始化默认业务类型"""
        from ...exts import db
        
        default_types = [
            {'code': 'flight', 'name': '机票', 'name_en': 'Flight', 'product_code_prefix': 'FLT', 'description': '航空机票服务', 'sort_order': 1},
            {'code': 'hotel', 'name': '酒店', 'name_en': 'Hotel', 'product_code_prefix': 'HTL', 'description': '酒店预订服务', 'sort_order': 2},
            {'code': 'visa', 'name': '签证', 'name_en': 'Visa', 'product_code_prefix': 'VIS', 'description': '签证申请服务', 'sort_order': 3},
            {'code': 'tour', 'name': '旅游团', 'name_en': 'Tour', 'product_code_prefix': 'TOU', 'description': '旅游团服务', 'sort_order': 4},
            {'code': 'insurance', 'name': '保险', 'name_en': 'Insurance', 'product_code_prefix': 'INS', 'description': '旅游保险服务', 'sort_order': 5},
            {'code': 'transport', 'name': '交通', 'name_en': 'Transport', 'product_code_prefix': 'TRP', 'description': '交通服务', 'sort_order': 6},
            {'code': 'attraction', 'name': '景点/活动', 'name_en': 'Attraction', 'product_code_prefix': 'ATR', 'description': '景点门票和活动', 'sort_order': 7},
            {'code': 'car', 'name': '租车', 'name_en': 'Car Rental', 'product_code_prefix': 'CAR', 'description': '汽车租赁服务', 'sort_order': 8},
            {'code': 'cruise', 'name': '邮轮', 'name_en': 'Cruise', 'product_code_prefix': 'CRU', 'description': '邮轮旅游服务', 'sort_order': 9},
            {'code': 'ferry', 'name': '渡轮', 'name_en': 'Ferry', 'product_code_prefix': 'FRY', 'description': '渡轮服务', 'sort_order': 10},
            {'code': 'land_tour', 'name': '地接', 'name_en': 'Land Tour', 'product_code_prefix': 'LND', 'description': '地接服务', 'sort_order': 11},
            {'code': 'rail_coach', 'name': '火车/大巴', 'name_en': 'Rail/Coach', 'product_code_prefix': 'TRN', 'description': '铁路和公路交通', 'sort_order': 12},
            {'code': 'service_fee', 'name': '服务费', 'name_en': 'Service Fee', 'product_code_prefix': 'SVC', 'description': '各种服务费用', 'sort_order': 13},
            {'code': 'ticket', 'name': '门票', 'name_en': 'Ticket', 'product_code_prefix': 'TKT', 'description': '各种门票服务', 'sort_order': 14},
            {'code': 'transfer', 'name': '接送', 'name_en': 'Transfer', 'product_code_prefix': 'TRF', 'description': '接送服务', 'sort_order': 15},
            {'code': 'tour_package', 'name': '旅游套餐', 'name_en': 'Tour Package', 'product_code_prefix': 'PKG', 'description': '旅游套餐服务', 'sort_order': 16},
            {'code': 'voucher', 'name': '代金券', 'name_en': 'Voucher', 'product_code_prefix': 'VOU', 'description': '代金券服务', 'sort_order': 17},
            {'code': 'other', 'name': '其他', 'name_en': 'Other', 'product_code_prefix': 'OTH', 'description': '其他服务', 'sort_order': 18}
        ]

        for type_info in default_types:
            if not cls.query.filter_by(code=type_info['code']).first():
                new_type = cls(**type_info)
                db.session.add(new_type)
        
        try:
            db.session.commit()
            print(f"✓ 成功初始化 {len(default_types)} 个默认业务类型")
        except Exception as e:
            db.session.rollback()
            print(f"✗ 初始化业务类型失败: {e}")
            raise e

class BusinessTypeExtension(db.Model):
    """业务类型扩展表 - 支持不同模块的特定属性"""
    __tablename__ = 'business_type_extensions'
    
    id = db.Column(db.Integer, primary_key=True)
    business_type_id = db.Column(db.Integer, db.ForeignKey('business_types.id'), nullable=False)
    module_name = db.Column(db.String(50), nullable=False, comment='模块名称：visa/flight/tour/package')
    extension_key = db.Column(db.String(100), nullable=False, comment='扩展属性键')
    extension_value = db.Column(TEXT, comment='扩展属性值')
    data_type = db.Column(db.String(20), default='string', comment='数据类型：string/number/boolean/json')
    
    # 关联关系
    business_type = db.relationship('BusinessType', backref='extensions')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class Meta:
        unique_together = ('business_type_id', 'module_name', 'extension_key')
    
    def __repr__(self):
        return f'<BusinessTypeExtension {self.module_name}.{self.extension_key}>'

class BusinessTypeRelation(db.Model):
    """业务类型关联表 - 支持不同类型间的关联关系"""
    __tablename__ = 'business_type_relations'
    
    id = db.Column(db.Integer, primary_key=True)
    source_type_id = db.Column(db.Integer, db.ForeignKey('business_types.id'), nullable=False)
    target_type_id = db.Column(db.Integer, db.ForeignKey('business_types.id'), nullable=False)
    relation_type = db.Column(db.String(50), nullable=False, comment='关联类型：compatible/required/excluded/suggested')
    strength = db.Column(db.Integer, default=1, comment='关联强度：1-10')
    description = db.Column(db.String(200), comment='关联描述')
    
    # 关联关系
    source_type = db.relationship('BusinessType', foreign_keys=[source_type_id], backref='outgoing_relations')
    target_type = db.relationship('BusinessType', foreign_keys=[target_type_id], backref='incoming_relations')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    class Meta:
        unique_together = ('source_type_id', 'target_type_id', 'relation_type')
    
    def __repr__(self):
        return f'<BusinessTypeRelation {self.source_type.code} -> {self.target_type.code}>'

# 业务类型分类常量
BUSINESS_CATEGORIES = {
    'visa': '签证服务',
    'flight': '机票服务', 
    'tour': '旅游服务',
    'package': '配套服务',
    'hotel': '酒店服务',
    'insurance': '保险服务',
    'other': '其他服务'
}

# 关联类型常量
RELATION_TYPES = {
    'compatible': '兼容',
    'required': '必需',
    'excluded': '互斥',
    'suggested': '建议',
    'alternative': '替代'
}

def get_business_types_by_category(category, include_children=True):
    """根据分类获取业务类型"""
    query = BusinessType.query.filter_by(category=category, is_active=True)
    if include_children:
        query = query.filter_by(level=1)  # 只获取主类型
    return query.order_by(BusinessType.sort_order).all()

def get_business_type_extensions(business_type_id, module_name):
    """获取业务类型在特定模块的扩展属性"""
    extensions = BusinessTypeExtension.query.filter_by(
        business_type_id=business_type_id,
        module_name=module_name
    ).all()
    
    result = {}
    for ext in extensions:
        if ext.data_type == 'json':
            try:
                import json
                result[ext.extension_key] = json.loads(ext.extension_value)
            except:
                result[ext.extension_key] = ext.extension_value
        elif ext.data_type == 'number':
            try:
                result[ext.extension_key] = float(ext.extension_value)
            except:
                result[ext.extension_key] = ext.extension_value
        elif ext.data_type == 'boolean':
            result[ext.extension_key] = ext.extension_value.lower() in ('true', '1', 'yes')
        else:
            result[ext.extension_key] = ext.extension_value
    
    return result

def create_business_type_relation(source_type_id, target_type_id, relation_type, strength=1, description=''):
    """创建业务类型关联关系"""
    relation = BusinessTypeRelation(
        source_type_id=source_type_id,
        target_type_id=target_type_id,
        relation_type=relation_type,
        strength=strength,
        description=description
    )
    db.session.add(relation)
    db.session.commit()
    return relation

def get_compatible_business_types(business_type_id, relation_type='compatible'):
    """获取兼容的业务类型"""
    relations = BusinessTypeRelation.query.filter_by(
        source_type_id=business_type_id,
        relation_type=relation_type
    ).all()
    
    return [rel.target_type for rel in relations if rel.target_type.is_active]

def get_required_business_types(business_type_id):
    """获取必需的业务类型"""
    return get_compatible_business_types(business_type_id, 'required')

def get_excluded_business_types(business_type_id):
    """获取互斥的业务类型"""
    return get_compatible_business_types(business_type_id, 'excluded')


def generate_product_code(business_type_code, table_model=None):
    """
    统一产品编号生成函数

    格式: {PREFIX}-{YYMM}-{SEQ}
    例如: TOU-2601-001

    Args:
        business_type_code: 业务类型代码 (如 'tour', 'visa')
        table_model: 可选，用于查询序号的模型类

    Returns:
        str: 生成的产品编号
    """
    from datetime import datetime

    # 获取前缀
    prefix = BusinessType.get_product_code_prefix(business_type_code)

    # 年月
    year_month = datetime.now().strftime('%y%m')

    # 构建模式
    pattern = f'{prefix}-{year_month}-%'

    # 查找当月最大序号
    if table_model:
        # 使用指定的模型查询
        max_record = table_model.query.filter(
            table_model.product_code.like(pattern)
        ).order_by(table_model.product_code.desc()).first()
    else:
        # 默认使用统一产品表
        from App_new.business.products.models import ProductsUnified
        max_record = ProductsUnified.query.filter(
            ProductsUnified.product_code.like(pattern)
        ).order_by(ProductsUnified.product_code.desc()).first()

    if max_record and max_record.product_code:
        try:
            last_seq = int(max_record.product_code.split('-')[-1])
            new_seq = last_seq + 1
        except ValueError:
            new_seq = 1
    else:
        new_seq = 1

    return f'{prefix}-{year_month}-{new_seq:03d}'
