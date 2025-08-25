from App_new.exts import db
from datetime import datetime


class AirportData(db.Model):
    # 表名
    __tablename__ = 'airport_data'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    airport_IATA = db.Column(db.String(3), unique=True, index=True, nullable=False)
    city_name = db.Column(db.String(100), index=True, nullable=False)
    airport_name_cn = db.Column(db.String(100), nullable=False)
    airport_name_en = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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


# 机票订单
class FlightOrder(db.Model):
    # 表名
    __tablename__ = 'flight_orders'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 订单号
    hid_number = db.Column(db.String(50), index=True)  # HID号码
    
    # 基本信息
    passenger_name = db.Column(db.String(100), nullable=False)  # 乘机人
    contact_person = db.Column(db.String(100))  # 联系人
    contact_phone = db.Column(db.String(20))  # 联系电话
    
    # 行程信息
    departure_date = db.Column(db.Date, nullable=False)  # 起飞日期
    itinerary = db.Column(db.Text)  # 行程详情
    departure_city = db.Column(db.String(50))  # 出发城市
    arrival_city = db.Column(db.String(50))  # 到达城市
    
    # 航班信息
    airline = db.Column(db.String(50))  # 航空公司
    flight_number = db.Column(db.String(20))  # 航班号
    departure_time = db.Column(db.DateTime)  # 出发时间
    arrival_time = db.Column(db.DateTime)  # 到达时间
    cabin_class = db.Column(db.String(20))  # 舱位等级
    is_transit = db.Column(db.Boolean, default=False)  # 是否中转
    transit_info = db.Column(db.Text)  # 中转信息
    
    # 订单管理
    order_status = db.Column(db.String(20), default='待出票')  # 订单状态：待出票/已出票/已取消/已完成
    payment_status = db.Column(db.String(20), default='待支付')  # 支付状态：待支付/已支付/已退款
    payment_method = db.Column(db.String(30))  # 支付方式
    total_price = db.Column(db.Float)  # 票价总额
    tax_fee = db.Column(db.Float)  # 税费
    actual_payment = db.Column(db.Float)  # 实付金额
    ticket_issue_time = db.Column(db.DateTime)  # 出票时间
    operator = db.Column(db.String(50))  # 操作人员
    refund_change_policy = db.Column(db.Text)  # 退改签政策
    
    # 额外信息
    baggage_allowance = db.Column(db.String(100))  # 行李额度
    pnr_code = db.Column(db.String(20))  # PNR号码
    e_ticket_number = db.Column(db.String(50))  # 电子客票号
    client_type = db.Column(db.String(20), default='个人')  # 客户类型：企业/个人
    remarks = db.Column(db.Text)  # 备注信息
    after_sales_record = db.Column(db.Text)  # 售后记录
    
    # 时间戳
    created_date = db.Column(db.DateTime, default=datetime.utcnow)  # 创建日期
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新日期

    def __repr__(self):
        return f'<FlightOrder {self.order_number} - {self.passenger_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'hid_number': self.hid_number,
            'passenger_name': self.passenger_name,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'departure_date': self.departure_date.strftime('%Y-%m-%d') if self.departure_date else None,
            'itinerary': self.itinerary,
            'departure_city': self.departure_city,
            'arrival_city': self.arrival_city,
            'airline': self.airline,
            'flight_number': self.flight_number,
            'departure_time': self.departure_time.strftime('%Y-%m-%d %H:%M') if self.departure_time else None,
            'arrival_time': self.arrival_time.strftime('%Y-%m-%d %H:%M') if self.arrival_time else None,
            'cabin_class': self.cabin_class,
            'is_transit': self.is_transit,
            'transit_info': self.transit_info,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'total_price': self.total_price,
            'tax_fee': self.tax_fee,
            'actual_payment': self.actual_payment,
            'ticket_issue_time': self.ticket_issue_time.strftime('%Y-%m-%d %H:%M') if self.ticket_issue_time else None,
            'operator': self.operator,
            'refund_change_policy': self.refund_change_policy,
            'baggage_allowance': self.baggage_allowance,
            'pnr_code': self.pnr_code,
            'e_ticket_number': self.e_ticket_number,
            'client_type': self.client_type,
            'remarks': self.remarks,
            'after_sales_record': self.after_sales_record,
            'created_date': self.created_date.strftime('%Y-%m-%d %H:%M:%S') if self.created_date else None,
            'updated_date': self.updated_date.strftime('%Y-%m-%d %H:%M:%S') if self.updated_date else None
        }
