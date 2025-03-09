from ..exts import db


class AirportData(db.Model):
    # 表名
    __tablename__ = 'airport_data'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    airport_IATA = db.Column(db.String(3), unique=True, index=True)  # IATA 代码一般为3个字符
    city_name = db.Column(db.String(100), index=True)  # 假设城市名不会超过100个字符
    airport_name_cn = db.Column(db.String(100))  # 假设中文机场名称不会超过100个字符
    airport_name_en = db.Column(db.String(100))  # 假设英文机场名称不会超过100个字符

    def __repr__(self):
        return f'<Airport {self.airport_IATA} - {self.airport_name_en}>'

    def to_dict(self):

        return {
            'id': self.id,
            'iata': self.airport_IATA,
            'city': self.city_name,
            # 添加其他字段
            'airport_name_cn': self.airport_name_cn,
            'airport_name_en': self.airport_name_en,
        }


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
