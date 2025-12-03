# -*- coding: utf-8 -*-
"""REF相关模型 - 项目REF订单和订单项"""

from App_new.exts import db
from datetime import datetime


class ProjectRef(db.Model):
    
    """项目REF表"""
    __tablename__ = 'project_refs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=False, comment='HID主表ID')
    ref_number = db.Column(db.String(30), unique=True, nullable=False, comment='REF编号')
    description = db.Column(db.String(100), nullable=True, comment='描述')
    detailed_description = db.Column(db.String(200), nullable=False, comment='详细描述')
    
    ref_type_id = db.Column(db.Integer, db.ForeignKey('business_types.id'), nullable=False, comment='REF类型ID')
    

    # 供应商信息
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=True, comment='供应商ID')

    # 价格信息
    selling_price = db.Column(db.Numeric(10, 2), nullable=True, comment='销售价格')
    cost_price = db.Column(db.Numeric(10, 2), nullable=True, comment='成本价格')
    currency = db.Column(db.String(3), default='SGD', nullable=False, comment='货币类型')

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

    # 关联关系 - 一个REF只能有一个EO
    eos = db.relationship('ProjectEO', back_populates='ref', cascade='all, delete-orphan', uselist=False)
    ref_type = db.relationship('BusinessType', backref='refs')
    supplier = db.relationship('Supplier', backref='refs')
    items = db.relationship('RefOrderItem', backref='ref', cascade='all, delete-orphan')

    # 机票相关关联关系
    # flight_passengers = db.relationship('ProjectFlightPassenger', backref='ref', cascade='all, delete-orphan')  # 暂时注释掉
    # flight_segments = db.relationship('ProjectFlightSegment', backref='ref', cascade='all, delete-orphan')  # 暂时注释掉

    def __repr__(self):
        return f'<ProjectRef {self.ref_number}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'header_id': self.header_id,
            'ref_number': self.ref_number,
            'description': self.description,
            'ref_type_id': self.ref_type_id,
            'detailed_description': self.detailed_description,
            'supplier_id': self.supplier_id,
            'selling_price': float(self.selling_price) if self.selling_price else None,
            'cost_price': float(self.cost_price) if self.cost_price else None,
            'currency': self.currency,
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
        selling_price = float(self.selling_price) if self.selling_price is not None else 0
        cost_price = float(self.cost_price) if self.cost_price is not None else 0
        return selling_price - cost_price

    @property
    def ref_profit_margin(self):
        """计算REF利润率"""
        selling_price = float(self.selling_price) if self.selling_price is not None else 0
        if selling_price > 0:
            return (self.ref_profit / selling_price) * 100
        elif selling_price == 0 and self.cost_price and self.cost_price > 0:
            # 当售价为0但有成本时，返回负无穷大表示亏损
            return float('-inf')
        return 0

    @property
    def unpaid_amount(self):
        """计算REF未付款金额"""
        if not self.selling_price:
            return 0

        # 使用辅助方法计算已确认的收款总额（包括项目级别收款记录的分配）
        from .receipt import ProjectReceipt  # 避免循环导入
        total_received = ProjectReceipt.get_ref_total_received(self.id, self.header_id)
        unpaid = float(self.selling_price) - total_received
        return max(0, unpaid)  # 确保不会返回负数

    # 机票相关计算属性
    @property
    def total_flight_selling_price(self):
        """计算机票总售价"""
        from ...flight.models.flight import ProjectFlightPassenger  # 避免循环导入
        passengers = ProjectFlightPassenger.query.filter_by(ref_id=self.id).all()
        return sum(p.selling_price or 0 for p in passengers)

    @property
    def total_flight_cost_price(self):
        """计算机票总成本"""
        from ...flight.models.flight import ProjectFlightPassenger  # 避免循环导入
        passengers = ProjectFlightPassenger.query.filter_by(ref_id=self.id).all()
        return sum(p.cost_price or 0 for p in passengers)

    @property
    def flight_profit(self):
        """计算机票利润"""
        return self.total_flight_selling_price - self.total_flight_cost_price

    @property
    def flight_passengers(self):
        """获取机票乘客信息"""
        from ...flight.models.flight import ProjectFlightPassenger  # 避免循环导入
        return ProjectFlightPassenger.query.filter_by(ref_id=self.id).all()

    @property
    def flight_segments(self):
        """获取机票航段信息"""
        from ...flight.models.flight import ProjectFlightSegment  # 避免循环导入
        return ProjectFlightSegment.query.filter_by(ref_id=self.id).all()

    @property
    def has_received_payment(self):
        """检查REF是否有收款记录（包括直接关联和项目级别分配）"""
        from .receipt import ProjectReceipt  # 避免循环导入
        total_received = ProjectReceipt.get_ref_total_received(self.id, self.header_id)
        return total_received > 0

    @property
    def can_delete(self):
        """检查REF是否可以删除（没有有效EO且没有收款）"""
        # 如果没有EO，或者EO已作废，且没有收款记录，则可以删除
        has_valid_eo = self.eos and self.eos.status != 'void'
        return not has_valid_eo and not self.has_received_payment

    def get_invoices(self):
        """获取与此REF关联的发票列表"""
        from .invoice import ProjectInvoice
        import json
        
        # 查询所有包含此REF ID的发票
        invoices = ProjectInvoice.query.filter(
            ProjectInvoice.header_id == self.header_id,
            ProjectInvoice.status != 'cancelled'
        ).all()
        
        result = []
        for inv in invoices:
            if inv.ref_ids:
                try:
                    ref_id_list = json.loads(inv.ref_ids)
                    if self.id in ref_id_list or str(self.id) in ref_id_list:
                        result.append(inv)
                except (json.JSONDecodeError, TypeError):
                    pass
        return result

    @classmethod
    def generate_ref_number(cls, project_hid=None):
        """生成REF编号"""
        try:
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
        except Exception as e:
            # 如果数据库查询失败，返回默认编号
            print(f"Warning: Failed to generate REF number: {e}")
            return 'R01'


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
