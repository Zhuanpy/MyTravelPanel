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
    
    name = StringField('EO订单名称', [
        Length(max=100, message='订单名称不能超过100个字符')
    ])
    
    supplier_type = SelectField('供应商类型', [
        DataRequired(message='请选择供应商类型')
    ], choices=[
        ('visa', '签证'),
        ('flight', '机票'),
        ('hotel', '酒店'),
        ('transport', '交通'),
        ('local_operator', '地接'),
        ('other', '其他')
    ])
    
    supplier_id = SelectField('供应商', [
        DataRequired(message='请选择供应商')
    ], coerce=int, choices=[])
    
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
    
    # 金额信息
    amount = DecimalField('金额', [
        DataRequired(message='金额不能为空'),
        NumberRange(min=0, message='金额不能为负数')
    ], places=2)
    
    currency = SelectField('货币类型', [
        DataRequired(message='请选择货币类型')
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
    
    remarks = TextAreaField('备注', [
        Length(max=1000, message='备注不能超过1000个字符')
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

    def __init__(self, *args, **kwargs):
        super(ProjectEOForm, self).__init__(*args, **kwargs)
        # 动态加载供应商选项
        self._load_choices()
    
    def _load_choices(self):
        """动态加载下拉选项"""
        try:
            from App.models.Product.Suppliers import Supplier
            
            # 加载供应商
            suppliers = Supplier.query.all()
            self.supplier_id.choices = [(s.supplier_id, s.name) for s in suppliers]
            
        except ImportError:
            # 如果模型导入失败，使用默认选项
            self.supplier_id.choices = [(1, '默认供应商')] 