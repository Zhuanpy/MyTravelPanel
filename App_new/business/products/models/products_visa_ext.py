# -*- coding: utf-8 -*-
"""
签证产品扩展表
存储签证特有的属性，整合现有 VisaTypes 表
"""

from datetime import datetime
from App_new.exts import db


class VisaCategory:
    """签证类别"""
    TOURIST = 'tourist'         # 旅游签证
    BUSINESS = 'business'       # 商务签证
    STUDENT = 'student'         # 学生签证
    WORK = 'work'               # 工作签证
    TRANSIT = 'transit'         # 过境签证
    FAMILY = 'family'           # 探亲签证
    MEDICAL = 'medical'         # 医疗签证

    CHOICES = [
        (TOURIST, '旅游签证'),
        (BUSINESS, '商务签证'),
        (STUDENT, '学生签证'),
        (WORK, '工作签证'),
        (TRANSIT, '过境签证'),
        (FAMILY, '探亲签证'),
        (MEDICAL, '医疗签证'),
    ]


class VisaEntryType:
    """入境类型"""
    SINGLE = 'single'           # 单次入境
    DOUBLE = 'double'           # 两次入境
    MULTIPLE = 'multiple'       # 多次入境

    CHOICES = [
        (SINGLE, '单次入境'),
        (DOUBLE, '两次入境'),
        (MULTIPLE, '多次入境'),
    ]


class ProductsVisaExt(db.Model):
    """
    签证产品扩展表
    存储签证类产品的特有属性
    """
    __tablename__ = 'products_visa_ext'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 关联主表 ==========
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, unique=True, comment='关联产品ID')

    # ========== 关联现有签证表（可选，用于数据迁移）==========
    visa_type_id = db.Column(db.Integer, db.ForeignKey('visa_types.id'),
                             nullable=True, comment='关联原签证类型ID')
    country_id = db.Column(db.Integer, db.ForeignKey('visa_countries.id'),
                           nullable=True, comment='关联签证国家ID')

    # ========== 签证基本信息 ==========
    visa_category = db.Column(db.String(30), comment='签证类别：tourist/business/student/work/transit/family/medical')
    visa_name = db.Column(db.String(100), comment='签证名称')
    visa_name_en = db.Column(db.String(100), comment='签证英文名')

    # ========== 目的地信息 ==========
    destination_country = db.Column(db.String(100), comment='目的地国家')
    destination_country_en = db.Column(db.String(100), comment='目的地国家英文')
    destination_country_code = db.Column(db.String(10), comment='目的地国家代码')
    embassy_location = db.Column(db.String(100), comment='使馆所在地')

    # ========== 申请人要求 ==========
    applicant_nationality = db.Column(db.Text, comment='适用国籍JSON数组')
    applicant_residence = db.Column(db.String(100), comment='申请人居住地要求')
    applicable_identities = db.Column(db.Text, comment='适用身份JSON数组')
    age_requirement = db.Column(db.String(100), comment='年龄要求')

    # ========== 签证有效期 ==========
    entry_type = db.Column(db.String(20), comment='入境类型：single/double/multiple')
    validity_days = db.Column(db.Integer, comment='签证有效期（天）')
    validity_months = db.Column(db.Integer, comment='签证有效期（月）')
    stay_days = db.Column(db.Integer, comment='每次停留天数')
    max_stay_days = db.Column(db.Integer, comment='最长停留天数')

    # ========== 办理时间 ==========
    processing_time = db.Column(db.String(100), comment='办理时间')
    processing_days_min = db.Column(db.Integer, comment='最短办理天数')
    processing_days_max = db.Column(db.Integer, comment='最长办理天数')
    express_available = db.Column(db.Boolean, default=False, comment='是否可加急')
    express_processing_days = db.Column(db.Integer, comment='加急办理天数')
    express_fee = db.Column(db.Numeric(10, 2), comment='加急费用')

    # ========== 费用信息 ==========
    visa_fee = db.Column(db.Numeric(10, 2), comment='签证费')
    service_fee = db.Column(db.Numeric(10, 2), comment='服务费')
    total_fee = db.Column(db.Numeric(10, 2), comment='总费用')
    fee_currency = db.Column(db.String(10), default='SGD', comment='费用币种')
    fee_includes = db.Column(db.Text, comment='费用包含说明')
    fee_excludes = db.Column(db.Text, comment='费用不含说明')

    # ========== 所需材料 ==========
    required_documents = db.Column(db.Text, comment='所需材料JSON')
    document_requirements = db.Column(db.Text, comment='材料要求说明')
    photo_requirements = db.Column(db.Text, comment='照片要求')
    passport_requirements = db.Column(db.Text, comment='护照要求')
    financial_proof = db.Column(db.Text, comment='财务证明要求')
    invitation_required = db.Column(db.Boolean, default=False, comment='是否需要邀请函')
    hotel_booking_required = db.Column(db.Boolean, default=False, comment='是否需要酒店预订')
    flight_booking_required = db.Column(db.Boolean, default=False, comment='是否需要机票预订')
    insurance_required = db.Column(db.Boolean, default=False, comment='是否需要保险')

    # ========== 面试信息 ==========
    interview_required = db.Column(db.Boolean, default=False, comment='是否需要面试')
    interview_location = db.Column(db.String(200), comment='面试地点')
    interview_tips = db.Column(db.Text, comment='面试注意事项')

    # ========== 办理方式 ==========
    can_mail_apply = db.Column(db.Boolean, default=True, comment='是否支持邮寄办理')
    can_online_apply = db.Column(db.Boolean, default=False, comment='是否支持在线办理')
    in_person_required = db.Column(db.Boolean, default=False, comment='是否需要本人递交')
    biometrics_required = db.Column(db.Boolean, default=False, comment='是否需要采集指纹')

    # ========== 出签方式 ==========
    visa_on_passport = db.Column(db.Boolean, default=True, comment='是否贴签')
    e_visa_available = db.Column(db.Boolean, default=False, comment='是否电子签')
    visa_sticker_type = db.Column(db.String(50), comment='签证贴纸类型')

    # ========== 注意事项 ==========
    important_notes = db.Column(db.Text, comment='重要提示')
    application_tips = db.Column(db.Text, comment='申请攻略')
    rejection_reasons = db.Column(db.Text, comment='常见拒签原因')
    success_rate = db.Column(db.String(50), comment='出签率说明')

    # ========== 相关链接 ==========
    embassy_website = db.Column(db.String(500), comment='使馆官网')
    application_form_url = db.Column(db.String(500), comment='申请表下载链接')
    tracking_url = db.Column(db.String(500), comment='进度查询链接')
    related_links = db.Column(db.Text, comment='相关链接JSON')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # ========== 关联关系 ==========
    product = db.relationship('ProductsUnified', backref=db.backref('visa_ext', uselist=False, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<ProductsVisaExt {self.id}: {self.visa_name}>'

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'product_id': self.product_id,
            'visa_type_id': self.visa_type_id,
            'country_id': self.country_id,
            'visa_category': self.visa_category,
            'visa_name': self.visa_name,
            'visa_name_en': self.visa_name_en,
            'destination_country': self.destination_country,
            'destination_country_en': self.destination_country_en,
            'destination_country_code': self.destination_country_code,
            'entry_type': self.entry_type,
            'validity_days': self.validity_days,
            'validity_months': self.validity_months,
            'stay_days': self.stay_days,
            'processing_time': self.processing_time,
            'processing_days_min': self.processing_days_min,
            'processing_days_max': self.processing_days_max,
            'express_available': self.express_available,
            'visa_fee': float(self.visa_fee) if self.visa_fee else None,
            'service_fee': float(self.service_fee) if self.service_fee else None,
            'total_fee': float(self.total_fee) if self.total_fee else None,
            'required_documents': json.loads(self.required_documents) if self.required_documents else None,
            'interview_required': self.interview_required,
            'can_mail_apply': self.can_mail_apply,
            'can_online_apply': self.can_online_apply,
            'e_visa_available': self.e_visa_available,
            'important_notes': self.important_notes,
            'embassy_website': self.embassy_website,
        }

    @property
    def processing_time_display(self):
        """获取办理时间显示"""
        if self.processing_time:
            return self.processing_time
        if self.processing_days_min and self.processing_days_max:
            if self.processing_days_min == self.processing_days_max:
                return f"{self.processing_days_min}个工作日"
            return f"{self.processing_days_min}-{self.processing_days_max}个工作日"
        elif self.processing_days_min:
            return f"{self.processing_days_min}个工作日起"
        return "请咨询"

    @property
    def validity_display(self):
        """获取有效期显示"""
        if self.validity_months:
            return f"{self.validity_months}个月"
        elif self.validity_days:
            return f"{self.validity_days}天"
        return "请咨询"

    @classmethod
    def create_from_visa_type(cls, product_id, visa_type):
        """
        从现有 VisaTypes 记录创建扩展表记录

        Args:
            product_id: 统一产品ID
            visa_type: VisaTypes 对象

        Returns:
            ProductsVisaExt 对象
        """
        ext = cls(
            product_id=product_id,
            visa_type_id=visa_type.id,
            country_id=visa_type.country_id,
            visa_name=visa_type.visa_type,
            destination_country=visa_type.country.country_name_CN if visa_type.country else None,
            destination_country_en=visa_type.country.country_name_EN if visa_type.country else None,
            destination_country_code=visa_type.country.country_code if visa_type.country else None,
            processing_time=visa_type.processing_time,
            important_notes=visa_type.introduction,
        )

        # 解析费用
        try:
            fee_str = visa_type.fee
            if fee_str:
                # 尝试提取数字
                import re
                numbers = re.findall(r'[\d.]+', fee_str)
                if numbers:
                    ext.total_fee = float(numbers[0])
        except (ValueError, TypeError):
            pass

        return ext
