from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
import re
from datetime import date

def validate_email_with_special_values(form, field):
    """自定义邮箱验证器，允许特殊值如N/A、NONE等"""
    if not field.data:
        return
    
    email = field.data.strip()
    
    # 允许的特殊值（不区分大小写）
    allowed_special_values = ['n/a', 'none', '无', 'na', 'null', '']
    if email.lower() in allowed_special_values:
        return
    
    # 标准邮箱格式验证
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        from wtforms import ValidationError
        raise ValidationError('请输入有效的邮箱地址或使用N/A、NONE等特殊值')

class CustomerCompanyForm(FlaskForm):
    """客户公司表单"""
    company_name = StringField('公司名称', [
        DataRequired(message='公司名称不能为空'),
        Length(max=100, message='公司名称不能超过100个字符')
    ])
    
    company_code = StringField('公司代码', [
        Length(max=50, message='公司代码不能超过50个字符')
    ])
    
    contact_person = StringField('联系人', [
        Length(max=50, message='联系人不能超过50个字符')
    ])
    
    contact_phone = StringField('联系电话', [
        Length(max=20, message='联系电话不能超过20个字符')
    ])
    
    contact_email = StringField('联系邮箱', [
        validate_email_with_special_values,
        Length(max=100, message='邮箱不能超过100个字符')
    ])
    
    address = TextAreaField('公司地址', [
        Length(max=500, message='地址不能超过500个字符')
    ])
    
    industry = SelectField('行业', [
        Optional()
    ], choices=[
        ('', '请选择行业'),
        ('technology', '科技'),
        ('finance', '金融'),
        ('manufacturing', '制造业'),
        ('healthcare', '医疗健康'),
        ('education', '教育'),
        ('retail', '零售'),
        ('tourism', '旅游'),
        ('real_estate', '房地产'),
        ('consulting', '咨询'),
        ('other', '其他')
    ])
    
    company_size = SelectField('公司规模', [
        Optional()
    ], choices=[
        ('', '请选择规模'),
        ('startup', '初创公司'),
        ('small', '小型公司'),
        ('medium', '中型公司'),
        ('large', '大型公司'),
        ('enterprise', '企业级')
    ])
    
    credit_limit = DecimalField('信用额度', [
        Optional(),
        NumberRange(min=0, message='信用额度不能为负数')
    ])
    
    currency = SelectField('币种', [
        DataRequired(message='请选择币种')
    ], choices=[
        ('SGD', '新加坡元'),
        ('CNY', '人民币'),
        ('USD', '美元'),
        ('EUR', '欧元'),
        ('JPY', '日元'),
        ('KRW', '韩元'),
        ('THB', '泰铢'),
        ('MYR', '马来西亚林吉特'),
        ('IDR', '印尼盾'),
        ('VND', '越南盾')
    ])
    
    status = SelectField('状态', [
        DataRequired(message='请选择状态')
    ], choices=[
        ('active', '活跃'),
        ('inactive', '非活跃'),
        ('suspended', '暂停')
    ])
    
    remarks = TextAreaField('备注', [
        Length(max=1000, message='备注不能超过1000个字符')
    ])
    
    created_at = DateField('创建时间', [
        Optional()
    ])
    
    # 集团/关联标签（可自由输入，如 BAONENG, ALIBABA 等）
    group_name = StringField('集团/关联', [
        Optional(),
        Length(max=100, message='集团/关联标签不能超过100个字符')
    ])
    
    submit = SubmitField('保存公司')
    cancel = SubmitField('取消') 