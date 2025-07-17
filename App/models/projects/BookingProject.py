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
    limit = db.Column(db.String(50), comment='额度限制')
    contact = db.Column(db.String(50), comment='联系人')
    dept = db.Column(db.String(50), comment='部门')
    staff_id = db.Column(db.Integer, comment='经办人ID')
    staff_name = db.Column(db.String(50), comment='经办人姓名')
    currency = db.Column(db.String(10), comment='币种')
    leader_name = db.Column(db.String(100), nullable=True)
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
            'limit': self.limit,
            'contact': self.contact,
            'dept': self.dept,
            'staff_id': self.staff_id,
            'staff_name': self.staff_name,
            'currency': self.currency,
            'leader_name': self.leader_name,
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
        # 格式: H + 数字序号, 例如: H1, H2, H3...
        
        # 查找最后一个HID编号
        last_header = cls.query.filter(
            cls.hid.like('H%')
        ).order_by(
            db.func.cast(db.func.substring(cls.hid, 2), db.Integer).desc()
        ).first()
        
        if last_header:
            # 提取数字部分
            try:
                last_number = int(last_header.hid[1:])  # 去掉'H'前缀
                new_number = last_number + 1
            except ValueError:
                # 如果解析失败，从1开始
                new_number = 1
        else:
            new_number = 1
        
        return f'H{new_number}'

    @property
    def total_selling_amount(self):
        """总销售金额"""
        total = 0
        for ref in self.refs:
            if ref.selling_price:
                total += float(ref.selling_price)
        return total

    @property
    def total_cost_amount(self):
        """总成本金额"""
        total = 0
        for ref in self.refs:
            if ref.cost_price:
                total += float(ref.cost_price)
        return total

    @property
    def total_profit(self):
        """总利润"""
        return self.total_selling_amount - self.total_cost_amount

    @property
    def total_paid_amount(self):
        """总已付款金额"""
        total = 0
        for ref in self.refs:
            if ref.selling_price:
                # 使用辅助方法计算该REF的实际已收款总额
                ref_received = ProjectReceipt.get_ref_total_received(ref.id, self.id)
                total += ref_received
        return total

    @property
    def total_unpaid_amount(self):
        """总未付款金额"""
        return self.total_selling_amount - self.total_paid_amount

    @property
    def payment_status_summary(self):
        """付款状态汇总"""
        paid_count = sum(1 for ref in self.refs if ref.payment_status == 'paid')
        partial_count = sum(1 for ref in self.refs if ref.payment_status == 'partial')
        unpaid_count = sum(1 for ref in self.refs if ref.payment_status == 'unpaid')
        total_count = len(self.refs)
        
        return {
            'paid': paid_count,
            'partial': partial_count,
            'unpaid': unpaid_count,
            'total': total_count
        }

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
    
    # 联系人信息
    contact_name = db.Column(db.String(50), nullable=True, comment='联系人姓名')
    contact_phone = db.Column(db.String(20), nullable=True, comment='联系电话')
    contact_email = db.Column(db.String(100), nullable=True, comment='电子邮箱')
    leader_name = db.Column(db.String(100), nullable=True, comment='负责人姓名')
    
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
    extra_info = db.Column(db.Text, nullable=True, comment='各业务类型专属字段(JSON)')
    
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
    
    # 机票相关关联关系
    flight_passengers = db.relationship('ProjectFlightPassenger', backref='ref', cascade='all, delete-orphan')
    flight_segments = db.relationship('ProjectFlightSegment', backref='ref', cascade='all, delete-orphan')

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
            'contact_name': self.contact_name,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'leader_name': self.leader_name,
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

    @property
    def ref_profit(self):
        """计算REF利润（售价-成本）"""
        if self.selling_price and self.cost_price:
            return float(self.selling_price) - float(self.cost_price)
        elif self.selling_price:
            return float(self.selling_price)
        else:
            return 0

    @property
    def ref_profit_margin(self):
        """计算REF利润率"""
        if self.selling_price and self.selling_price > 0:
            return (self.ref_profit / float(self.selling_price)) * 100
        return 0

    @property
    def unpaid_amount(self):
        """计算REF未付款金额"""
        if not self.selling_price:
            return 0
        
        # 使用辅助方法计算已确认的收款总额（包括项目级别收款记录的分配）
        total_received = ProjectReceipt.get_ref_total_received(self.id, self.header_id)
        unpaid = float(self.selling_price) - total_received
        return max(0, unpaid)  # 确保不会返回负数

    # 机票相关计算属性
    @property
    def total_flight_selling_price(self):
        """计算机票总售价"""
        return sum(p.selling_price or 0 for p in self.flight_passengers)

    @property
    def total_flight_cost_price(self):
        """计算机票总成本"""
        return sum(p.cost_price or 0 for p in self.flight_passengers)

    @property
    def flight_profit(self):
        """计算机票利润"""
        return self.total_flight_selling_price - self.total_flight_cost_price

    @classmethod
    def generate_ref_number(cls, project_hid=None):
        """生成REF编号"""
        # 查找全局最后一个REF编号（按数字排序）
        last_ref = cls.query.filter(
            cls.ref_number.like('R%')
        ).order_by(
            db.func.cast(db.func.substring(cls.ref_number, 2), db.Integer).desc()
        ).first()

        if last_ref:
            # 提取数字部分
            try:
                last_number = int(last_ref.ref_number[1:])  # 去掉'R'前缀
                new_number = str(last_number + 1).zfill(2)
            except ValueError:
                # 如果解析失败，从01开始
                new_number = '01'
        else:
            new_number = '01'

        return f'R{new_number}'

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
    def generate_eo_number(cls, ref_number=None):
        """生成EO编号"""
        # 格式: E + 2位序号, 例如: E01, E02, E03...
        last_eo = cls.query.order_by(cls.eo_number.desc()).first()

        if last_eo:
            # 提取最后一个EO编号中的数字部分
            try:
                last_number = int(last_eo.eo_number[1:])  # 去掉'E'前缀，取数字部分
                new_number = str(last_number + 1).zfill(2)
            except ValueError:
                # 如果解析失败，从01开始
                new_number = '01'
        else:
            new_number = '01'

        return f'E{new_number}'

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




class ProjectFlightPassenger(db.Model):
    """机票乘客信息表 - 3级表"""
    __tablename__ = 'project_flight_passengers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False, comment='REF明细ID')
    
    # 乘客基本信息
    name = db.Column(db.String(50), nullable=False, comment='乘客姓名')
    passenger_type = db.Column(db.String(10), nullable=False, default='adult', comment='乘客类型：adult/child/infant')
    
    # 票价信息
    selling_price = db.Column(db.Numeric(10, 2), comment='售价')
    cost_price = db.Column(db.Numeric(10, 2), comment='成本')
    
    # 票务信息
    ticket_number = db.Column(db.String(50), comment='电子客票号')
    pnr = db.Column(db.String(6), comment='PNR编码')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ProjectFlightPassenger {self.name}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'ref_id': self.ref_id,
            'name': self.name,
            'passenger_type': self.passenger_type,
            'selling_price': float(self.selling_price) if self.selling_price else None,
            'cost_price': float(self.cost_price) if self.cost_price else None,
            'ticket_number': self.ticket_number,
            'pnr': self.pnr,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectFlightSegment(db.Model):
    """机票航段信息表 - 3级表"""
    __tablename__ = 'project_flight_segments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False, comment='REF明细ID')
    
    # 航班信息
    flight_number = db.Column(db.String(10), nullable=False, comment='航班号')
    departure_airport = db.Column(db.String(3), nullable=False, comment='出发机场')
    arrival_airport = db.Column(db.String(3), nullable=False, comment='到达机场')
    departure_time = db.Column(db.DateTime, nullable=False, comment='起飞时间')
    arrival_time = db.Column(db.DateTime, nullable=False, comment='到达时间')
    
    # 舱位信息
    cabin_class = db.Column(db.String(20), nullable=False, comment='舱位等级')
    cabin_code = db.Column(db.String(2), nullable=False, comment='舱位代码')
    
    # 航段状态
    status = db.Column(db.String(20), nullable=False, default='pending', comment='航段状态')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ProjectFlightSegment {self.flight_number}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'ref_id': self.ref_id,
            'flight_number': self.flight_number,
            'departure_airport': self.departure_airport,
            'arrival_airport': self.arrival_airport,
            'departure_time': self.departure_time.isoformat() if self.departure_time else None,
            'arrival_time': self.arrival_time.isoformat() if self.arrival_time else None,
            'cabin_class': self.cabin_class,
            'cabin_code': self.cabin_code,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ProjectReceipt(db.Model):
    """项目收款记录表"""
    __tablename__ = 'project_receipts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    receipt_number = db.Column(db.String(30), unique=True, nullable=False, comment='收款单号')
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=True, comment='REF明细ID（可选）')
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=False, comment='项目主表ID')
    
    # 收款信息
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='收款金额')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币类型')
    payment_method = db.Column(db.Enum('cash', 'bank_transfer', 'credit_card', 'cheque', 'other'),
                              nullable=False, comment='付款方式')
    payment_date = db.Column(db.Date, nullable=False, comment='收款日期')
    
    # 收款人信息
    payer_name = db.Column(db.String(100), nullable=True, comment='付款人姓名')
    payer_contact = db.Column(db.String(50), nullable=True, comment='付款人联系方式')
    payer_company = db.Column(db.String(100), nullable=True, comment='付款人公司')
    
    # 银行信息（如果是银行转账）
    bank_name = db.Column(db.String(100), nullable=True, comment='银行名称')
    account_number = db.Column(db.String(50), nullable=True, comment='账号')
    transaction_id = db.Column(db.String(100), nullable=True, comment='交易流水号')
    
    # 状态和备注
    status = db.Column(db.Enum('pending', 'confirmed', 'cancelled'),
                      default='pending', nullable=False, comment='收款状态')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    extra_info = db.Column(db.Text, nullable=True, comment='额外信息(JSON格式，用于存储分配信息等)')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')
    
    # 关联关系
    ref = db.relationship('ProjectRef', backref='receipts')
    header = db.relationship('ProjectHeader', backref='receipts')

    def __repr__(self):
        return f'<ProjectReceipt {self.receipt_number}: {self.amount} {self.currency}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'receipt_number': self.receipt_number,
            'ref_id': self.ref_id,
            'header_id': self.header_id,
            'amount': float(self.amount) if self.amount else 0,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payer_name': self.payer_name,
            'payer_contact': self.payer_contact,
            'payer_company': self.payer_company,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'remarks': self.remarks,
            'extra_info': json.loads(self.extra_info) if self.extra_info else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

    @classmethod
    def generate_receipt_number(cls):
        """生成收款单号"""
        # 格式: RC + 年月日 + 3位序号, 例如: RC20240702001
        
        today = datetime.now().strftime('%Y%m%d')
        prefix = f'RC{today}'
        
        # 查找今天最后一个收款单号
        last_receipt = cls.query.filter(
            cls.receipt_number.like(f'{prefix}%')
        ).order_by(cls.receipt_number.desc()).first()
        
        if last_receipt:
            # 提取序号部分
            try:
                last_number = int(last_receipt.receipt_number[-3:])
                new_number = str(last_number + 1).zfill(3)
            except ValueError:
                new_number = '001'
        else:
            new_number = '001'
        
        return f'{prefix}{new_number}'

    @property
    def payment_method_display(self):
        """付款方式显示文本"""
        method_map = {
            'cash': '现金',
            'bank_transfer': '银行转账',
            'credit_card': '信用卡',
            'cheque': '支票',
            'other': '其他'
        }
        return method_map.get(self.payment_method, self.payment_method)

    @property
    def status_display(self):
        """状态显示文本"""
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'cancelled': '已取消'
        }
        return status_map.get(self.status, self.status)

    @property
    def receipt_type(self):
        """收款类型：项目级别或REF级别"""
        return '项目级别' if self.ref_id is None else 'REF级别'

    @classmethod
    def get_ref_total_received(cls, ref_id, header_id):
        """获取REF的实际已收款总额（包括项目级别收款记录的分配）"""
        # 1. 直接关联的REF级别收款记录
        ref_receipts = cls.query.filter_by(ref_id=ref_id, status='confirmed').all()
        total_received = sum(float(r.amount) for r in ref_receipts)
        
        # 2. 项目级别收款记录中分配给该REF的金额
        project_receipts = cls.query.filter_by(header_id=header_id, ref_id=None, status='confirmed').all()
        for project_receipt in project_receipts:
            if project_receipt.extra_info:
                try:
                    distribution_info = json.loads(project_receipt.extra_info)
                    if 'distribution' in distribution_info:
                        for dist in distribution_info['distribution']:
                            if dist['ref_id'] == ref_id:
                                total_received += dist['amount']
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
        
        return total_received

    @classmethod
    def get_project_unpaid_amount(cls, header_id):
        """获取项目的总未收款金额"""
        header = ProjectHeader.query.get(header_id)
        if not header:
            return 0
        
        # 计算所有REF的未收款总额
        total_unpaid = 0
        for ref in header.refs:
            if ref.selling_price:
                # 计算该REF的已收款总额
                # 1. 直接关联的REF级别收款记录
                ref_receipts = cls.query.filter_by(ref_id=ref.id, status='confirmed').all()
                ref_received = sum(float(r.amount) for r in ref_receipts)
                
                # 2. 项目级别收款记录中分配给该REF的金额
                project_receipts = cls.query.filter_by(header_id=header_id, ref_id=None, status='confirmed').all()
                for project_receipt in project_receipts:
                    if project_receipt.extra_info:
                        try:
                            distribution_info = json.loads(project_receipt.extra_info)
                            if 'distribution' in distribution_info:
                                for dist in distribution_info['distribution']:
                                    if dist['ref_id'] == ref.id:
                                        ref_received += dist['amount']
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass
                
                ref_unpaid = float(ref.selling_price) - ref_received
                if ref_unpaid > 0:
                    total_unpaid += ref_unpaid
        
        return total_unpaid

    @classmethod
    def can_create_project_receipt(cls, header_id, amount):
        """检查是否可以创建项目级别收款"""
        unpaid_amount = cls.get_project_unpaid_amount(header_id)
        return float(amount) <= unpaid_amount

    @classmethod
    def distribute_project_receipt(cls, header_id, amount, distribution_method='auto'):
        """
        分配项目级别收款到各个REF
        
        Args:
            header_id: 项目ID
            amount: 收款金额
            distribution_method: 分配方式 ('auto', 'manual')
        
        Returns:
            dict: 分配结果
        """
        header = ProjectHeader.query.get(header_id)
        if not header:
            return {'success': False, 'message': '项目不存在'}
        
        # 检查收款金额是否超过未收款总额
        total_unpaid = cls.get_project_unpaid_amount(header_id)
        if float(amount) > total_unpaid:
            return {'success': False, 'message': f'收款金额({amount})不能超过未收款总额({total_unpaid})'}
        
        # 获取所有有未收款的REF
        unpaid_refs = []
        for ref in header.refs:
            if ref.selling_price:
                ref_receipts = cls.query.filter_by(ref_id=ref.id, status='confirmed').all()
                ref_received = sum(float(r.amount) for r in ref_receipts)
                
                # 项目级别收款记录中分配给该REF的金额
                project_receipts = cls.query.filter_by(header_id=header_id, ref_id=None, status='confirmed').all()
                for project_receipt in project_receipts:
                    if project_receipt.extra_info:
                        try:
                            distribution_info = json.loads(project_receipt.extra_info)
                            if 'distribution' in distribution_info:
                                for dist in distribution_info['distribution']:
                                    if dist['ref_id'] == ref.id:
                                        ref_received += dist['amount']
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass
                
                ref_unpaid = float(ref.selling_price) - ref_received
                if ref_unpaid > 0:
                    unpaid_refs.append({
                        'ref': ref,
                        'unpaid': ref_unpaid
                    })
        
        if not unpaid_refs:
            return {'success': False, 'message': '没有需要收款的REF'}
        
        # 按分配方式计算分配金额
        distribution = []
        remaining_amount = float(amount)
        
        if distribution_method == 'auto':
            # 按未收款比例自动分配
            total_unpaid = sum(ref['unpaid'] for ref in unpaid_refs)
            
            # 如果收款金额正好等于总未收款金额，优先完全覆盖每个REF
            if abs(float(amount) - total_unpaid) < 0.01:  # 允许0.01的误差
                for ref_info in unpaid_refs:
                    if remaining_amount <= 0:
                        break
                    # 完全覆盖该REF的未收款金额
                    allocated = min(ref_info['unpaid'], remaining_amount)
                    if allocated > 0:
                        distribution.append({
                            'ref_id': ref_info['ref'].id,
                            'amount': allocated,
                            'method': 'auto'
                        })
                        remaining_amount -= allocated
            else:
                # 按比例分配
                for ref_info in unpaid_refs:
                    if remaining_amount <= 0:
                        break
                    # 按比例分配，但不超过该REF的未收款金额
                    allocated = min(ref_info['unpaid'], remaining_amount * (ref_info['unpaid'] / total_unpaid))
                    if allocated > 0:
                        distribution.append({
                            'ref_id': ref_info['ref'].id,
                            'amount': allocated,
                            'method': 'auto'
                        })
                        remaining_amount -= allocated
        
        return {
            'success': True,
            'distribution': distribution,
            'remaining_amount': remaining_amount,
            'total_unpaid': total_unpaid
        } 