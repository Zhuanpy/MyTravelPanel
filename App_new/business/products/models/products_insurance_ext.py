# -*- coding: utf-8 -*-
"""
保险产品扩展表
存储保险特有的属性
"""

from datetime import datetime
from App_new.exts import db


class InsuranceType:
    """保险类型"""
    TRAVEL = 'travel'           # 旅行险
    ACCIDENT = 'accident'       # 意外险
    MEDICAL = 'medical'         # 医疗险
    FLIGHT = 'flight'           # 航空险
    CANCEL = 'cancel'           # 取消险

    CHOICES = [
        (TRAVEL, '旅行险'),
        (ACCIDENT, '意外险'),
        (MEDICAL, '医疗险'),
        (FLIGHT, '航空险'),
        (CANCEL, '取消险'),
    ]


class CoverageRegion:
    """保障地区"""
    DOMESTIC = 'domestic'       # 国内
    ASIA = 'asia'               # 亚洲
    GLOBAL = 'global'           # 全球
    GLOBAL_EX_US = 'global_ex_us'  # 全球除美加

    CHOICES = [
        (DOMESTIC, '国内'),
        (ASIA, '亚洲'),
        (GLOBAL, '全球'),
        (GLOBAL_EX_US, '全球（除美加）'),
    ]


class ProductsInsuranceExt(db.Model):
    """
    保险产品扩展表
    存储保险类产品的特有属性
    """
    __tablename__ = 'products_insurance_ext'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ========== 关联主表 ==========
    product_id = db.Column(db.Integer, db.ForeignKey('products_unified.id'),
                           nullable=False, unique=True, comment='关联产品ID')

    # ========== 保险公司信息 ==========
    insurance_company = db.Column(db.String(100), comment='保险公司')
    insurance_company_en = db.Column(db.String(100), comment='保险公司英文名')
    underwriter = db.Column(db.String(100), comment='承保公司')
    policy_number_prefix = db.Column(db.String(50), comment='保单号前缀')

    # ========== 保险类型 ==========
    insurance_type = db.Column(db.String(30), comment='保险类型：travel/accident/medical/flight/cancel')
    plan_name = db.Column(db.String(100), comment='计划名称')
    plan_level = db.Column(db.String(50), comment='计划等级：基础/标准/豪华')

    # ========== 保障范围 ==========
    coverage_region = db.Column(db.String(30), comment='保障地区：domestic/asia/global/global_ex_us')
    coverage_countries = db.Column(db.Text, comment='保障国家JSON数组')
    excluded_countries = db.Column(db.Text, comment='排除国家JSON数组')

    # ========== 保障期限 ==========
    coverage_days = db.Column(db.Integer, comment='保障天数')
    min_coverage_days = db.Column(db.Integer, comment='最少保障天数')
    max_coverage_days = db.Column(db.Integer, comment='最多保障天数')
    effective_rule = db.Column(db.String(100), comment='生效规则：即时生效/次日生效/指定日期')
    effective_delay_hours = db.Column(db.Integer, comment='生效延迟小时数')

    # ========== 适用人群 ==========
    applicable_age_min = db.Column(db.Integer, comment='适用最小年龄')
    applicable_age_max = db.Column(db.Integer, comment='适用最大年龄')
    applicable_nationality = db.Column(db.Text, comment='适用国籍JSON数组')
    excluded_nationality = db.Column(db.Text, comment='排除国籍JSON数组')
    pre_existing_conditions = db.Column(db.Boolean, default=False, comment='是否承保既往病症')

    # ========== 保障项目 ==========
    coverage_items = db.Column(db.Text, comment='保障项目JSON')
    # 常见保障项目
    medical_expense = db.Column(db.Numeric(12, 2), comment='医疗费用保额')
    accidental_death = db.Column(db.Numeric(12, 2), comment='意外身故保额')
    permanent_disability = db.Column(db.Numeric(12, 2), comment='永久残疾保额')
    trip_cancellation = db.Column(db.Numeric(12, 2), comment='旅程取消保额')
    trip_delay = db.Column(db.Numeric(12, 2), comment='旅程延误保额')
    baggage_loss = db.Column(db.Numeric(12, 2), comment='行李丢失保额')
    baggage_delay = db.Column(db.Numeric(12, 2), comment='行李延误保额')
    personal_liability = db.Column(db.Numeric(12, 2), comment='个人责任保额')
    emergency_evacuation = db.Column(db.Numeric(12, 2), comment='紧急撤离保额')
    flight_delay_hours = db.Column(db.Integer, comment='航班延误赔付门槛（小时）')
    baggage_delay_hours = db.Column(db.Integer, comment='行李延误赔付门槛（小时）')

    # ========== 免责条款 ==========
    exclusions = db.Column(db.Text, comment='免责条款')
    special_exclusions = db.Column(db.Text, comment='特别除外责任')
    high_risk_activities = db.Column(db.Text, comment='高风险活动说明')
    covers_adventure = db.Column(db.Boolean, default=False, comment='是否承保冒险活动')

    # ========== 理赔信息 ==========
    claim_process = db.Column(db.Text, comment='理赔流程')
    claim_documents = db.Column(db.Text, comment='理赔所需文件JSON')
    claim_hotline = db.Column(db.String(50), comment='理赔热线')
    claim_email = db.Column(db.String(100), comment='理赔邮箱')
    claim_deadline_days = db.Column(db.Integer, comment='理赔申请期限（天）')

    # ========== 服务热线 ==========
    emergency_hotline = db.Column(db.String(50), comment='紧急救援热线')
    customer_service = db.Column(db.String(50), comment='客服热线')
    service_hours = db.Column(db.String(100), comment='服务时间')

    # ========== 购买限制 ==========
    max_insured_amount = db.Column(db.Numeric(12, 2), comment='最高保额限制')
    min_premium = db.Column(db.Numeric(10, 2), comment='最低保费')
    max_purchase_count = db.Column(db.Integer, comment='单人最多购买份数')

    # ========== 文档链接 ==========
    policy_terms_url = db.Column(db.String(500), comment='保单条款链接')
    product_brochure_url = db.Column(db.String(500), comment='产品说明书链接')
    claim_form_url = db.Column(db.String(500), comment='理赔表格链接')

    # ========== 时间戳 ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # ========== 关联关系 ==========
    product = db.relationship('ProductsUnified', backref=db.backref('insurance_ext', uselist=False))

    def __repr__(self):
        return f'<ProductsInsuranceExt {self.id}: {self.plan_name}>'

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'product_id': self.product_id,
            'insurance_company': self.insurance_company,
            'insurance_type': self.insurance_type,
            'plan_name': self.plan_name,
            'plan_level': self.plan_level,
            'coverage_region': self.coverage_region,
            'coverage_days': self.coverage_days,
            'applicable_age_min': self.applicable_age_min,
            'applicable_age_max': self.applicable_age_max,
            'coverage_items': json.loads(self.coverage_items) if self.coverage_items else None,
            'medical_expense': float(self.medical_expense) if self.medical_expense else None,
            'accidental_death': float(self.accidental_death) if self.accidental_death else None,
            'trip_cancellation': float(self.trip_cancellation) if self.trip_cancellation else None,
            'trip_delay': float(self.trip_delay) if self.trip_delay else None,
            'baggage_loss': float(self.baggage_loss) if self.baggage_loss else None,
            'emergency_evacuation': float(self.emergency_evacuation) if self.emergency_evacuation else None,
            'exclusions': self.exclusions,
            'claim_process': self.claim_process,
            'emergency_hotline': self.emergency_hotline,
            'effective_rule': self.effective_rule,
        }

    @property
    def coverage_summary(self):
        """获取保障摘要"""
        items = []
        if self.medical_expense:
            items.append(f"医疗费用: ${self.medical_expense:,.0f}")
        if self.accidental_death:
            items.append(f"意外身故: ${self.accidental_death:,.0f}")
        if self.trip_cancellation:
            items.append(f"旅程取消: ${self.trip_cancellation:,.0f}")
        if self.baggage_loss:
            items.append(f"行李丢失: ${self.baggage_loss:,.0f}")
        return items
