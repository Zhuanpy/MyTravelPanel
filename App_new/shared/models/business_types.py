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
            'description': self.description,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def init_default_types(cls):
        """初始化默认业务类型"""
        from ...exts import db
        
        default_types = [
            {'code': 'flight', 'name': '机票', 'description': '航空机票服务', 'sort_order': 1},
            {'code': 'hotel', 'name': '酒店', 'description': '酒店预订服务', 'sort_order': 2},
            {'code': 'visa', 'name': '签证', 'description': '签证申请服务', 'sort_order': 3},
            {'code': 'tour', 'name': '旅游团', 'description': '旅游团服务', 'sort_order': 4},
            {'code': 'insurance', 'name': '保险', 'description': '旅游保险服务', 'sort_order': 5},
            {'code': 'transport', 'name': '交通', 'description': '交通服务', 'sort_order': 6},
            {'code': 'attraction', 'name': '景点/活动', 'description': '景点门票和活动', 'sort_order': 7},
            {'code': 'car', 'name': '租车', 'description': '汽车租赁服务', 'sort_order': 8},
            {'code': 'cruise', 'name': '邮轮', 'description': '邮轮旅游服务', 'sort_order': 9},
            {'code': 'ferry', 'name': '渡轮', 'description': '渡轮服务', 'sort_order': 10},
            {'code': 'land_tour', 'name': '地接', 'description': '地接服务', 'sort_order': 11},
            {'code': 'rail_coach', 'name': '火车/大巴', 'description': '铁路和公路交通', 'sort_order': 12},
            {'code': 'service_fee', 'name': '服务费', 'description': '各种服务费用', 'sort_order': 13},
            {'code': 'ticket', 'name': '门票', 'description': '各种门票服务', 'sort_order': 14},
            {'code': 'transfer', 'name': '接送', 'description': '接送服务', 'sort_order': 15},
            {'code': 'tour_package', 'name': '旅游套餐', 'description': '旅游套餐服务', 'sort_order': 16},
            {'code': 'voucher', 'name': '代金券', 'description': '代金券服务', 'sort_order': 17},
            {'code': 'other', 'name': '其他', 'description': '其他服务', 'sort_order': 18}
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
