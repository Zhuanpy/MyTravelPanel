# -*- coding: utf-8 -*-
"""
供应商模型兼容层
原 Supplier 模型已合并到 CustomerCompany，此文件保留用于兼容旧代码
所有新代码应直接使用 CustomerCompany 模型
"""

from App_new.business.projects.models.project import CustomerCompany
from App_new.shared.models.business_types import BusinessType

# 兼容别名 - 新代码请直接使用 CustomerCompany
Supplier = CustomerCompany


def get_suppliers():
    """获取所有供应商（is_supplier=True 的公司）"""
    return CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()


def get_supplier_by_id(supplier_id):
    """
    通过 ID 获取供应商
    注意：现在使用 company_id，旧的 supplier_id 需要通过映射表查询
    """
    # 先尝试直接通过 company_id 查询
    company = CustomerCompany.query.filter(
        CustomerCompany.id == supplier_id,
        CustomerCompany.is_supplier == True
    ).first()

    if company:
        return company

    # 如果没找到，尝试通过映射表查询（兼容旧的 supplier_id）
    from App_new.exts import db
    from sqlalchemy import text

    try:
        result = db.session.execute(text(
            'SELECT company_id FROM supplier_company_mapping WHERE supplier_id = :sid'
        ), {'sid': supplier_id}).fetchone()

        if result:
            return CustomerCompany.query.get(result[0])
    except:
        pass

    return None


def get_supplier_type_choices():
    """获取供应商类型选项"""
    business_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()
    return [(bt.id, bt.name) for bt in business_types]


def get_supplier_types():
    """获取供应商类型代码列表"""
    business_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()
    return [bt.code for bt in business_types]


# 保留旧的子模型定义（如果表仍存在）
# 这些模型暂时保留，但不再使用 suppliers 表的外键

from ...exts import db
from datetime import datetime


class SupplierService(db.Model):
    """供应商服务表（已废弃，保留兼容）"""
    __tablename__ = 'supplier_services'
    __table_args__ = {'extend_existing': True}

    service_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, nullable=True)  # 不再使用外键
    company_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id'), nullable=True)
    service_type = db.Column(db.Enum('hotel', 'transport', 'ticket', 'tour', 'other'), nullable=False)
    service_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.Enum('available', 'unavailable'), default='available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('CustomerCompany', foreign_keys=[company_id], overlaps="services")


class SupplierPrice(db.Model):
    """供应商价格表（已废弃，保留兼容）"""
    __tablename__ = 'supplier_prices'
    __table_args__ = {'extend_existing': True}

    price_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_id = db.Column(db.Integer, db.ForeignKey('supplier_services.service_id'), nullable=False)
    season = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SupplierContract(db.Model):
    """供应商合同表（已废弃，保留兼容）"""
    __tablename__ = 'supplier_contracts'
    __table_args__ = {'extend_existing': True}

    contract_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, nullable=True)  # 不再使用外键
    company_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id'), nullable=True)
    contract_number = db.Column(db.String(50), nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    terms = db.Column(db.Text)
    status = db.Column(db.Enum('active', 'expired', 'pending'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('CustomerCompany', foreign_keys=[company_id], overlaps="contracts")


# SupplierPayment 模型已迁移到 App_new/business/projects/models/supplier_payment.py
# 使用新的 SupplierPayment 模型：
# from App_new.business.projects.models.supplier_payment import SupplierPayment
