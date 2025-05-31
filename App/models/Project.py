from ..exts import db
from datetime import datetime
import json

class Customer(db.Model):
    """客户模型"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='客户名称')
    phone = db.Column(db.String(20), nullable=True, comment='电话')
    email = db.Column(db.String(100), nullable=True, comment='邮箱')
    id_number = db.Column(db.String(30), nullable=True, comment='证件号码')
    id_type = db.Column(db.String(20), nullable=True, comment='证件类型')
    address = db.Column(db.Text, nullable=True, comment='地址')
    company = db.Column(db.String(100), nullable=True, comment='公司名称')
    contact_person = db.Column(db.String(50), nullable=True, comment='联系人')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    projects = db.relationship('Project', back_populates='customer')

    def __repr__(self):
        return f'<Customer {self.name}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'id_number': self.id_number,
            'id_type': self.id_type,
            'address': self.address,
            'company': self.company,
            'contact_person': self.contact_person
        }

class Project(db.Model):
    """项目主表"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hid = db.Column(db.String(20), unique=True, nullable=False, comment='项目编号')
    project_name = db.Column(db.String(100), nullable=False, comment='项目名称')
    name = db.Column(db.String(100), nullable=True, comment='订单显示名称/标题')
    
    # 客户信息
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True, comment='客户ID')
    client_name = db.Column(db.String(100), nullable=False, comment='客户名称')
    customer_phone = db.Column(db.String(20), nullable=True, comment='客户电话')
    customer_email = db.Column(db.String(100), nullable=True, comment='客户邮箱')
    customer_id_number = db.Column(db.String(30), nullable=True, comment='客户证件号码')
    customer_id_type = db.Column(db.String(20), nullable=True, comment='客户证件类型')
    customer_company = db.Column(db.String(100), nullable=True, comment='客户公司名称')
    customer_contact_person = db.Column(db.String(50), nullable=True, comment='客户联系人')
    
    description = db.Column(db.Text, comment='项目描述')
    status = db.Column(db.Enum('draft', 'active', 'completed', 'cancelled'), 
                      default='draft', nullable=False, comment='项目状态')
    
    # 金额信息
    total_amount = db.Column(db.Numeric(10, 2), nullable=True, comment='总金额')
    paid_amount = db.Column(db.Numeric(10, 2), nullable=True, comment='已付金额')
    balance = db.Column(db.Numeric(10, 2), nullable=True, comment='余额')
    
    # 日期信息
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date(), comment='项目开始日期')
    end_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date(), comment='项目结束日期')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    refs = db.relationship('ProjectRef', backref='project', cascade='all, delete-orphan')
    customer = db.relationship('Customer', back_populates='projects')

    @property
    def calculate_balance(self):
        """计算余额"""
        if self.total_amount is None:
            return None
        paid = self.paid_amount or 0
        return float(self.total_amount - paid)

    @property
    def calculated_total(self):
        """计算总金额（从REF汇总）"""
        return sum(ref.total_amount for ref in self.refs) if self.refs else 0

    def update_customer_info(self, customer):
        """更新客户信息"""
        if customer:
            self.customer_id = customer.id
            self.client_name = customer.name
            self.customer_phone = customer.phone
            self.customer_email = customer.email
            self.customer_id_number = customer.id_number
            self.customer_id_type = customer.id_type
            self.customer_company = customer.company
            self.customer_contact_person = customer.contact_person

    @classmethod
    def generate_hid(cls):
        """生成项目编号 HID"""
        # 格式: H + 年月日 + 3位序号, 例如: H2024031001
        today = datetime.now()
        date_str = today.strftime('%Y%m%d')
        
        # 查找当天最后一个编号
        last_hid = cls.query.filter(
            cls.hid.like(f'H{date_str}%')
        ).order_by(cls.hid.desc()).first()

        if last_hid:
            last_number = int(last_hid.hid[-3:])
            new_number = str(last_number + 1).zfill(3)
        else:
            new_number = '001'

        return f'H{date_str}{new_number}'

class ProjectRef(db.Model):
    """项目REF表"""
    __tablename__ = 'project_refs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    ref_number = db.Column(db.String(30), unique=True, nullable=False, comment='REF编号')
    name = db.Column(db.String(100), nullable=True, comment='REF订单名称')
    ref_type_id = db.Column(db.Integer, db.ForeignKey('business_types.id'), nullable=False, comment='REF类型ID')
    description = db.Column(db.String(200), nullable=False, comment='描述')
    
    # 供应商信息
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=True, comment='供应商ID')
    supplier_contact = db.Column(db.String(50), nullable=True, comment='供应商联系人')
    supplier_phone = db.Column(db.String(20), nullable=True, comment='供应商联系电话')
    
    # 价格信息
    selling_price = db.Column(db.Numeric(10, 2), nullable=True, comment='销售价格')
    cost_price = db.Column(db.Numeric(10, 2), nullable=True, comment='成本价格')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币类型')
    
    # 日期信息
    expected_delivery_date = db.Column(db.Date, nullable=True, comment='预计交付日期')
    actual_delivery_date = db.Column(db.Date, nullable=True, comment='实际交付日期')
    
    # 备注和附加信息
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    attachments = db.Column(db.Text, nullable=True, comment='附件列表(JSON)')
    
    # 状态信息
    status = db.Column(db.Enum('draft', 'processing', 'completed', 'cancelled'),
                      default='draft', nullable=False, comment='状态')
    payment_status = db.Column(db.Enum('unpaid', 'partial', 'paid', 'refunded'),
                           default='unpaid', nullable=False, comment='支付状态')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    eos = db.relationship('ProjectEO', back_populates='ref', cascade='all, delete-orphan')
    ref_type = db.relationship('BusinessType', backref='refs')
    supplier = db.relationship('Supplier', backref='refs')
    items = db.relationship('RefOrderItem', backref='ref', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ProjectRef {self.ref_number}>'

    @property
    def total_amount(self):
        """计算订单总金额"""
        return sum(item.total_price for item in self.items) if self.items else 0

    @property
    def total_cost(self):
        """计算订单总成本"""
        return sum(item.unit_price * item.quantity for item in self.items) if self.items else 0

    @property
    def profit(self):
        """计算利润"""
        return self.total_amount - self.total_cost

    @property
    def profit_margin(self):
        """计算利润率"""
        if self.total_amount == 0:
            return 0
        return (self.profit / self.total_amount) * 100

    @classmethod
    def generate_ref_number(cls, project_hid):
        """生成REF编号"""
        # 检查项目是否存在（仅在非新项目时检查）
        today = datetime.now().strftime('%Y%m%d')
        if not project_hid.endswith(today):
            project = Project.query.filter_by(hid=project_hid).first()
            if not project:
                raise ValueError(f'项目编号 {project_hid} 不存在')

        # 查找当前项目最后一个REF编号
        last_ref = cls.query.filter(
            cls.ref_number.like(f'{project_hid}-R%')
        ).order_by(cls.ref_number.desc()).first()

        if last_ref:
            last_number = int(last_ref.ref_number.split('-R')[1])
            new_number = str(last_number + 1).zfill(2)
        else:
            new_number = '01'

        return f'{project_hid}-R{new_number}'

class ProjectEO(db.Model):
    """项目EO表"""
    __tablename__ = 'project_eos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False)
    eo_number = db.Column(db.String(30), unique=True, nullable=False, comment='EO编号')
    name = db.Column(db.String(100), nullable=True, comment='EO订单名称')
    supplier_type = db.Column(db.Enum('visa', 'flight', 'hotel', 'transport', 'local_operator', 'other'),
                            nullable=False, comment='供应商类型')
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    
    # 外部系统信息
    external_system = db.Column(db.String(50), nullable=True, comment='外部系统名称')
    external_status = db.Column(db.String(50), nullable=True, comment='外部系统状态')
    external_reference = db.Column(db.String(100), nullable=True, comment='外部系统参考号')
    
    # 金额和状态信息
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币类型')
    remarks = db.Column(db.Text, comment='备注')
    status = db.Column(db.Enum('draft', 'confirmed', 'paid', 'cancelled'),
                      default='draft', nullable=False, comment='状态')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    supplier = db.relationship('Supplier', backref='eos')
    ref = db.relationship('ProjectRef', back_populates='eos')

    def __repr__(self):
        return f'<ProjectEO {self.eo_number}: {self.name}>'

    @property
    def is_external_synced(self):
        """检查是否与外部系统同步"""
        return bool(self.external_system and self.external_status and self.external_reference)

    @property
    def formatted_amount(self):
        """格式化金额显示"""
        return f"{self.currency} {float(self.amount):,.2f}"

    @classmethod
    def generate_eo_number(cls, ref_number):
        """生成EO编号"""
        # 格式: REF编号-E + 2位序号, 例如: H2024031001-R01-E01
        last_eo = cls.query.filter(
            cls.eo_number.like(f'{ref_number}-E%')
        ).order_by(cls.eo_number.desc()).first()

        if last_eo:
            last_number = int(last_eo.eo_number.split('-E')[1])
            new_number = str(last_number + 1).zfill(2)
        else:
            new_number = '01'

        return f'{ref_number}-E{new_number}'

class RefOrderItem(db.Model):
    """REF订单项目表"""
    __tablename__ = 'ref_order_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False)
    item_name = db.Column(db.String(200), nullable=False, comment='项目名称')
    quantity = db.Column(db.Integer, nullable=False, default=1, comment='数量')
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, comment='单价')
    total_price = db.Column(db.Numeric(10, 2), nullable=False, comment='总价')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<RefOrderItem {self.item_name}>'

    @property
    def calculate_total(self):
        """计算总价"""
        return float(self.unit_price * self.quantity) 