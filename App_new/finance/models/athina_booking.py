# -*- coding: utf-8 -*-
"""
Athina 账单相关模型
用于存储 Reservation Listing Report 数据
"""

from App_new.exts import db
from datetime import datetime


class AthinaBookingHeader(db.Model):
    """Athina 预订头部信息 - 包含汇总数据"""
    __tablename__ = 'athina_booking_headers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_header_id = db.Column(db.String(50), unique=True, nullable=False, comment='预订头部ID')
    corporate_name = db.Column(db.String(200), nullable=True, comment='公司名称')
    book_date = db.Column(db.Date, nullable=True, comment='预订日期')
    
    # 汇总财务数据
    sub_total_gross = db.Column(db.Numeric(15, 2), nullable=True, comment='小计总金额')
    sub_total_cost = db.Column(db.Numeric(15, 2), nullable=True, comment='小计成本')
    sub_total_pl = db.Column(db.Numeric(15, 2), nullable=True, comment='小计盈亏')
    sub_total_balance = db.Column(db.Numeric(15, 2), nullable=True, comment='小计余额')
    sub_total_tax = db.Column(db.Numeric(15, 2), nullable=True, comment='小计税额')
    sub_total_discount = db.Column(db.Numeric(15, 2), nullable=True, comment='小计折扣')
    sub_total_local_gross = db.Column(db.Numeric(15, 2), nullable=True, comment='小计本地总金额')
    sub_total_margin = db.Column(db.Numeric(5, 2), nullable=True, comment='小计利润率')
    
    # 利润分配
    operator_profit = db.Column(db.Numeric(15, 2), nullable=True, comment='分给操作员的利润')
    sales_profit = db.Column(db.Numeric(15, 2), nullable=True, comment='分给业务员的利润')
    company_profit = db.Column(db.Numeric(15, 2), nullable=True, comment='分给公司的利润')
    order_type = db.Column(db.String(50), nullable=True, comment='订单类型（小单/小单-中单过渡/中单/中单-大单过渡/大单）')
    
    # 顾问和发票信息
    consultant = db.Column(db.String(200), nullable=True, comment='顾问')
    sales_consultant = db.Column(db.String(200), nullable=True, comment='销售顾问')
    is_all_invoiced = db.Column(db.Boolean, default=False, comment='是否全部已开票（该HEADER下所有booking_ref都有invoice_no）')
    is_count_performance = db.Column(db.Boolean, default=False, comment='是否已核算业绩')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联的明细记录
    details = db.relationship('AthinaBookingDetail', backref='header', lazy='dynamic', cascade='all, delete-orphan')
    
    def update_invoice_status(self):
        """更新是否全部已开票状态
        判断该HEADER下每个唯一的 booking_ref 是否至少有一个 detail 有 invoice_no
        """
        # 获取该HEADER下所有非小计的明细记录
        non_subtotal_details = self.details.filter_by(is_subtotal=False).all()
        
        if not non_subtotal_details:
            # 如果没有明细记录，设为 False
            self.is_all_invoiced = False
            return
        
        # 获取所有唯一的 booking_ref（排除 None）
        unique_booking_refs = set()
        for detail in non_subtotal_details:
            if detail.booking_ref:
                unique_booking_refs.add(detail.booking_ref)
        
        if not unique_booking_refs:
            # 如果没有任何 booking_ref，设为 False
            self.is_all_invoiced = False
            return
        
        # 检查每个唯一的 booking_ref 是否至少有一个 detail 有 invoice_no
        all_invoiced = True
        for booking_ref in unique_booking_refs:
            # 查找该 booking_ref 下是否有任何 detail 有 invoice_no
            ref_details = [d for d in non_subtotal_details if d.booking_ref == booking_ref]
            has_invoice = any(detail.invoice_no for detail in ref_details)
            
            if not has_invoice:
                all_invoiced = False
                break
        
        self.is_all_invoiced = all_invoiced
    
    @property
    def invoice_no(self):
        """获取第一个有 invoice_no 的 detail 的 invoice_no（用于兼容性）"""
        detail_with_invoice = self.details.filter(
            AthinaBookingDetail.invoice_no.isnot(None),
            AthinaBookingDetail.invoice_no != ''
        ).filter_by(is_subtotal=False).first()
        
        return detail_with_invoice.invoice_no if detail_with_invoice else None
    
    @property
    def invoice_date(self):
        """获取第一个有 invoice_date 的 detail 的 invoice_date（用于兼容性）"""
        detail_with_invoice = self.details.filter(
            AthinaBookingDetail.invoice_date.isnot(None)
        ).filter_by(is_subtotal=False).first()
        
        return detail_with_invoice.invoice_date if detail_with_invoice else None


class AthinaBookingDetail(db.Model):
    """Athina 预订明细信息 - 包含所有业务和财务数据"""
    __tablename__ = 'athina_booking_details'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    header_id = db.Column(db.Integer, db.ForeignKey('athina_booking_headers.id'), nullable=False, comment='头部ID')
    
    # 业务信息
    corporate_name = db.Column(db.String(200), nullable=True, comment='公司名称')
    client_name = db.Column(db.String(200), nullable=True, comment='客户名称')
    booking_ref = db.Column(db.Integer, nullable=True, unique=True, comment='预订参考号')
    book_type = db.Column(db.String(50), nullable=True, comment='预订类型')
    book_date = db.Column(db.Date, nullable=True, comment='预订日期')
    dep_date = db.Column(db.Date, nullable=True, comment='出发日期')
    itin_desc = db.Column(db.Text, nullable=True, comment='行程描述')
    
    # 财务信息
    gross_curr = db.Column(db.String(10), nullable=True, comment='总金额货币')
    gross_amount = db.Column(db.Numeric(15, 2), nullable=True, comment='总金额')
    gross_tax = db.Column(db.Numeric(15, 2), nullable=True, comment='总税额')
    discount = db.Column(db.Numeric(15, 2), nullable=True, comment='折扣')
    local_gross = db.Column(db.Numeric(15, 2), nullable=True, comment='本地总金额')
    local_cost = db.Column(db.Numeric(15, 2), nullable=True, comment='本地成本')
    profit_loss = db.Column(db.Numeric(15, 2), nullable=True, comment='盈亏')
    margin = db.Column(db.Numeric(5, 2), nullable=True, comment='利润率')
    balance = db.Column(db.Numeric(15, 2), nullable=True, comment='余额')
    
    # 供应商信息
    supplier = db.Column(db.String(200), nullable=True, comment='供应商')
    consultant = db.Column(db.String(200), nullable=True, comment='顾问')
    sales_consultant = db.Column(db.String(200), nullable=True, comment='销售顾问')
    
    # 发票信息
    invoice_no = db.Column(db.String(100), nullable=True, comment='发票号')
    invoice_date = db.Column(db.Date, nullable=True, comment='发票日期')
    
    # 特殊标记
    is_subtotal = db.Column(db.Boolean, default=False, comment='是否为小计行')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
