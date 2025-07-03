from App.exts import db
from datetime import datetime
import json

class CustomerCompany(db.Model):
    """客户公司模型"""
    __tablename__ = 'customer_companies'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False, unique=True, comment='公司名称')
    company_code = db.Column(db.String(50), nullable=True, comment='公司代码')
    contact_person = db.Column(db.String(50), nullable=True, comment='联系人')
    contact_phone = db.Column(db.String(20), nullable=True, comment='联系电话')
    contact_email = db.Column(db.String(100), nullable=True, comment='联系邮箱')
    address = db.Column(db.Text, nullable=True, comment='公司地址')
    industry = db.Column(db.String(50), nullable=True, comment='行业')
    company_size = db.Column(db.String(20), nullable=True, comment='公司规模')
    credit_limit = db.Column(db.Numeric(15, 2), nullable=True, comment='信用额度')
    currency = db.Column(db.String(10), default='SGD', comment='币种')
    status = db.Column(db.Enum('active', 'inactive', 'suspended'), default='active', comment='状态')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')
    
    # 关联项目
    projects = db.relationship('ProjectHeader', backref='company', lazy='dynamic')
    
    def __repr__(self):
        return f'<CustomerCompany {self.company_name}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'company_code': self.company_code,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'address': self.address,
            'industry': self.industry,
            'company_size': self.company_size,
            'credit_limit': float(self.credit_limit) if self.credit_limit else None,
            'currency': self.currency,
            'status': self.status,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

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

    # 关系 - 如果需要与项目主表关联，可以添加以下关系
    # headers = db.relationship('ProjectHeader', backref='customer')

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

class ProjectHeader(db.Model):
    """
    项目主表（HID头表）
    """
    __tablename__ = 'project_headers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hid = db.Column(db.String(20), unique=True, nullable=False, comment='项目编号（如H20240702001）')
    desc = db.Column(db.String(200), comment='项目描述')
    company_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id'), comment='客户公司ID')
    company_name = db.Column(db.String(100), comment='公司名称')
    limit = db.Column(db.String(50), comment='额度限制')
    contact = db.Column(db.String(50), comment='联系人')
    dept = db.Column(db.String(50), comment='部门')
    staff_id = db.Column(db.Integer, comment='经办人ID')
    staff_name = db.Column(db.String(50), comment='经办人姓名')
    currency = db.Column(db.String(10), comment='币种')
    type = db.Column(db.String(50), comment='类型')
    source = db.Column(db.String(50), comment='来源')
    country = db.Column(db.String(50), comment='国家')
    status = db.Column(
        db.Enum('draft', 'active', 'completed', 'cancelled'),
        default='draft',
        nullable=False,
        comment='状态'
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='最后更新时间')
    last_updated_by = db.Column(db.String(50), comment='最后操作人')
    remarks = db.Column(db.Text, comment='备注')

    # 关联REF明细
    refs = db.relationship('ProjectRef', backref='header', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ProjectHeader {self.hid} - {self.desc}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'hid': self.hid,
            'desc': self.desc,
            'company_id': self.company_id,
            'company_name': self.company_name,
            'limit': self.limit,
            'contact': self.contact,
            'dept': self.dept,
            'staff_id': self.staff_id,
            'staff_name': self.staff_name,
            'currency': self.currency,
            'type': self.type,
            'source': self.source,
            'country': self.country,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_updated_by': self.last_updated_by,
            'remarks': self.remarks
        }

    @classmethod
    def generate_hid(cls):
        """生成项目编号（HID）"""
        # 格式: H + YYYYMMDD + 3位序号, 例如: H20240310001
        today = datetime.now().strftime('%Y%m%d')
        
        # 查找今天创建的项目数量
        today_count = cls.query.filter(
            cls.hid.like(f'H{today}%')
        ).count()
        
        # 生成3位序号
        sequence = str(today_count + 1).zfill(3)
        
        return f'H{today}{sequence}'

class ProjectRef(db.Model):
    """项目REF表"""
    __tablename__ = 'project_refs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=False, comment='HID主表ID')
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

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'header_id': self.header_id,
            'ref_number': self.ref_number,
            'name': self.name,
            'ref_type_id': self.ref_type_id,
            'description': self.description,
            'supplier_id': self.supplier_id,
            'supplier_contact': self.supplier_contact,
            'supplier_phone': self.supplier_phone,
            'selling_price': float(self.selling_price) if self.selling_price else None,
            'cost_price': float(self.cost_price) if self.cost_price else None,
            'currency': self.currency,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'actual_delivery_date': self.actual_delivery_date.isoformat() if self.actual_delivery_date else None,
            'remarks': self.remarks,
            'status': self.status,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

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
            header = ProjectHeader.query.filter_by(hid=project_hid).first()
            if not header:
                raise ValueError(f'项目编号 {project_hid} 不存在')

        # 查找当前主表最后一个REF编号
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
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False, comment='REF明细ID')
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

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'ref_id': self.ref_id,
            'eo_number': self.eo_number,
            'name': self.name,
            'supplier_type': self.supplier_type,
            'supplier_id': self.supplier_id,
            'external_system': self.external_system,
            'external_status': self.external_status,
            'external_reference': self.external_reference,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'remarks': self.remarks,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

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