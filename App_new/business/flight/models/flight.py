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

    # 票务信息（乘客级默认值：航段格子留空时继承这里）
    ticket_number = db.Column(db.String(50), comment='电子客票号(默认值)')
    pnr = db.Column(db.String(10), comment='PNR编码(默认值)')
    baggage = db.Column(db.String(50), comment='行李额(默认值)')

    # 证件信息
    passport_number = db.Column(db.String(20), comment='护照号')

    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 乘客×航段 明细格子
    segment_cells = db.relationship(
        'ProjectFlightPassengerSegment',
        backref='passenger',
        lazy='select',
        cascade='all, delete-orphan'
    )

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
            'passport_number': self.passport_number,
            'segments': [c.to_dict() for c in sorted(self.segment_cells, key=lambda x: x.segment_id or 0)],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def cell_for(self, segment):
        """取该乘客在指定航段上的格子，没有则返回 None。segment 可传对象或 id"""
        segment_id = getattr(segment, 'id', segment)
        if not segment_id:
            return None
        for c in self.segment_cells:
            if c.segment_id == segment_id:
                return c
        return None

    def _resolve(self, segment, field, passenger_default):
        """取值链：乘客×航段格子 → 乘客级默认值 → 航段级遗留值

        最后一级是为了兼容老数据：机票订单页（order_create/order_edit）至今仍把
        PNR/票号/行李/座位写在航段上，全体乘客共用。新的 REF 录入不再写那里。
        """
        cell = self.cell_for(segment)
        value = getattr(cell, field, None) if cell else None
        legacy = getattr(segment, field, None) if not isinstance(segment, int) else None
        return value or passenger_default or legacy or ''

    def pnr_for(self, segment):
        """该乘客在指定航段的 PNR"""
        return self._resolve(segment, 'pnr', self.pnr)

    def ticket_number_for(self, segment):
        """该乘客在指定航段的票号"""
        return self._resolve(segment, 'ticket_number', self.ticket_number)

    def baggage_for(self, segment):
        """该乘客在指定航段的行李额"""
        return self._resolve(segment, 'baggage', self.baggage)

    def seat_for(self, segment):
        """该乘客在指定航段的座位号（座位没有乘客级默认值）"""
        return self._resolve(segment, 'seat', None)


class ProjectFlightPassengerSegment(db.Model):
    """乘客×航段 明细表 - 4级表

    每个「乘客 × 航段」一行，存该乘客在该航段上的 PNR / 票号 / 座位 / 行李。
    四个字段均可留空，留空表示继承 ProjectFlightPassenger 上的乘客级默认值
    （座位除外，座位没有默认值）。
    """
    __tablename__ = 'project_flight_passenger_segments'
    __table_args__ = (
        db.UniqueConstraint('passenger_id', 'segment_id', name='uq_pax_segment'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 冗余 ref_id：乘客/航段是「先删后建」，按 ref_id 批量清理格子最省事
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False, index=True, comment='REF明细ID')
    passenger_id = db.Column(db.Integer, db.ForeignKey('project_flight_passengers.id'), nullable=False, comment='乘客ID')
    segment_id = db.Column(db.Integer, db.ForeignKey('project_flight_segments.id'), nullable=False, comment='航段ID')

    pnr = db.Column(db.String(10), comment='PNR编码(留空继承乘客级)')
    ticket_number = db.Column(db.String(50), comment='电子客票号(留空继承乘客级)')
    seat = db.Column(db.String(10), comment='座位号')
    baggage = db.Column(db.String(50), comment='行李额(留空继承乘客级)')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ProjectFlightPassengerSegment pax={self.passenger_id} seg={self.segment_id}>'

    def is_empty(self):
        """四个字段全空 = 这个格子没有任何覆盖值，可以不落库"""
        return not any([self.pnr, self.ticket_number, self.seat, self.baggage])

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'passenger_id': self.passenger_id,
            'segment_id': self.segment_id,
            'pnr': self.pnr,
            'ticket_number': self.ticket_number,
            'seat': self.seat,
            'baggage': self.baggage
        }


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
    # 以下四个字段是航段级（全体乘客共用），已被 project_flight_passenger_segments 取代。
    # REF 录入不再写入，仅作为老数据的最后一级回退（见 ProjectFlightPassenger._resolve）。
    baggage = db.Column(db.String(50), comment='行李额(遗留,全体乘客共用)')
    seat = db.Column(db.String(10), comment='座位号(遗留,全体乘客共用)')
    ticket_number = db.Column(db.String(50), comment='电子客票号(遗留,全体乘客共用)')
    pnr = db.Column(db.String(10), comment='PNR编码(遗留,全体乘客共用)')

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
