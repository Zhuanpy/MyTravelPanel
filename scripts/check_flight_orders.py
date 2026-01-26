# -*- coding: utf-8 -*-
"""检查机票订单数据完整性"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.flight.models.models import FlightOrder, FlightSegment, Passenger

app = create_app()

with app.app_context():
    # 统计各种问题
    total_orders = FlightOrder.query.count()

    # 没有航段的订单
    orders_without_segments = FlightOrder.query.filter(
        ~FlightOrder.id.in_(db.session.query(FlightSegment.order_id).distinct())
    ).count()

    # 没有乘客的订单
    orders_without_passengers = FlightOrder.query.filter(
        ~FlightOrder.id.in_(db.session.query(Passenger.order_id).distinct())
    ).count()

    # 没有联系人的订单
    orders_without_contact = FlightOrder.query.filter(
        db.or_(
            FlightOrder.contact_name.is_(None),
            FlightOrder.contact_name == '',
            FlightOrder.contact_name == 'None'
        )
    ).count()

    # 没有行程的订单
    orders_without_itinerary = FlightOrder.query.filter(
        db.or_(
            FlightOrder.itinerary.is_(None),
            FlightOrder.itinerary == ''
        )
    ).count()

    # 没有出发日期的订单
    orders_without_date = FlightOrder.query.filter(
        FlightOrder.departure_date.is_(None)
    ).count()

    # 没有乘客名的订单
    orders_without_passenger_name = FlightOrder.query.filter(
        db.or_(
            FlightOrder.passenger_name.is_(None),
            FlightOrder.passenger_name == '',
            FlightOrder.passenger_name == 'None'
        )
    ).count()

    print("=" * 60)
    print("机票订单数据完整性检查")
    print("=" * 60)
    print(f"总订单数: {total_orders}")
    print(f"缺少航段: {orders_without_segments}")
    print(f"缺少乘客记录: {orders_without_passengers}")
    print(f"缺少联系人: {orders_without_contact}")
    print(f"缺少行程: {orders_without_itinerary}")
    print(f"缺少出发日期: {orders_without_date}")
    print(f"缺少乘客名: {orders_without_passenger_name}")

    # 显示几个有问题的订单示例
    print("\n" + "-" * 60)
    print("问题订单示例（前5条）:")
    print("-" * 60)

    problem_orders = FlightOrder.query.filter(
        db.or_(
            FlightOrder.contact_name.is_(None),
            FlightOrder.contact_name == '',
            FlightOrder.contact_name == 'None',
            FlightOrder.passenger_name.is_(None),
            FlightOrder.passenger_name == '',
            FlightOrder.passenger_name == 'None'
        )
    ).limit(5).all()

    for order in problem_orders:
        segments_count = FlightSegment.query.filter_by(order_id=order.id).count()
        passengers_count = Passenger.query.filter_by(order_id=order.id).count()
        print(f"\n订单: {order.order_number}")
        print(f"  REF ID: {order.project_ref_id}")
        print(f"  乘客名(passenger_name): '{order.passenger_name}'")
        print(f"  联系人(contact_name): '{order.contact_name}'")
        print(f"  行程(itinerary): '{order.itinerary}'")
        print(f"  出发日期: {order.departure_date}")
        print(f"  航段数: {segments_count}")
        print(f"  乘客记录数: {passengers_count}")
