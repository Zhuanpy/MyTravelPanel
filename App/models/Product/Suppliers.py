from App.exts import db  # 确保你已正确导入 db 对象
from datetime import datetime

class Supplier(db.Model):
    """供应商表"""
    __tablename__ = 'suppliers'

    # 供应商类型中英文映射
    SUPPLIER_TYPE_MAP = {
        'visa': '签证',
        'flight': '机票',
        'hotel': '酒店',
        'transport': '用车',
        'local_operator': '地接',
        'other': '其他'
    }

    supplier_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    supplier_type = db.Column(db.Enum('visa', 'flight', 'hotel', 'transport', 'local_operator', 'other'), 
                            nullable=False, default='other', comment='供应商类型')
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))
    address = db.Column(db.Text)
    country = db.Column(db.String(50))
    region = db.Column(db.String(50))
    status = db.Column(db.Enum('active', 'inactive'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # 关联关系
    services = db.relationship('SupplierService', backref='supplier', cascade="all, delete-orphan")
    contracts = db.relationship('SupplierContract', backref='supplier', cascade="all, delete-orphan")
    payments = db.relationship('SupplierPayment', backref='supplier', cascade="all, delete-orphan")

    def to_dict(self):
        """将供应商对象转换为字典，用于JSON序列化"""
        return {
            'supplier_id': self.supplier_id,
            'name': self.name,
            'supplier_type': self.supplier_type,
            'supplier_type_display': self.supplier_type_display,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'country': self.country,
            'region': self.region,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'notes': self.notes
        }

    @classmethod
    def get_supplier_types(cls):
        """获取供应商类型列表"""
        # 从 supplier_type 字段的枚举定义中获取类型列表
        enum_type = cls.supplier_type.type
        return enum_type.enums

    @classmethod
    def get_supplier_type_choices(cls):
        """获取供应商类型选项（包含中英文）"""
        return [(type_code, cls.SUPPLIER_TYPE_MAP.get(type_code, type_code)) 
                for type_code in cls.get_supplier_types()]

    @property
    def supplier_type_display(self):
        """获取供应商类型的显示名称"""
        return self.SUPPLIER_TYPE_MAP.get(self.supplier_type, self.supplier_type)




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
