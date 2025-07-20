from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, DateField, TextAreaField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import date

class ProjectReceiptForm(FlaskForm):
    """项目收款表单"""
    
    # 收款信息
    amount = DecimalField('收款金额', validators=[
        DataRequired(message='收款金额不能为空'),
        NumberRange(min=0.01, message='收款金额必须大于0')
    ], places=2)
    
    currency = SelectField('货币类型', choices=[
        ('SGD', 'SGD - 新加坡元'),
        ('USD', 'USD - 美元'),
        ('CNY', 'CNY - 人民币'),
        ('EUR', 'EUR - 欧元'),
        ('JPY', 'JPY - 日元')
    ], default='SGD', validators=[DataRequired(message='请选择货币类型')])
    
    payment_method = SelectField('付款方式', choices=[
        ('bank_transfer', '银行转账'),
        ('cash', '现金'),
        ('credit_card', '信用卡'),
        ('cheque', '支票'),
        ('other', '其他')
    ], default='bank_transfer', validators=[DataRequired(message='请选择付款方式')])
    
    payment_date = DateField('收款日期', validators=[
        DataRequired(message='收款日期不能为空')
    ], default=date.today)
    
    # 付款人信息
    payer_name = StringField('付款人姓名', validators=[
        Optional()
    ])
    
    payer_contact = StringField('付款人联系方式', validators=[
        Optional()
    ])
    
    payer_company = StringField('付款人公司', validators=[
        Optional()
    ])
    
    # 银行信息（可选）
    bank_name = StringField('银行名称', validators=[
        Optional()
    ])
    
    account_number = StringField('账号', validators=[
        Optional()
    ])
    
    transaction_id = StringField('交易流水号', validators=[
        Optional()
    ])
    
    # 备注
    remarks = TextAreaField('备注', validators=[
        Optional()
    ])
    
    # 提交按钮
    submit = SubmitField('保存收款记录')

class ProjectLevelReceiptForm(FlaskForm):
    """项目级别收款表单"""
    
    # 收款信息
    amount = DecimalField('收款金额', validators=[
        DataRequired(message='收款金额不能为空'),
        NumberRange(min=0.01, message='收款金额必须大于0')
    ], places=2)
    
    currency = SelectField('货币类型', choices=[
        ('SGD', 'SGD - 新加坡元'),
        ('USD', 'USD - 美元'),
        ('CNY', 'CNY - 人民币'),
        ('EUR', 'EUR - 欧元'),
        ('JPY', 'JPY - 日元')
    ], default='SGD', validators=[DataRequired(message='请选择货币类型')])
    
    payment_method = SelectField('付款方式', choices=[
        ('bank_transfer', '银行转账'),
        ('cash', '现金'),
        ('credit_card', '信用卡'),
        ('cheque', '支票'),
        ('other', '其他')
    ], default='bank_transfer', validators=[DataRequired(message='请选择付款方式')])
    
    payment_date = DateField('收款日期', validators=[
        DataRequired(message='收款日期不能为空')
    ], default=date.today)
    
    # 分配方式
    distribution_method = SelectField('分配方式', choices=[
        ('auto', '自动分配'),
        ('manual', '手动指定分配')
    ], default='auto', validators=[DataRequired(message='请选择分配方式')])
    
    # 手动分配REF选择（动态生成）
    selected_refs = SelectMultipleField('选择要分配的REF', coerce=int, validators=[
        Optional()
    ])
    
    # 付款人信息
    payer_name = StringField('付款人姓名', validators=[
        Optional()
    ])
    
    payer_contact = StringField('付款人联系方式', validators=[
        Optional()
    ])
    
    payer_company = StringField('付款人公司', validators=[
        Optional()
    ])
    
    # 银行信息（可选）
    bank_name = StringField('银行名称', validators=[
        Optional()
    ])
    
    account_number = StringField('账号', validators=[
        Optional()
    ])
    
    transaction_id = StringField('交易流水号', validators=[
        Optional()
    ])
    
    # 备注
    remarks = TextAreaField('备注', validators=[
        Optional()
    ])
    
    # 提交按钮
    submit = SubmitField('创建收款记录') 