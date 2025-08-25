from App_new.exts import db
from datetime import datetime
from sqlalchemy import DECIMAL
from App_new.utils.cache import cached
# 导入项目相关模型

class AirportData(db.Model):
    # 表名
    __tablename__ = 'airport_data'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    airport_IATA = db.Column(db.String(3), unique=True, index=True, nullable=False)
    city_name = db.Column(db.String(100), index=True, nullable=False)
    airport_name_cn = db.Column(db.String(100), nullable=False)
    airport_name_en = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<Airport {self.airport_IATA} - {self.airport_name_en}>'

    def to_dict(self):
        return {
            'id': self.id,
            'iata': self.airport_IATA,
            'city': self.city_name,
            'airport_name_cn': self.airport_name_cn,
            'airport_name_en': self.airport_name_en,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def validate_iata(iata_code):
        """验证IATA代码格式"""
        if not iata_code or len(iata_code) != 3:
            return False
        return iata_code.isalpha() and iata_code.isupper()

    @classmethod
    def create_or_update(cls, iata, city, name_cn, name_en):
        """创建或更新机场信息"""
        airport = cls.query.filter_by(airport_IATA=iata.upper()).first()
        if airport:
            airport.city_name = city.strip()
            airport.airport_name_cn = name_cn.strip()
            airport.airport_name_en = name_en.strip()
        else:
            airport = cls(
                airport_IATA=iata.upper(),
                city_name=city.strip(),
                airport_name_cn=name_cn.strip(),
                airport_name_en=name_en.strip()
            )
            db.session.add(airport)
        return airport


# flight schedule
class FlightSchedule(db.Model):
    # 表名
    __tablename__ = 'flight_schedule'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    flight_number = db.Column(db.String(10), unique=True, index=True)

    airline_code = db.Column(db.String(10))
    airline_num = db.Column(db.String(10))

    schedule_city = db.Column(db.String(20))
    schedule_timing = db.Column(db.String(15))

    def to_dict(self):
        return {
            'id': self.id,
            'flight_number': self.flight_number,
            'airline_code': self.airline_code,
            'airline_num': self.airline_num,
            'schedule_city': self.schedule_city,
            'schedule_timing': self.schedule_timing,
        }


class FlightOrder(db.Model):
    """机票订单主表"""
    __tablename__ = 'flight_orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, comment='订单编号')
    hid_number = db.Column(db.String(50), comment='会员号')

    # 项目关联字段
    project_header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=True,
                                  comment='关联项目主表ID')
    project_ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=True, comment='关联项目明细ID')

    passenger_name = db.Column(db.String(100), nullable=False, comment='乘客姓名')
    contact_person = db.Column(db.String(100), comment='联系人')
    contact_phone = db.Column(db.String(20), nullable=True, comment='联系人电话')
    contact_name = db.Column(db.String(50), nullable=False, comment='联系人姓名')
    supplier_name = db.Column(db.String(100), comment='供应商名称')

    # 航班信息
    departure_date = db.Column(db.Date, nullable=False, comment='出发日期')
    itinerary = db.Column(db.String(200), comment='行程信息')
    departure_city = db.Column(db.String(50), comment='出发城市')
    arrival_city = db.Column(db.String(50), comment='到达城市')
    airline = db.Column(db.String(50), comment='航空公司')
    flight_number = db.Column(db.String(20), comment='航班号')
    departure_time = db.Column(db.DateTime, comment='起飞时间')
    arrival_time = db.Column(db.DateTime, comment='到达时间')
    cabin_class = db.Column(db.String(20), comment='舱位等级')

    # 中转信息
    is_transit = db.Column(db.Boolean, default=False, comment='是否中转')
    transit_info = db.Column(db.Text, comment='中转信息')

    # 订单状态和支付信息
    status = db.Column(db.String(20), nullable=False, default='pending', comment='订单状态')
    order_status = db.Column(db.String(20), comment='订单状态')
    payment_status = db.Column(db.String(20), comment='支付状态')
    payment_method = db.Column(db.String(30), comment='支付方式')
    selling_price = db.Column(DECIMAL(10, 2), comment='售价')
    cost_price = db.Column(DECIMAL(10, 2), comment='成本')
    actual_payment = db.Column(db.Float, comment='实际支付金额')

    # 票务信息
    ticket_issue_time = db.Column(db.DateTime, comment='出票时间')
    operator = db.Column(db.String(50), comment='操作员')
    refund_change_policy = db.Column(db.Text, comment='退改政策')
    baggage_allowance = db.Column(db.String(100), comment='行李额')
    pnr_code = db.Column(db.String(20), comment='PNR编码')
    e_ticket_number = db.Column(db.String(50), comment='电子客票号')
    client_type = db.Column(db.String(20), comment='客户类型')

    # 其他信息
    remarks = db.Column(db.Text, comment='备注')
    after_sales_record = db.Column(db.Text, comment='售后记录')
    created_date = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_date = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联信息
    passengers = db.relationship('Passenger', backref='order', lazy=True)
    flight_segments = db.relationship('FlightSegment', backref='order', lazy=True)

    # 项目关联关系
    project_header = db.relationship('ProjectHeader', backref='flight_orders', lazy=True)
    project_ref = db.relationship('ProjectRef', backref='flight_orders', lazy=True)

    @property
    @cached(expire_minutes=30)
    def formatted_itinerary(self):
        """获取格式化的行程信息"""
        segments = []
        for segment in sorted(self.flight_segments, key=lambda x: x.departure_time):
            date_str = segment.departure_time.strftime('%d%b').upper()
            route = f"{segment.departure_airport}-{segment.arrival_airport}"
            segments.append(f"{date_str} {route}")
        return " → ".join(segments)

    @property
    @cached(expire_minutes=30)
    def first_departure_city(self):
        """获取第一个出发城市"""
        if self.flight_segments:
            first_segment = min(self.flight_segments, key=lambda x: x.departure_time)
            return first_segment.departure_airport
        return self.departure_city

    @property
    @cached(expire_minutes=30)
    def final_arrival_city(self):
        """获取最终到达城市"""
        if self.flight_segments:
            last_segment = max(self.flight_segments, key=lambda x: x.departure_time)
            return last_segment.arrival_airport
        return self.arrival_city

    # 从机票订单访问项目信息
    @property
    @cached(expire_minutes=30)
    def project_header_hid(self):
        """获取HID编号"""
        return self.project_header.hid if self.project_header else None

    @property
    @cached(expire_minutes=30)
    def project_ref_ref_number(self):
        """获取REF编号"""
        return self.project_ref.ref_number if self.project_ref else None


class Passenger(db.Model):
    """乘机人信息表"""
    __tablename__ = 'passengers'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('flight_orders.id'), nullable=False)

    # 乘客基本信息
    name = db.Column(db.String(50), nullable=False, comment='乘客姓名')

    # 乘客类型：成人、儿童、婴儿
    passenger_type = db.Column(db.String(10), nullable=False, default='adult', comment='乘客类型')

    # 票价信息
    selling_price = db.Column(DECIMAL(10, 2), comment='售价')
    cost_price = db.Column(DECIMAL(10, 2), comment='成本')
    phone = db.Column(db.String(20), comment='乘客电话')

    # 票务信息
    ticket_number = db.Column(db.String(13), comment='电子客票号')
    pnr = db.Column(db.String(6), comment='PNR编码')


class FlightSegment(db.Model):
    """航段信息表"""
    __tablename__ = 'flight_segments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('flight_orders.id'), nullable=False)

    # 航班信息
    flight_number = db.Column(db.String(10), nullable=False, comment='航班号')
    departure_airport = db.Column(db.String(3), nullable=False, comment='出发机场')
    arrival_airport = db.Column(db.String(3), nullable=False, comment='到达机场')
    departure_time = db.Column(db.DateTime, nullable=False, comment='起飞时间')
    arrival_time = db.Column(db.DateTime, nullable=False, comment='到达时间')

    # 舱位信息
    cabin_class = db.Column(db.String(20), nullable=False, comment='舱位等级')
    cabin_code = db.Column(db.String(2), nullable=False, comment='舱位代码')

    # 航段状态
    status = db.Column(db.String(20), nullable=False, default='pending', comment='航段状态')
