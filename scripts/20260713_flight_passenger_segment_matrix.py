# -*- coding: utf-8 -*-
"""建「乘客×航段」交叉表 project_flight_passenger_segments，并迁移老数据。

背景：PNR / 票号 / 行李 原先只存在乘客上（全程一个值），座位存在乘客的 seats
JSON 列表里（靠下标对齐航段 id 升序）。现在四个字段统一按「乘客×航段」存到
交叉表，格子留空 = 继承乘客级默认值。

本脚本做两件事：
  1. 建表（已存在则跳过）
  2. 把每个乘客的 seats JSON 按下标拆到对应航段的格子里

注意：乘客级的 pnr / ticket_number / baggage **不搬**——它们保留在乘客表上作为
默认值，格子留空时自动继承，显示效果不变。只有座位必须搬，因为它没有默认值可继承。

运行：python scripts/20260713_flight_passenger_segment_matrix.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from App_new import create_app
from App_new.exts import db
from App_new.business.flight.models.flight import (
    ProjectFlightPassenger, ProjectFlightSegment, ProjectFlightPassengerSegment
)

TABLE = ProjectFlightPassengerSegment.__tablename__


def create_table():
    """建交叉表（已存在则跳过）"""
    inspector = inspect(db.engine)
    if TABLE in inspector.get_table_names():
        print(f'[跳过] 表 {TABLE} 已存在')
        return
    ProjectFlightPassengerSegment.__table__.create(db.engine)
    print(f'[建表] {TABLE}')


def legacy_seat_lists():
    """读老的 passenger.seats JSON 列（模型上已删掉这个字段，直接走 SQL）

    返回 {passenger_id: [座位, ...]}；表里没有 seats 列（全新库）时返回空字典。
    """
    inspector = inspect(db.engine)
    columns = {c['name'] for c in inspector.get_columns(ProjectFlightPassenger.__tablename__)}
    if 'seats' not in columns:
        print('[跳过] 乘客表没有 seats 列，无老座位数据可迁移')
        return {}

    result = {}
    rows = db.session.execute(
        text(f'SELECT id, seats FROM {ProjectFlightPassenger.__tablename__} '
             f'WHERE seats IS NOT NULL AND seats != ""')
    )
    for pid, raw in rows:
        try:
            seats = json.loads(raw)
        except (ValueError, TypeError):
            print(f'[警告] 乘客 {pid} 的 seats 不是合法 JSON，跳过：{raw!r}')
            continue
        if isinstance(seats, list) and any(seats):
            result[pid] = seats
    return result


def migrate_seats():
    """把 seats JSON 按下标拆成 乘客×航段 的座位格子"""
    seat_map = legacy_seat_lists()
    if not seat_map:
        return

    # 每个 REF 的航段按 id 升序 —— 这是老 seats 列表的下标口径
    segments_by_ref = {}
    for seg in ProjectFlightSegment.query.order_by(ProjectFlightSegment.id).all():
        segments_by_ref.setdefault(seg.ref_id, []).append(seg)

    created = 0
    skipped = 0
    for passenger in ProjectFlightPassenger.query.all():
        seats = seat_map.get(passenger.id)
        if not seats:
            continue

        segments = segments_by_ref.get(passenger.ref_id, [])
        if len(seats) > len(segments):
            print(f'[警告] 乘客 {passenger.id}（REF {passenger.ref_id}）有 {len(seats)} 个座位'
                  f'但只有 {len(segments)} 个航段，多出的座位丢弃：{seats[len(segments):]}')

        for idx, seat in enumerate(seats):
            seat = (seat or '').strip()
            if not seat or idx >= len(segments):
                continue
            segment = segments[idx]
            if passenger.cell_for(segment):
                skipped += 1  # 已有格子（脚本重跑）
                continue
            db.session.add(ProjectFlightPassengerSegment(
                ref_id=passenger.ref_id,
                passenger_id=passenger.id,
                segment_id=segment.id,
                seat=seat[:10],
            ))
            created += 1

    db.session.commit()
    print(f'[迁移] 座位格子 新建 {created} 条，跳过已存在 {skipped} 条')


def main():
    app = create_app()
    with app.app_context():
        create_table()
        migrate_seats()
        print('完成。乘客级 PNR/票号/行李 保留原位作为默认值，无需搬迁。')


if __name__ == '__main__':
    main()
