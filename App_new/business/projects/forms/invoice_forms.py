# -*- coding: utf-8 -*-
"""Invoice表单 - 发票/账单表单"""

from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, DateField, TextAreaField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Optional, NumberRange, Email
from datetime import date


class ProjectInvoiceForm(FlaskForm):
    """项目发票表单"""
    
    # 发票基本信息
    invoice_date = DateField('发票日期', validators=[
        DataRequired(message='发票日期不能为空')
    ], default=date.today)
    
    due_date = DateField('到期日期', validators=[
        Optional()
    ])
    
    amount = DecimalField('发票金额', validators=[
        DataRequired(message='发票金额不能为空'),
        NumberRange(min=0.01, message='发票金额必须大于0')
    ], places=2)
    
    currency = SelectField('货币类型', choices=[
        ('SGD', 'SGD - 新加坡元'),
        ('USD', 'USD - 美元'),
        ('CNY', 'CNY - 人民币'),
        ('EUR', 'EUR - 欧元'),
        ('JPY', 'JPY - 日元')
    ], default='SGD', validators=[DataRequired(message='请选择货币类型')])
    
    invoice_type = SelectField('发票类型', choices=[
        ('full', '全额发票'),
        ('partial', '分期发票'),
        ('deposit', '定金发票'),
        ('final', '尾款发票')
    ], default='full', validators=[DataRequired(message='请选择发票类型')])
    
    # 客户信息
    customer_name = StringField('客户名称', validators=[
        Optional()
    ])
    
    customer_company = StringField('客户公司', validators=[
        Optional()
    ])
    
    customer_email = StringField('客户邮箱', validators=[
        Optional(),
        Email(message='请输入有效的邮箱地址')
    ])
    
    customer_phone = StringField('客户电话', validators=[
        Optional()
    ])
    
    customer_address = TextAreaField('客户地址', validators=[
        Optional()
    ])
    
    # 关联REF（动态生成）
    selected_refs = SelectMultipleField('关联REF', coerce=int, validators=[
        Optional()
    ])
    
    # 备注和条款
    remarks = TextAreaField('备注', validators=[
        Optional()
    ])
    
    terms = TextAreaField('付款条款', validators=[
        Optional()
    ])
    
    # 提交按钮
    submit = SubmitField('保存发票')


class InvoicePaymentForm(FlaskForm):
    """发票付款表单 - 记录发票的收款"""
    
    payment_amount = DecimalField('付款金额', validators=[
        DataRequired(message='付款金额不能为空'),
        NumberRange(min=0.01, message='付款金额必须大于0')
    ], places=2)
    
    payment_date = DateField('付款日期', validators=[
        DataRequired(message='付款日期不能为空')
    ], default=date.today)
    
    payment_method = SelectField('付款方式', choices=[
        ('bank_transfer', '银行转账'),
        ('cash', '现金'),
        ('credit_card', '信用卡'),
        ('cheque', '支票'),
        ('other', '其他')
    ], default='bank_transfer', validators=[DataRequired(message='请选择付款方式')])
    
    transaction_id = StringField('交易流水号', validators=[
        Optional()
    ])
    
    remarks = TextAreaField('备注', validators=[
        Optional()
    ])
    
    submit = SubmitField('确认收款')


class InvoiceItemForm(FlaskForm):
    """发票明细项表单"""
    
    description = StringField('项目描述', validators=[
        DataRequired(message='项目描述不能为空')
    ])
    
    quantity = DecimalField('数量', validators=[
        DataRequired(message='数量不能为空'),
        NumberRange(min=1, message='数量必须大于0')
    ], default=1)
    
    unit_price = DecimalField('单价', validators=[
        DataRequired(message='单价不能为空'),
        NumberRange(min=0, message='单价不能为负')
    ], places=2)
    
    remarks = TextAreaField('备注', validators=[
        Optional()
    ])

