from ..exts import db


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
