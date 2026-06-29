# -*- coding: utf-8 -*-
"""机票相关模型 - 机票乘客和航段信息"""

from ....exts import db
from datetime import datetime


class ProjectFlightPassenger(db.Model):
    """机票乘客信息表 - 3级表"""
    __tablename__ = 'project_flight_passengers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False, comment='REF明细ID')

    # 乘客基本信息
    name = db.Column(db.String(50), nullable=False, comment='乘客姓名')
    passenger_type = db.Column(db.String(10), nullable=False, default='adult', comment='乘客类型：adult/child/infant')

    # 票价信息
    selling_price = db.Column(db.Numeric(10, 2), comment='售价')
    cost_price = db.Column(db.Numeric(10, 2), comment='成本')

    # 票务信息
    ticket_number = db.Column(db.String(50), comment='电子客票号')
    pnr = db.Column(db.String(10), comment='PNR编码')

    # 行李额（按乘客，全程通用）
    baggage = db.Column(db.String(50), comment='行李额')
    # 各航段座位号：JSON 列表，按航段顺序一一对应（座位按 乘客×航段 区分）
    seats = db.Column(db.Text, comment='各航段座位号(JSON列表,按航段顺序)')

    # 证件信息
    passport_number = db.Column(db.String(20), comment='护照号')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ProjectFlightPassenger {self.name}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'ref_id': self.ref_id,
            'name': self.name,
            'passenger_type': self.passenger_type,
            'selling_price': float(self.selling_price) if self.selling_price else None,
            'cost_price': float(self.cost_price) if self.cost_price else None,
            'ticket_number': self.ticket_number,
            'pnr': self.pnr,
            'baggage': self.baggage,
            'seats': self.seat_list,
            'passport_number': self.passport_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def seat_list(self):
        """各航段座位号列表（解析 JSON，失败返回空列表）"""
        if not self.seats:
            return []
        try:
            import json
            v = json.loads(self.seats)
            return v if isinstance(v, list) else []
        except (ValueError, TypeError):
            return []

    def seat_for_index(self, idx):
        """取第 idx 个航段（从0起）的座位号，越界返回空串"""
        lst = self.seat_list
        return lst[idx] if 0 <= idx < len(lst) else ''


class ProjectFlightSegment(db.Model):
    """机票航段信息表 - 3级表"""
    __tablename__ = 'project_flight_segments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False, comment='REF明细ID')

    # 航班信息
    flight_number = db.Column(db.String(10), nullable=False, comment='航班号')
    airline_name = db.Column(db.String(50), comment='航司名称')
    departure_airport = db.Column(db.String(3), nullable=False, comment='出发机场')
    arrival_airport = db.Column(db.String(3), nullable=False, comment='到达机场')
    departure_time = db.Column(db.DateTime, nullable=False, comment='起飞时间')
    arrival_time = db.Column(db.DateTime, nullable=False, comment='到达时间')
    departure_terminal = db.Column(db.String(50), comment='出发航站楼')
    arrival_terminal = db.Column(db.String(50), comment='到达航站楼')

    # 舱位信息
    cabin_class = db.Column(db.String(20), nullable=False, comment='舱位等级')
    cabin_code = db.Column(db.String(2), nullable=False, comment='舱位代码')
    baggage = db.Column(db.String(50), comment='行李额')
    seat = db.Column(db.String(10), comment='座位号')

    # 票号信息
    ticket_number = db.Column(db.String(50), comment='电子客票号')
    pnr = db.Column(db.String(10), comment='PNR编码')

    # 航段状态
    status = db.Column(db.String(20), nullable=False, default='pending', comment='航段状态')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ProjectFlightSegment {self.flight_number}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'ref_id': self.ref_id,
            'flight_number': self.flight_number,
            'airline_name': self.airline_name,
            'departure_airport': self.departure_airport,
            'arrival_airport': self.arrival_airport,
            'departure_time': self.departure_time.isoformat() if self.departure_time else None,
            'arrival_time': self.arrival_time.isoformat() if self.arrival_time else None,
            'departure_terminal': self.departure_terminal,
            'arrival_terminal': self.arrival_terminal,
            'cabin_class': self.cabin_class,
            'cabin_code': self.cabin_code,
            'baggage': self.baggage,
            'seat': self.seat,
            'ticket_number': self.ticket_number,
            'pnr': self.pnr,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
