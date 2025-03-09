from datetime import datetime
from datetime import date
from ..exts import db  # 确保你已正确导入 db 对象
from sqlalchemy import Date
from flask_sqlalchemy import SQLAlchemy


class Product(db.Model):

    __tablename__ = 'travelproducts'  # 可选：定义表名

    id = db.Column(db.Integer, primary_key=True)  # 主键
    city_name = db.Column(db.String(100), nullable=False)  # 新增城市名字
    company_name = db.Column(db.String(100), nullable=False)  # 公司名字
    product_name = db.Column(db.String(100), nullable=False)  # 产品名字
    created_at = db.Column(Date, default=datetime.utcnow().date)  # 创建时间，默认当前时间
    valid_until = db.Column(Date)  # 有效期

    def __init__(self, city_name: str, company_name: str, product_name: str, created_at: date, valid_until: date):
        self.id = None  # id由数据库自动生成
        self.city_name = city_name  # 新增城市名字
        self.company_name = company_name
        self.product_name = product_name
        self.created_at = created_at
        self.valid_until = valid_until  # 有效期需要传入

    @classmethod
    def add_product(cls, city_name: str, company_name: str, product_name: str, created_at: date,
                    valid_until: date) -> 'Product':
        """添加新产品到数据库。

        Args:
            city_name (str): 城市名称。
            company_name (str): 公司名称。
            product_name (str): 产品名称。
            created_at (date): 创建时间。
            valid_until (date): 产品有效期。

        Returns:
            Product: 返回新创建的产品实例。
        """
        # 创建新产品实例
        new_product = cls(city_name=city_name, company_name=company_name,
                          product_name=product_name, created_at=created_at,
                          valid_until=valid_until)

        # 将新产品添加到会话
        db.session.add(new_product)

        # 提交到数据库
        db.session.commit()

        return new_product  # 可选择返回新创建的产品实例

    @staticmethod
    def product_exists(city_name: str, company_name: str, product_name: str):
        # 查询数据库以检查产品是否存在
        return db.session.query(Product).filter_by(
            city_name=city_name,
            company_name=company_name,
            product_name=product_name
        ).first() is not None


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

# 定义 tour_project 表的模型
class TourProject(db.Model):

    __tablename__ = 'tour_project'

    id = db.Column(db.Integer, primary_key=True)  # 自增主键
    project_name = db.Column(db.String(100), nullable=False)  # 项目名称
    project_hid = db.Column(db.String(255), nullable=True)  # 项目HID，允许为空
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)  # 创建日期，默认为当前时间
    departure_date = db.Column(db.Date, nullable=False)  # 出发日期
    project_status = db.Column(db.String(50), nullable=False)  # 项目状态
    folder_name = db.Column(db.String(100), nullable=False)  # 项目状态
    contact_person = db.Column(db.String(100), nullable=False)  # 联系人
    contact_info = db.Column(db.String(100), nullable=False)  # 联系方式
    remarks = db.Column(db.Text, nullable=True)  # 备注

    def __init__(self, project_name, project_hid, departure_date, project_status, folder_name, contact_person, contact_info, remarks,
                 creation_date=None):
        self.project_name = project_name
        self.project_hid = project_hid
        self.departure_date = departure_date
        self.project_status = project_status
        self.folder_name = folder_name
        self.contact_person = contact_person
        self.contact_info = contact_info
        self.remarks = remarks
        self.creation_date = creation_date or datetime.utcnow()

    def save(self):
        """保存或更新当前实例到数据库"""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, project_id):
        """通过 ID 获取实例"""
        return cls.query.get(project_id)

    def to_dict(self):
        """将模型实例转化为字典，用于 JSON 响应"""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "project_hid": self.project_hid,
            "creation_date": self.creation_date.strftime('%Y-%m-%d'),
            "departure_date": self.departure_date.strftime('%Y-%m-%d'),
            "project_status": self.project_status,
            "folder_name": self.folder_name,
            "contact_person": self.contact_person,
            "contact_info": self.contact_info,
            "remarks": self.remarks
        }

class TourProduct(db.Model):
    __tablename__ = 'tour_products'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
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