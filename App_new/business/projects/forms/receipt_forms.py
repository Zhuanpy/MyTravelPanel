from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, DateField, TextAreaField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import date

class ProjectReceiptForm(FlaskForm):
    """项目收款表单"""

    # 关联发票（可选）
    invoice_id = SelectField('关联发票', coerce=int, validators=[
        Optional()
    ])

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
        ('wechat', 'WeChat'),
        ('other', '其他')
    ], default='bank_transfer', validators=[DataRequired(message='请选择付款方式')])
    
    payment_date = DateField('收款日期', validators=[
        DataRequired(message='收款日期不能为空')
    ], default=date.today)
    
    # 付款人信息
    payer_name = StringField('付款人姓名', validators=[
        DataRequired(message='付款人姓名不能为空')
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
    """项目级别收款表单 - 按发票分配"""

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
        ('wechat', 'WeChat'),
        ('other', '其他')
    ], default='bank_transfer', validators=[DataRequired(message='请选择付款方式')])
    
    payment_date = DateField('收款日期', validators=[
        DataRequired(message='收款日期不能为空')
    ], default=date.today)
    
    # 分配方式
    distribution_method = SelectField('分配方式', choices=[
        ('sequential', '顺序分配（按发票顺序依次结算）'),
        ('manual', '手动指定发票')
    ], default='sequential', validators=[DataRequired(message='请选择分配方式')])

    # 手动分配发票选择（动态生成）
    selected_invoices = SelectMultipleField('选择要分配的发票', coerce=int, validators=[
        Optional()
    ])
    
    # 付款人信息
    payer_name = StringField('付款人姓名', validators=[
        DataRequired(message='付款人姓名不能为空')
    ])
    
    payer_contact = StringField('付款人联系方式', validators=[
        Optional()
    ])
    
    payer_company = StringField('付款人公司', validators=[
        Optional()
    ])
    
    # 银行信息（必填）
    bank_name = StringField('银行名称', validators=[
        DataRequired(message='银行名称不能为空')
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


class CompanyReceiptForm(FlaskForm):
    """按公司收款表单"""

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

    # 发票选择（多选，动态生成）
    selected_invoices = SelectMultipleField('选择发票', coerce=int, validators=[
        Optional()
    ])

    # 分配方式
    distribution_method = SelectField('分配方式', choices=[
        ('sequential', '顺序分配（按发票日期从早到晚依次付清）'),
        ('proportional', '按比例分配')
    ], default='sequential', validators=[DataRequired(message='请选择分配方式')])

    payment_method = SelectField('付款方式', choices=[
        ('bank_transfer', '银行转账'),
        ('cash', '现金'),
        ('credit_card', '信用卡'),
        ('cheque', '支票'),
        ('wechat', 'WeChat'),
        ('other', '其他')
    ], default='bank_transfer', validators=[DataRequired(message='请选择付款方式')])

    payment_date = DateField('收款日期', validators=[
        DataRequired(message='收款日期不能为空')
    ], default=date.today)

    # 付款人信息
    payer_name = StringField('付款人姓名', validators=[Optional()])
    payer_contact = StringField('付款人联系方式', validators=[Optional()])

    # 银行信息
    bank_name = StringField('银行名称', validators=[
        DataRequired(message='银行名称不能为空')
    ])
    account_number = StringField('账号', validators=[Optional()])
    transaction_id = StringField('交易流水号', validators=[Optional()])

    # 备注
    remarks = TextAreaField('备注', validators=[Optional()])

    submit = SubmitField('创建收款记录')