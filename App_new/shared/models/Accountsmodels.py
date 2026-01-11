from App_new.exts import db

# SupplierData 类已废弃，供应商数据已迁移到 CustomerCompany 表（is_supplier=True）
# 新代码请使用: from App_new.business.projects.models.project import CustomerCompany


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

