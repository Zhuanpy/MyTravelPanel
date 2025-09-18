# -*- coding: utf-8 -*-
"""项目核心模型 - 客户和项目主表相关"""

from App_new.exts import db
from datetime import datetime


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
    legal_person = db.Column(db.String(100))

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
    # 提醒相关字段
    reminder_event = db.Column(db.String(200), comment='提醒事件描述')
    reminder_date = db.Column(db.DateTime, comment='提醒日期')
    reminder_sent = db.Column(db.Boolean, default=False, comment='是否已发送提醒邮件')

    # 关联REF明细
    refs = db.relationship('ProjectRef', backref='header', cascade='all, delete-orphan')
    
    # 注意：CustomerCompany模型中已经定义了 backref='company'，这里不需要重复定义

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

        try:
            # 查找最后一个HID编号 - 使用更简单的方法
            last_headers = cls.query.filter(
                cls.hid.like('H%')
            ).all()
            
            if last_headers:
                # 提取所有数字部分并找到最大值
                max_number = 0
                for header in last_headers:
                    try:
                        if header.hid and header.hid.startswith('H'):
                            number_part = header.hid[1:]  # 去掉'H'前缀
                            if number_part.isdigit():
                                number = int(number_part)
                                if number > max_number:
                                    max_number = number
                    except (ValueError, AttributeError, IndexError):
                        continue
                
                new_number = max_number + 1
            else:
                new_number = 1
            
            return f'H{new_number}'
            
        except Exception as e:
            print(f"DEBUG: generate_hid 方法出错: {e}")
            # 如果出错，返回默认值
            return "H1"

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
        from .receipt import ProjectReceipt  # 避免循环导入
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
