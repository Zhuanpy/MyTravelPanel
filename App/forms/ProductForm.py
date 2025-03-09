from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateTimeField
from wtforms.validators import DataRequired
from datetime import datetime


class ProductForm(FlaskForm):
    city_name = StringField("城市名字", validators=[DataRequired()])
    company_name = StringField("公司名字", validators=[DataRequired()])
    product_name = StringField("产品名", validators=[DataRequired()])
    created_at = DateTimeField("创建时间", default=datetime.utcnow().date, format='%Y-%m-%d')
    valid_until = DateTimeField("有效期", format='%Y-%m-%d')
    submit = SubmitField("添加产品")
