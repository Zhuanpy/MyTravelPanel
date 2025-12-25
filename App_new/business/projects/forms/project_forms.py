# -*- coding: utf-8 -*-
"""
项目表单类
包含项目创建、编辑等表单
"""

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, StringField, IntegerField, SelectField, TextAreaField, SubmitField, DateTimeField
from wtforms.validators import DataRequired, Length, Email, Optional, ValidationError
from App_new.business.projects.models.project import ProjectHeader
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, Optional
from App_new.business.projects.models.project import CustomerCompany

class ProjectCreateForm(FlaskForm):
    """项目创建表单"""
    
    hid = StringField('项目编号', validators=[
        DataRequired(message='项目编号不能为空'),
        Length(min=1, max=50, message='项目编号长度必须在1-50个字符之间')
    ])
    
    description = TextAreaField('项目描述', validators=[
        DataRequired(message='项目描述不能为空'),
        Length(min=1, max=500, message='项目描述长度必须在1-500个字符之间')
    ])
    
    company_id = SelectField('客户公司', coerce=int, validators=[
        Optional()
    ])
    
    contact = StringField('联系人', validators=[
        DataRequired(message='联系人不能为空'),
        Length(min=1, max=100, message='联系人长度必须在1-100个字符之间')
    ])
    
    contact_phone = StringField('联系电话', validators=[
        Optional(),
        Length(max=20, message='联系电话长度不能超过20个字符')
    ])
    
    contact_email = StringField('联系邮箱', validators=[
        Optional(),
        Email(message='请输入有效的邮箱地址'),
        Length(max=100, message='邮箱长度不能超过100个字符')
    ])
    
    type = SelectField('项目类型', choices=[
        ('comprehensive', '综合'),
        ('flight', '机票'),
        ('visa', '签证'),
        ('tour', '旅游'),
        ('hotel', '酒店'),
        ('other', '其他')
    ], validators=[
        DataRequired(message='请选择项目类型')
    ])
    
    status = SelectField('项目状态', choices=[
        ('draft', '草稿'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消')
    ], validators=[
        DataRequired(message='请选择项目状态')
    ])
    
    currency = SelectField('货币', choices=[
        ('CNY', '人民币'),
        ('USD', '美元'),
        ('EUR', '欧元'),
        ('SGD', '新加坡元'),
        ('JPY', '日元'),
        ('KRW', '韩元'),
        ('THB', '泰铢'),
        ('MYR', '马来西亚林吉特'),
        ('IDR', '印尼盾'),
        ('PHP', '菲律宾比索'),
        ('VND', '越南盾'),
        ('INR', '印度卢比'),
        ('AUD', '澳元'),
        ('CAD', '加元'),
        ('GBP', '英镑')
    ], validators=[
        DataRequired(message='请选择货币')
    ])
    
    leader_name = StringField('项目负责人', validators=[
        Optional(),
        Length(max=100, message='项目负责人长度不能超过100个字符')
    ])
    
    remarks = TextAreaField('备注', validators=[
        Optional(),
        Length(max=1000, message='备注长度不能超过1000个字符')
    ])
    
    def validate_hid(self, field):
        """验证项目编号唯一性"""
        if ProjectHeader.query.filter_by(hid=field.data).first():
            raise ValidationError('项目编号已存在，请使用其他编号')

class ProjectEditForm(FlaskForm):
    """项目编辑表单"""
    
    description = TextAreaField('项目描述', validators=[
        DataRequired(message='项目描述不能为空'),
        Length(min=1, max=500, message='项目描述长度必须在1-500个字符之间')
    ])
    
    company_id = SelectField('客户公司', coerce=int, validators=[
        Optional()
    ])
    
    contact = StringField('联系人', validators=[
        DataRequired(message='联系人不能为空'),
        Length(min=1, max=100, message='联系人长度必须在1-100个字符之间')
    ])
    
    contact_phone = StringField('联系电话', validators=[
        Optional(),
        Length(max=20, message='联系电话长度不能超过20个字符')
    ])
    
    contact_email = StringField('联系邮箱', validators=[
        Optional(),
        Email(message='请输入有效的邮箱地址'),
        Length(max=100, message='邮箱长度不能超过100个字符')
    ])
    
    type = SelectField('项目类型', choices=[
        ('comprehensive', '综合'),
        ('flight', '机票'),
        ('visa', '签证'),
        ('tour', '旅游'),
        ('hotel', '酒店'),
        ('other', '其他')
    ], validators=[
        DataRequired(message='请选择项目类型')
    ])
    
    status = SelectField('项目状态', choices=[
        ('draft', '草稿'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消')
    ], validators=[
        DataRequired(message='请选择项目状态')
    ])
    
    currency = SelectField('货币', choices=[
        ('CNY', '人民币'),
        ('USD', '美元'),
        ('EUR', '欧元'),
        ('SGD', '新加坡元'),
        ('JPY', '日元'),
        ('KRW', '韩元'),
        ('THB', '泰铢'),
        ('MYR', '马来西亚林吉特'),
        ('IDR', '印尼盾'),
        ('PHP', '菲律宾比索'),
        ('VND', '越南盾'),
        ('INR', '印度卢比'),
        ('AUD', '澳元'),
        ('CAD', '加元'),
        ('GBP', '英镑')
    ], validators=[
        DataRequired(message='请选择货币')
    ])
    
    leader_name = StringField('项目负责人', validators=[
        Optional(),
        Length(max=100, message='项目负责人长度不能超过100个字符')
    ])
    
    remarks = TextAreaField('备注', validators=[
        Optional(),
        Length(max=1000, message='备注长度不能超过1000个字符')
    ])

class ProjectSearchForm(FlaskForm):
    """项目搜索表单"""
    
    search = StringField('搜索关键词', validators=[
        Optional()
    ])
    
    status = SelectField('项目状态', choices=[
        ('', '所有状态'),
        ('draft', '草稿'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消')
    ], validators=[
        Optional()
    ])
    
    type = SelectField('项目类型', choices=[
        ('', '所有类型'),
        ('comprehensive', '综合'),
        ('flight', '机票'),
        ('visa', '签证'),
        ('tour', '旅游'),
        ('hotel', '酒店'),
        ('other', '其他')
    ], validators=[
        Optional()
    ])
    
    company = StringField('客户公司', validators=[
        Optional()
    ])
    
    leader = StringField('项目负责人', validators=[
        Optional()
    ])
    
    contact = StringField('联系人', validators=[
        Optional()
    ])
    
    date_from = DateField('开始日期', validators=[
        Optional()
    ])
    
    date_to = DateField('结束日期', validators=[
        Optional()
    ])
    
    selling_min = DecimalField('最小销售金额', validators=[
        Optional()
    ])
    
    selling_max = DecimalField('最大销售金额', validators=[
        Optional()
    ])
    
    profit_min = DecimalField('最小利润', validators=[
        Optional()
    ])
    
    profit_max = DecimalField('最大利润', validators=[
        Optional()
    ])
    
    sort_by = SelectField('排序方式', choices=[
        ('created_at_desc', '创建时间（最新）'),
        ('created_at_asc', '创建时间（最早）'),
        ('updated_at_desc', '更新时间（最新）'),
        ('updated_at_asc', '更新时间（最早）')
    ], validators=[
        Optional()
    ])

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

    company_id = SelectField('选择公司', coerce=int, choices=[])

    def __init__(self, *args, **kwargs):
        super(ProjectHeaderForm, self).__init__(*args, **kwargs)
        # 动态加载公司选项，第一项为空占位符
        companies = CustomerCompany.query.filter_by(status='active').order_by(CustomerCompany.company_name).all()
        self.company_id.choices = [(-1, '请选择公司')] + [(0, '个人')] + [(c.id, c.company_name) for c in companies]

        # 如果是编辑模式，移除项目编号的长度验证
        if 'obj' in kwargs and kwargs['obj']:
            self.hid.validators = [DataRequired(message='项目编号不能为空')]

    def validate_company_id(self, field):
        """验证必须选择公司或个人"""
        if field.data == -1:
            raise ValidationError('请选择公司或个人')

    limit = StringField('额度限制', [
        Length(max=50, message='额度限制不能超过50个字符')
    ])

    contact = StringField('联系人', [
        DataRequired(message='联系人不能为空'),
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
        ('CNY', '人民币')
    ])

    type = SelectField('类型', [
        DataRequired(message='请选择类型')
    ], choices=[
        ('', '请选择类型'),
        ('comprehensive', '综合'),
        ('flight', '机票'),
        ('visa', '签证'),
        ('tour', '旅游'),
        ('hotel', '酒店'),
        ('other', '其他')
    ])

    status = SelectField('状态', [
        DataRequired(message='请选择状态')
    ], choices=[
        ('draft', '草稿'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消')
    ], default='active')

    remarks = TextAreaField('备注', [
        Length(max=1000, message='备注不能超过1000个字符')
    ])

    # 提醒相关字段已移除，现在在项目详情页面管理

    submit = SubmitField('保存项目')
    cancel = SubmitField('取消')