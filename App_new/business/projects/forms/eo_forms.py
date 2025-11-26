from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class ProjectEOForm(FlaskForm):
    """项目EO子明细表单"""
    ref_id = IntegerField('REF明细ID', [DataRequired(message='REF明细ID不能为空')])
    
    eo_number = StringField('EO编号', [
        DataRequired(message='EO编号不能为空'),
        Length(max=30, message='EO编号不能超过30个字符')
    ])
    
    # 外部系统信息
    external_system = StringField('外部系统名称', [
        Length(max=50, message='外部系统名称不能超过50个字符')
    ])
    
    external_status = StringField('外部系统状态', [
        Length(max=50, message='外部系统状态不能超过50个字符')
    ])
    
    external_reference = StringField('外部系统参考号', [
        Length(max=100, message='外部系统参考号不能超过100个字符')
    ])
    
    status = SelectField('状态', [
        DataRequired(message='请选择状态')
    ], choices=[
        ('confirmed', '已确认'),
        ('draft', '草稿'),
        ('paid', '已支付'),
        ('cancelled', '已取消')
    ], default='confirmed')
    
    submit = SubmitField('保存EO')
    cancel = SubmitField('取消')
