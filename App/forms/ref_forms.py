from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, DecimalField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from datetime import date

class ProjectRefForm(FlaskForm):
    """项目REF明细表单"""
    header_id = IntegerField('主表ID', [DataRequired(message='主表ID不能为空')])
    
    ref_number = StringField('REF编号', [
        DataRequired(message='REF编号不能为空'),
        Length(max=30, message='REF编号不能超过30个字符')
    ])
    
    name = StringField('REF订单名称', [
        Length(max=100, message='订单名称不能超过100个字符')
    ])
    
    ref_type_id = SelectField('REF类型', [
        DataRequired(message='请选择REF类型')
    ], coerce=int)
    
    description = StringField('描述', [
        DataRequired(message='描述不能为空'),
        Length(max=200, message='描述不能超过200个字符')
    ])
    
    # 供应商信息
    supplier_id = SelectField('供应商', [
        Optional()
    ], coerce=int, choices=[])
    
    supplier_contact = StringField('供应商联系人', [
        Length(max=50, message='供应商联系人不能超过50个字符')
    ])
    
    supplier_phone = StringField('供应商联系电话', [
        Length(max=20, message='供应商联系电话不能超过20个字符')
    ])
    
    # 联系人信息
    contact_name = StringField('联系人姓名', [
        Length(max=50, message='联系人姓名不能超过50个字符')
    ])
    
    contact_phone = StringField('联系电话', [
        Length(max=20, message='联系电话不能超过20个字符')
    ])
    
    contact_email = StringField('电子邮箱', [
        Length(max=100, message='电子邮箱不能超过100个字符')
    ])
    
    leader_name = StringField('负责人姓名', [
        Length(max=100, message='负责人姓名不能超过100个字符')
    ])
    
    # 价格信息
    selling_price = DecimalField('销售价格', [
        Optional(),
        NumberRange(min=0, message='销售价格不能为负数')
    ], places=2)
    
    cost_price = DecimalField('成本价格', [
        Optional(),
        NumberRange(min=0, message='成本价格不能为负数')
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
    
    # 日期信息
    expected_delivery_date = DateField('预计交付日期', [
        Optional()
    ], format='%Y-%m-%d')
    
    actual_delivery_date = DateField('实际交付日期', [
        Optional()
    ], format='%Y-%m-%d')
    
    # 备注
    remarks = TextAreaField('备注', [
        Length(max=1000, message='备注不能超过1000个字符')
    ])
    
    # 状态信息
    status = SelectField('状态', [
        DataRequired(message='请选择状态')
    ], choices=[
        ('draft', '草稿'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消')
    ])
    
    payment_status = SelectField('支付状态', [
        DataRequired(message='请选择支付状态')
    ], choices=[
        ('unpaid', '未支付'),
        ('partial', '部分支付'),
        ('paid', '已支付'),
        ('refunded', '已退款')
    ])
    
    submit = SubmitField('保存REF')
    cancel = SubmitField('取消')

    def __init__(self, *args, **kwargs):
        super(ProjectRefForm, self).__init__(*args, **kwargs)
        # 动态加载供应商和业务类型选项
        self._load_choices()
    
    def _load_choices(self):
        """动态加载下拉选项"""
        try:
            from App.models.Product.BusinessType import BusinessType
            from App.models.Product.Suppliers import Supplier
            
            # 加载业务类型
            business_types = BusinessType.query.all()
            self.ref_type_id.choices = [(bt.id, bt.name) for bt in business_types]
            
            # 加载供应商
            suppliers = Supplier.query.all()
            self.supplier_id.choices = [(0, '请选择供应商')] + [(s.supplier_id, s.name) for s in suppliers]
            
        except ImportError:
            # 如果模型导入失败，使用默认选项
            self.ref_type_id.choices = [(1, '默认类型')]
            self.supplier_id.choices = [(0, '请选择供应商')] 