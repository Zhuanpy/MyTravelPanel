from flask_wtf import FlaskForm
from wtforms import StringField, validators

class FlightScheduleForm(FlaskForm):
    flight_number = StringField('Flight Number', [
        validators.DataRequired(message='航班号不能为空'),
        validators.Length(min=2, max=10, message='航班号长度必须在2-10个字符之间')
    ])
    schedule_city = StringField('Schedule City', [
        validators.DataRequired(message='航班城市不能为空'),
        validators.Length(min=6, max=8, message='城市代码格式不正确')
    ])
    schedule_timing = StringField('Schedule Timing', [
        validators.DataRequired(message='航班时间不能为空')
    ]) 