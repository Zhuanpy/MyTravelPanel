from App.exts import db
from datetime import datetime

class BusinessType(db.Model):
    """业务类型表"""
    __tablename__ = 'business_types'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True, comment='类型名称')
    code = db.Column(db.String(20), nullable=False, unique=True, comment='类型代码')
    description = db.Column(db.String(200), comment='描述')
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment='是否启用')
    sort_order = db.Column(db.Integer, default=0, comment='排序顺序')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'is_active': self.is_active,
            'sort_order': self.sort_order
        }

    @classmethod
    def init_default_types(cls):
        """初始化默认业务类型"""
        default_types = [
            {'name': '机票', 'code': 'airline', 'sort_order': 10},
            {'name': '景点/活动', 'code': 'attraction', 'sort_order': 20},
            {'name': '租车', 'code': 'car', 'sort_order': 30},
            {'name': '邮轮', 'code': 'cruise', 'sort_order': 40},
            {'name': '渡轮', 'code': 'ferry', 'sort_order': 50},
            {'name': '酒店', 'code': 'hotel', 'sort_order': 60},
            {'name': '保险', 'code': 'insurance', 'sort_order': 70},
            {'name': '地接', 'code': 'land_tour', 'sort_order': 80},
            {'name': '其他', 'code': 'miscellaneous', 'sort_order': 90},
            {'name': '火车/大巴', 'code': 'rail_coach', 'sort_order': 100},
            {'name': '服务费', 'code': 'service_fee', 'sort_order': 110},
            {'name': '门票', 'code': 'ticket', 'sort_order': 120},
            {'name': '接送', 'code': 'transfer', 'sort_order': 130},
            {'name': '签证', 'code': 'visa', 'sort_order': 140},
            {'name': '代金券', 'code': 'voucher', 'sort_order': 150},
            {'name': '旅游套餐', 'code': 'tour_package', 'sort_order': 160},
        ]

        for type_info in default_types:
            if not cls.query.filter_by(code=type_info['code']).first():
                new_type = cls(
                    name=type_info['name'],
                    code=type_info['code'],
                    sort_order=type_info['sort_order']
                )
                db.session.add(new_type)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e 