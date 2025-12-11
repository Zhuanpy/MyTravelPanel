from ...exts import db  # 确保你已正确导入 db 对象
from datetime import datetime

class Supplier(db.Model):
    """供应商表"""
    __tablename__ = 'suppliers'

    supplier_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    supplier_type_id = db.Column(db.Integer, db.ForeignKey('business_types.id'), nullable=True, comment='供应商类型ID')
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))
    address = db.Column(db.Text)
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))
    region = db.Column(db.String(50))
    status = db.Column(db.Enum('active', 'inactive'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    click_count = db.Column(db.Integer, default=0, comment='点击次数')
    notes = db.Column(db.Text)

    # 关联关系
    supplier_type = db.relationship('BusinessType', foreign_keys=[supplier_type_id], backref='suppliers')
    services = db.relationship('SupplierService', backref='supplier', cascade="all, delete-orphan")
    contracts = db.relationship('SupplierContract', backref='supplier', cascade="all, delete-orphan")
    payments = db.relationship('SupplierPayment', backref='supplier', cascade="all, delete-orphan")
    # accounts 关联通过 Account 模型的 backref 自动创建

    def to_dict(self, include_accounts=False):
        """将供应商对象转换为字典，用于JSON序列化
        
        Args:
            include_accounts: 是否包含关联的账号信息
        """
        result = {
            'supplier_id': self.supplier_id,
            'name': self.name,
            'supplier_type_id': self.supplier_type_id,
            'supplier_type': self.supplier_type.code if self.supplier_type else None,
            'supplier_type_display': self.supplier_type_display,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'country': self.country,
            'city': self.city,
            'region': self.region,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'click_count': self.click_count,
            'notes': self.notes
        }
        
        # 添加关联账号数量
        if hasattr(self, 'accounts'):
            result['accounts_count'] = len(self.accounts) if self.accounts else 0
            
            # 如果需要包含详细账号信息
            if include_accounts:
                result['accounts'] = [
                    {
                        'id': acc.id,
                        'platform': acc.platform,
                        'username': acc.username,
                        'category': acc.category,
                        'owner': acc.owner
                    } for acc in self.accounts
                ] if self.accounts else []
        
        return result

    @classmethod
    def get_supplier_type_choices(cls):
        """从 business_types 表获取供应商类型选项"""
        from .business_types import BusinessType
        business_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()
        return [(bt.id, bt.name) for bt in business_types]

    @property
    def supplier_type_display(self):
        """获取供应商类型的显示名称"""
        if self.supplier_type:
            return self.supplier_type.name
        return '未设置'
    
    @property
    def supplier_type_code(self):
        """获取供应商类型的代码（兼容旧代码）"""
        if self.supplier_type:
            return self.supplier_type.code
        return None



class SupplierService(db.Model):
    """供应商服务表"""
    __tablename__ = 'supplier_services'

    service_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    service_type = db.Column(db.Enum('hotel', 'transport', 'ticket', 'tour', 'other'), nullable=False)
    service_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.Enum('available', 'unavailable'), default='available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联价格信息
    prices = db.relationship('SupplierPrice', backref='service', cascade="all, delete-orphan")


class SupplierPrice(db.Model):
    """供应商价格表"""
    __tablename__ = 'supplier_prices'

    price_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_id = db.Column(db.Integer, db.ForeignKey('supplier_services.service_id'), nullable=False)
    season = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SupplierContract(db.Model):
    """供应商合同表"""
    __tablename__ = 'supplier_contracts'

    contract_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    contract_number = db.Column(db.String(50), nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    terms = db.Column(db.Text)
    status = db.Column(db.Enum('active', 'expired', 'pending'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联付款信息
    payments = db.relationship('SupplierPayment', backref='contract', cascade="all, delete-orphan")


class SupplierPayment(db.Model):
    """供应商付款表"""
    __tablename__ = 'supplier_payments'

    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('supplier_contracts.contract_id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.Enum('bank_transfer', 'credit_card', 'cash', 'paypal'), nullable=False)
    status = db.Column(db.Enum('paid', 'pending', 'failed'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
