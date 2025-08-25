from App_new.exts import db
from datetime import date

# 供应商数据表: supplier_data_table
class SupplierData(db.Model):
    # 表名
    __tablename__ = 'supplier_data'

    # 供应商类型中英文映射
    SUPPLIER_TYPE_MAP = {
        'visa': '签证',
        'flight': '机票',
        'hotel': '酒店',
        'transport': '用车',
        'local_operator': '地接',
        'other': '其他'
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 创建时间
    create_date = db.Column(db.DateTime, index=True)
    # 最后更新日期 (last_updated)： 记录数据最后一次更新的时间，帮助保持数据的时效性。
    last_updated = db.Column(db.DateTime, index=True)

    # 供应商名字
    name = db.Column(db.String(255), index=True)
    # 供应商类型
    supplier_type = db.Column(db.Enum('visa', 'flight', 'hotel', 'transport', 'local_operator', 'other'), 
                            nullable=False, default='other', comment='供应商类型')
    # 供应商 地址
    address = db.Column(db.String(255), index=True)
    # 供应商联系信息
    contact_info = db.Column(db.String(255), index=True)

    # 供应商 联系人
    contact_person = db.Column(db.String(20), index=True)

    # 可以用来表示供应商是否处于活跃状态，例如：active、inactive，方便管理。
    status = db.Column(db.String(20), default='active', index=True)

    # 国家和地区 (country, region)：
    country = db.Column(db.String(50), index=True)
    region = db.Column(db.String(50), index=True)

    # 供应商评级或评价 (rating)：对供应商的服务或产品进行评级或评价，用于供应商管理的参考
    rating = db.Column(db.Float, index=True)

    # 备注 (notes)： 用于记录额外的供应商信息或与供应商的交互历史。
    notes = db.Column(db.Text)

    @property
    def supplier_type_display(self):
        """获取供应商类型的显示名称"""
        return self.SUPPLIER_TYPE_MAP.get(self.supplier_type, self.supplier_type)

    @classmethod
    def get_supplier_types(cls):
        """获取供应商类型列表"""
        return ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']

    @classmethod
    def get_supplier_type_choices(cls):
        """获取供应商类型选项（包含中英文）"""
        return [(type_code, cls.SUPPLIER_TYPE_MAP.get(type_code, type_code)) 
                for type_code in cls.get_supplier_types()]

    @classmethod
    def add_supplier(cls, name, address, contact_info=None, contact_person=None, status='active',
                     country=None, region=None, rating=None, notes=None):
        """
        添加供应商数据到数据库
        :param name: 供应商名字（必填）
        :param address: 供应商地址（必填）
        :param contact_info: 联系信息
        :param contact_person: 联系人
        :param status: 状态，默认 'active'
        :param country: 国家
        :param region: 地区
        :param rating: 评级
        :param notes: 备注
        :return: 新增的供应商实例或错误信息
        """

        try:
            # 如果 rating 为空字符串，则将其设置为 None
            if rating == '':
                rating = None

            new_supplier = cls(
                name=name,
                address=address,
                contact_info=contact_info,
                contact_person=contact_person,
                status=status,
                country=country,
                region=region,
                rating=rating,
                notes=notes,
                create_date=date.today(),
                last_updated=date.today()
            )

            db.session.add(new_supplier)
            db.session.commit()
            return new_supplier
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"添加供应商失败: {str(e)}")


# 旅游产品数据表: tour_product_data_table
class TourProductData(db.Model):
    # 表名
    __tablename__ = 'tour_product_data'

    # 主键 ID
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 产品名称
    name = db.Column(db.String(100), nullable=False)

    # 产品描述
    description = db.Column(db.Text, nullable=False)

    # 目的地
    destination = db.Column(db.String(100), nullable=False)

    # 出发日期
    departure_date = db.Column(db.Date, nullable=False)

    # 返回日期
    return_date = db.Column(db.Date, nullable=False)

    # 产品价格
    price = db.Column(db.Float, nullable=False)

    # 可用座位数
    available_seats = db.Column(db.Integer, nullable=False)

    # 创建时间
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # 更新时间
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f'<TourProductData {self.name}>'


# 系统账号数据表: system_account_data_table
class SystemAccountData(db.Model):
    # 表名
    __tablename__ = 'system_account_data'

    # 主键 ID
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 用户名
    username = db.Column(db.String(50))

    # 密码（建议存储加密后的密码）
    password_hash = db.Column(db.String(128))

    # 电子邮件
    email = db.Column(db.String(100))

    # 用户角色（如管理员、普通用户等）
    role = db.Column(db.String(20))

    # 账号状态（如激活、禁用等）
    status = db.Column(db.String(20), default='active')

    # 创建时间
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # 更新时间
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f'<SystemAccountData {self.username}>'

