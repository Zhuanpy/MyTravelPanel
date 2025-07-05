from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from App.models.projects.BookingProject import CustomerCompany

class ProjectHeaderForm(FlaskForm):
    """项目主表表单"""
    hid = StringField('项目编号', [
        DataRequired(message='项目编号不能为空'),
        Length(min=3, max=20, message='项目编号长度必须在3-20个字符之间')
    ])
    
    desc = StringField('项目描述', [
        DataRequired(message='项目描述不能为空'),
        Length(max=200, message='项目描述不能超过200个字符')
    ])
    
    company_id = SelectField('选择公司', [
        Optional()
    ], coerce=int, choices=[])
    

    
    def __init__(self, *args, **kwargs):
        super(ProjectHeaderForm, self).__init__(*args, **kwargs)
        # 动态加载公司选项
        companies = CustomerCompany.query.filter_by(status='active').order_by(CustomerCompany.company_name).all()
        self.company_id.choices = [(0, '请选择公司')] + [(c.id, c.company_name) for c in companies]
    
    limit = StringField('额度限制', [
        Length(max=50, message='额度限制不能超过50个字符')
    ])
    
    contact = StringField('联系人', [
        Length(max=50, message='联系人不能超过50个字符')
    ])
    
    dept = StringField('部门', [
        Length(max=50, message='部门不能超过50个字符')
    ])
    
    staff_id = IntegerField('经办人ID', [Optional()])
    staff_name = StringField('经办人姓名', [
        DataRequired(message='经办人姓名不能为空'),
        Length(max=50, message='经办人姓名不能超过50个字符')
    ])
    
    leader_name = StringField('负责人姓名', [
        Length(max=100, message='负责人姓名不能超过100个字符')
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
    
    type = StringField('类型', [
        Length(max=50, message='类型不能超过50个字符')
    ])
    
    source = StringField('来源', [
        Length(max=50, message='来源不能超过50个字符')
    ])
    
    country = StringField('国家', [
        Length(max=50, message='国家不能超过50个字符')
    ])
    
    status = SelectField('状态', [
        DataRequired(message='请选择状态')
    ], choices=[
        ('draft', '草稿'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消')
    ])
    
    remarks = TextAreaField('备注', [
        Length(max=1000, message='备注不能超过1000个字符')
    ])
    
    submit = SubmitField('保存项目')
    cancel = SubmitField('取消') 