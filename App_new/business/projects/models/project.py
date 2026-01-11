# -*- coding: utf-8 -*-
"""项目核心模型 - 客户和项目主表相关"""

from App_new.exts import db
from datetime import datetime


class CustomerCompany(db.Model):
    """公司模型 - 统一管理客户和供应商"""
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
    click_count = db.Column(db.Integer, default=0, comment='点击次数')
    last_clicked_at = db.Column(db.DateTime, nullable=True, comment='最后点击时间')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')
    legal_person = db.Column(db.String(100))

    # 集团/关联标签（用于标识同一集团下的多个公司，如 BAONENG, ALIBABA 等）
    group_name = db.Column(db.String(100), nullable=True, comment='集团/关联标签')

    # ========== 公司角色标识 ==========
    is_customer = db.Column(db.Boolean, default=True, nullable=False, comment='是否为客户')
    is_supplier = db.Column(db.Boolean, default=False, nullable=False, comment='是否为供应商')

    # ========== 供应商专属字段 ==========
    supplier_type_id = db.Column(db.Integer, db.ForeignKey('business_types.id'), nullable=True, comment='供应商类型ID')
    country = db.Column(db.String(50), nullable=True, comment='国家')
    city = db.Column(db.String(50), nullable=True, comment='城市')
    region = db.Column(db.String(50), nullable=True, comment='地区')

    # 关联项目
    projects = db.relationship('ProjectHeader', backref='company', lazy='dynamic')
    # 供应商类型关联
    supplier_type = db.relationship('BusinessType', foreign_keys=[supplier_type_id])

    def __repr__(self):
        return f'<CustomerCompany {self.company_name}>'
    
    def increment_click_count(self):
        """增加点击次数"""
        self.click_count = (self.click_count or 0) + 1
        self.last_clicked_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    @property
    def supplier_type_display(self):
        """获取供应商类型的显示名称"""
        if self.supplier_type:
            return self.supplier_type.name
        return None

    @property
    def role_display(self):
        """获取公司角色显示"""
        roles = []
        if self.is_customer:
            roles.append('客户')
        if self.is_supplier:
            roles.append('供应商')
        return ' / '.join(roles) if roles else '未设置'

    @property
    def name(self):
        """向后兼容：返回公司名称（原 Supplier.name）"""
        return self.company_name

    @property
    def name_en(self):
        """向后兼容：返回公司名称（英文）"""
        return self.company_name

    @property
    def phone(self):
        """向后兼容：返回联系电话（原 Supplier.phone）"""
        return self.contact_phone

    @property
    def email(self):
        """向后兼容：返回联系邮箱（原 Supplier.email）"""
        return self.contact_email

    @property
    def notes(self):
        """向后兼容：返回备注（原 Supplier.notes）"""
        return self.remarks

    @property
    def supplier_type_code(self):
        """获取供应商类型代码"""
        if self.supplier_type:
            return self.supplier_type.code
        return None

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
            'click_count': self.click_count,
            'last_clicked_at': self.last_clicked_at.isoformat() if self.last_clicked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'group_name': self.group_name,
            # 新增字段
            'is_customer': self.is_customer,
            'is_supplier': self.is_supplier,
            'supplier_type_id': self.supplier_type_id,
            'supplier_type_display': self.supplier_type_display,
            'country': self.country,
            'city': self.city,
            'region': self.region,
            'role_display': self.role_display
        }


class CompanyContact(db.Model):
    """公司联系人模型"""
    __tablename__ = 'company_contacts'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id', ondelete='CASCADE'), nullable=False, comment='公司ID')
    name = db.Column(db.String(100), nullable=False, comment='联系人姓名')
    position = db.Column(db.String(100), nullable=True, comment='职位')
    phone = db.Column(db.String(50), nullable=True, comment='电话')
    email = db.Column(db.String(100), nullable=True, comment='邮箱')
    wechat = db.Column(db.String(50), nullable=True, comment='微信')
    is_primary = db.Column(db.Boolean, default=False, comment='是否主要联系人')
    remarks = db.Column(db.Text, nullable=True, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    company = db.relationship('CustomerCompany', backref=db.backref('contacts', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<CompanyContact {self.name}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'position': self.position,
            'phone': self.phone,
            'email': self.email,
            'wechat': self.wechat,
            'is_primary': self.is_primary,
            'remarks': self.remarks,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None
        }


class CompanyFile(db.Model):
    """公司文件/附件模型"""
    __tablename__ = 'company_files'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_id = db.Column(db.Integer, db.ForeignKey('customer_companies.id', ondelete='CASCADE'), nullable=False, comment='公司ID')
    filename = db.Column(db.String(255), nullable=False, comment='原始文件名')
    stored_filename = db.Column(db.String(255), nullable=False, comment='存储文件名')
    file_path = db.Column(db.String(500), nullable=False, comment='文件存储路径')
    file_size = db.Column(db.Integer, nullable=True, comment='文件大小（字节）')
    file_type = db.Column(db.String(100), nullable=True, comment='文件类型/MIME类型')
    description = db.Column(db.String(500), nullable=True, comment='文件描述')
    uploaded_by = db.Column(db.String(100), nullable=True, comment='上传人')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='上传时间')

    # 关联关系
    company = db.relationship('CustomerCompany', backref=db.backref('files', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<CompanyFile {self.filename}>'

    @property
    def file_size_display(self):
        """格式化显示文件大小"""
        if not self.file_size:
            return '未知'
        if self.file_size < 1024:
            return f'{self.file_size} B'
        elif self.file_size < 1024 * 1024:
            return f'{self.file_size / 1024:.1f} KB'
        else:
            return f'{self.file_size / (1024 * 1024):.1f} MB'

    @property
    def file_extension(self):
        """获取文件扩展名"""
        import os
        _, ext = os.path.splitext(self.filename)
        return ext.lower() if ext else ''

    @property
    def icon_class(self):
        """根据文件类型返回图标类名"""
        ext = self.file_extension
        if ext in ['.pdf']:
            return 'fa-file-pdf'
        elif ext in ['.doc', '.docx']:
            return 'fa-file-word'
        elif ext in ['.xls', '.xlsx']:
            return 'fa-file-excel'
        elif ext in ['.ppt', '.pptx']:
            return 'fa-file-powerpoint'
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return 'fa-file-image'
        elif ext in ['.zip', '.rar', '.7z']:
            return 'fa-file-archive'
        else:
            return 'fa-file'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'filename': self.filename,
            'stored_filename': self.stored_filename,
            'file_size': self.file_size,
            'file_size_display': self.file_size_display,
            'file_type': self.file_type,
            'file_extension': self.file_extension,
            'icon_class': self.icon_class,
            'description': self.description,
            'uploaded_by': self.uploaded_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
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

    # 结算相关字段
    is_settled = db.Column(db.Boolean, default=False, nullable=False, comment='是否已结算')
    settled_at = db.Column(db.DateTime, nullable=True, comment='结算时间')
    settled_by = db.Column(db.String(50), nullable=True, comment='结算人')
    payment_voucher_id = db.Column(db.Integer, db.ForeignKey('payment_vouchers.id'), nullable=True, comment='付款凭证ID')

    # 利润分配字段
    order_type = db.Column(db.String(20), nullable=True, comment='订单类型(小单/中单/大单等)')
    operator_profit = db.Column(db.Numeric(12, 2), nullable=True, comment='操作员利润')
    sales_profit = db.Column(db.Numeric(12, 2), nullable=True, comment='业务员利润')
    company_profit = db.Column(db.Numeric(12, 2), nullable=True, comment='公司利润')

    # 操作员和业务员字段（利润分配关联人员，支持多选，逗号分隔）
    operator_ids = db.Column(db.String(200), nullable=True, comment='操作员ID列表(逗号分隔)')
    operator_names = db.Column(db.String(500), nullable=True, comment='操作员姓名列表(逗号分隔)')
    salesperson_ids = db.Column(db.String(200), nullable=True, comment='业务员ID列表(逗号分隔)')
    salesperson_names = db.Column(db.String(500), nullable=True, comment='业务员姓名列表(逗号分隔)')

    # 关联REF明细
    refs = db.relationship('ProjectRef', backref='header', cascade='all, delete-orphan')
    
    # 关联项目人员
    members = db.relationship('ProjectMember', backref='project', cascade='all, delete-orphan', lazy='dynamic')
    
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
            'remarks': self.remarks,
            'is_settled': self.is_settled,
            'settled_at': self.settled_at.isoformat() if self.settled_at else None,
            'settled_by': self.settled_by,
            'payment_voucher_id': self.payment_voucher_id,
            'voucher_no': self.payment_voucher.voucher_no if self.payment_voucher else None,
            'order_type': self.order_type,
            'operator_profit': float(self.operator_profit) if self.operator_profit else None,
            'sales_profit': float(self.sales_profit) if self.sales_profit else None,
            'company_profit': float(self.company_profit) if self.company_profit else None,
            'operator_ids': self.operator_ids,
            'operator_names': self.operator_names,
            'salesperson_ids': self.salesperson_ids,
            'salesperson_names': self.salesperson_names
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


class EmailTemplate(db.Model):
    """邮件模板模型"""
    __tablename__ = 'email_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='模板名称')
    subject = db.Column(db.String(255), nullable=False, comment='邮件主题')
    body = db.Column(db.Text, nullable=False, comment='邮件正文（支持HTML和变量替换）')
    category = db.Column(db.String(50), nullable=True, comment='分类：flight/hotel/visa/invoice等')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='创建人')

    def __repr__(self):
        return f'<EmailTemplate {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject,
            'body': self.body,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }


class ProjectEmail(db.Model):
    """项目邮件发送记录"""
    __tablename__ = 'project_emails'

    id = db.Column(db.Integer, primary_key=True)
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id', ondelete='CASCADE'), nullable=False, comment='项目ID')
    template_id = db.Column(db.Integer, db.ForeignKey('email_templates.id', ondelete='SET NULL'), nullable=True, comment='使用的模板ID')
    subject = db.Column(db.String(255), nullable=False, comment='邮件主题')
    body = db.Column(db.Text, nullable=False, comment='邮件正文')
    recipients = db.Column(db.Text, nullable=False, comment='收件人（JSON格式）')
    cc = db.Column(db.Text, nullable=True, comment='抄送人（JSON格式）')
    attachments = db.Column(db.Text, nullable=True, comment='附件列表（JSON格式）')
    status = db.Column(db.Enum('draft', 'sent', 'failed'), default='draft', comment='状态')
    sent_at = db.Column(db.DateTime, nullable=True, comment='发送时间')
    error_message = db.Column(db.Text, nullable=True, comment='错误信息')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=True, comment='发送人')

    # 关联关系
    header = db.relationship('ProjectHeader', backref=db.backref('emails', lazy='dynamic'))
    template = db.relationship('EmailTemplate', backref=db.backref('emails', lazy='dynamic'))

    def __repr__(self):
        return f'<ProjectEmail {self.id} - {self.subject}>'

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'header_id': self.header_id,
            'template_id': self.template_id,
            'subject': self.subject,
            'body': self.body,
            'recipients': json.loads(self.recipients) if self.recipients else [],
            'cc': json.loads(self.cc) if self.cc else [],
            'attachments': json.loads(self.attachments) if self.attachments else [],
            'status': self.status,
            'sent_at': self.sent_at.strftime('%Y-%m-%d %H:%M') if self.sent_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'created_by': self.created_by
        }
