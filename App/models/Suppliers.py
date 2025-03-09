from ..exts import db  # 确保你已正确导入 db 对象
from datetime import datetime

class Supplier(db.Model):
    """供应商表"""
    __tablename__ = 'suppliers'

    supplier_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
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
