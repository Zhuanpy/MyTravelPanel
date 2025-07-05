#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析flight_orders、passengers、flight_segments表的数据结构
并分析如何迁移到project_headers、project_flight_passengers、project_flight_segments
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.Flightmodels import FlightOrder, Passenger, FlightSegment
from App.models.projects.BookingProject import ProjectHeader, ProjectRef, ProjectFlightPassenger, ProjectFlightSegment
from App.models.Product.BusinessType import BusinessType
from App.exts import db
from datetime import datetime

def analyze_flight_data_migration():
    """分析机票数据迁移"""
    app = create_app()
    
    with app.app_context():
        print("=== 机票数据迁移分析 ===")
        
        # 1. 分析源表数据
        print("\n1. 源表数据分析:")
        print("-" * 50)
        
        # flight_orders表
        total_orders = FlightOrder.query.count()
        print(f"flight_orders表: {total_orders} 条记录")
        
        if total_orders > 0:
            sample_order = FlightOrder.query.first()
            print(f"示例订单字段:")
            print(f"  - order_number: {sample_order.order_number}")
            print(f"  - passenger_name: {sample_order.passenger_name}")
            print(f"  - contact_name: {sample_order.contact_name}")
            print(f"  - supplier_name: {sample_order.supplier_name}")
            print(f"  - departure_date: {sample_order.departure_date}")
            print(f"  - selling_price: {sample_order.selling_price}")
            print(f"  - cost_price: {sample_order.cost_price}")
            print(f"  - status: {sample_order.status}")
            print(f"  - created_date: {sample_order.created_date}")
        
        # passengers表
        total_passengers = Passenger.query.count()
        print(f"\npassengers表: {total_passengers} 条记录")
        
        if total_passengers > 0:
            sample_passenger = Passenger.query.first()
            print(f"示例乘客字段:")
            print(f"  - name: {sample_passenger.name}")
            print(f"  - passenger_type: {sample_passenger.passenger_type}")
            print(f"  - selling_price: {sample_passenger.selling_price}")
            print(f"  - cost_price: {sample_passenger.cost_price}")
            print(f"  - ticket_number: {sample_passenger.ticket_number}")
            print(f"  - pnr: {sample_passenger.pnr}")
        
        # flight_segments表
        total_segments = FlightSegment.query.count()
        print(f"\nflight_segments表: {total_segments} 条记录")
        
        if total_segments > 0:
            sample_segment = FlightSegment.query.first()
            print(f"示例航段字段:")
            print(f"  - flight_number: {sample_segment.flight_number}")
            print(f"  - departure_airport: {sample_segment.departure_airport}")
            print(f"  - arrival_airport: {sample_segment.arrival_airport}")
            print(f"  - departure_time: {sample_segment.departure_time}")
            print(f"  - arrival_time: {sample_segment.arrival_time}")
            print(f"  - cabin_class: {sample_segment.cabin_class}")
            print(f"  - cabin_code: {sample_segment.cabin_code}")
            print(f"  - status: {sample_segment.status}")
        
        # 2. 分析目标表结构
        print("\n2. 目标表结构分析:")
        print("-" * 50)
        
        # project_headers表
        total_headers = ProjectHeader.query.count()
        print(f"project_headers表: {total_headers} 条记录")
        
        # project_refs表
        total_refs = ProjectRef.query.count()
        print(f"project_refs表: {total_refs} 条记录")
        
        # project_flight_passengers表
        total_new_passengers = ProjectFlightPassenger.query.count()
        print(f"project_flight_passengers表: {total_new_passengers} 条记录")
        
        # project_flight_segments表
        total_new_segments = ProjectFlightSegment.query.count()
        print(f"project_flight_segments表: {total_new_segments} 条记录")
        
        # 3. 字段映射分析
        print("\n3. 字段映射分析:")
        print("-" * 50)
        
        print("flight_orders → project_headers 映射:")
        print("  ✅ order_number → 可用于生成HID")
        print("  ✅ passenger_name → desc (项目描述)")
        print("  ✅ contact_name → company_name (公司名称)")
        print("  ✅ supplier_name → 需要查找或创建供应商")
        print("  ✅ selling_price → 不直接映射，需要计算")
        print("  ✅ cost_price → 不直接映射，需要计算")
        print("  ✅ status → status (状态)")
        print("  ✅ created_date → created_at (创建时间)")
        
        print("\nflight_orders → project_refs 映射:")
        print("  ✅ order_number → name (REF名称)")
        print("  ✅ passenger_name → description (描述)")
        print("  ✅ contact_name → contact_name (联系人)")
        print("  ✅ contact_phone → contact_phone (联系电话)")
        print("  ✅ supplier_name → 需要查找supplier_id")
        print("  ✅ selling_price → selling_price (销售价格)")
        print("  ✅ cost_price → cost_price (成本价格)")
        print("  ✅ status → status (状态)")
        print("  ✅ payment_status → payment_status (支付状态)")
        print("  ✅ created_date → created_at (创建时间)")
        
        print("\npassengers → project_flight_passengers 映射:")
        print("  ✅ name → name (乘客姓名)")
        print("  ✅ passenger_type → passenger_type (乘客类型)")
        print("  ✅ selling_price → selling_price (售价)")
        print("  ✅ cost_price → cost_price (成本)")
        print("  ✅ ticket_number → ticket_number (电子客票号)")
        print("  ✅ pnr → pnr (PNR编码)")
        
        print("\nflight_segments → project_flight_segments 映射:")
        print("  ✅ flight_number → flight_number (航班号)")
        print("  ✅ departure_airport → departure_airport (出发机场)")
        print("  ✅ arrival_airport → arrival_airport (到达机场)")
        print("  ✅ departure_time → departure_time (起飞时间)")
        print("  ✅ arrival_time → arrival_time (到达时间)")
        print("  ✅ cabin_class → cabin_class (舱位等级)")
        print("  ✅ cabin_code → cabin_code (舱位代码)")
        print("  ✅ status → status (航段状态)")
        
        # 4. 数据关联分析
        print("\n4. 数据关联分析:")
        print("-" * 50)
        
        # 分析订单与乘客的关联
        orders_with_passengers = db.session.query(FlightOrder).join(Passenger).distinct().count()
        print(f"有乘客信息的订单: {orders_with_passengers}")
        
        # 分析订单与航段的关联
        orders_with_segments = db.session.query(FlightOrder).join(FlightSegment).distinct().count()
        print(f"有航段信息的订单: {orders_with_segments}")
        
        # 分析完整的订单（既有乘客又有航段）
        complete_orders = db.session.query(FlightOrder).join(Passenger).join(FlightSegment).distinct().count()
        print(f"完整的订单（有乘客和航段）: {complete_orders}")
        
        # 5. 迁移策略建议
        print("\n5. 迁移策略建议:")
        print("-" * 50)
        
        print("迁移步骤:")
        print("1. 为每个flight_order创建project_header")
        print("2. 为每个project_header创建project_ref（机票类型）")
        print("3. 将passengers数据迁移到project_flight_passengers")
        print("4. 将flight_segments数据迁移到project_flight_segments")
        print("5. 更新关联关系")
        
        print("\n注意事项:")
        print("- 需要确保机票业务类型存在")
        print("- 需要处理供应商信息的映射")
        print("- 需要保持数据的完整性和一致性")
        print("- 建议分批迁移，避免数据量过大")
        
        # 6. 检查业务类型
        print("\n6. 业务类型检查:")
        print("-" * 50)
        
        airline_type = BusinessType.query.filter_by(code='airline').first()
        if airline_type:
            print(f"✅ 找到机票业务类型: {airline_type.name} (ID: {airline_type.id})")
        else:
            print("❌ 未找到机票业务类型，需要先创建")
        
        # 7. 数据完整性检查
        print("\n7. 数据完整性检查:")
        print("-" * 50)
        
        # 检查是否有重复的订单号
        duplicate_orders = db.session.query(FlightOrder.order_number).group_by(FlightOrder.order_number).having(db.func.count(FlightOrder.id) > 1).count()
        print(f"重复订单号: {duplicate_orders}")
        
        # 检查是否有空值的关键字段
        orders_without_passenger = FlightOrder.query.filter(FlightOrder.passenger_name.is_(None)).count()
        print(f"缺少乘客姓名的订单: {orders_without_passenger}")
        
        orders_without_contact = FlightOrder.query.filter(FlightOrder.contact_name.is_(None)).count()
        print(f"缺少联系人的订单: {orders_without_contact}")
        
        print("\n✅ 分析完成")

if __name__ == "__main__":
    analyze_flight_data_migration() 