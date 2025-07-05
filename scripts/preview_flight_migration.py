#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览机票数据迁移计划
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

def preview_flight_migration():
    """预览机票数据迁移计划"""
    app = create_app()
    
    with app.app_context():
        print("=== 机票数据迁移预览 ===")
        
        # 1. 检查业务类型
        airline_type = BusinessType.query.filter_by(code='airline').first()
        if not airline_type:
            print("❌ 未找到机票业务类型，请先创建")
            return False
        
        print(f"✅ 机票业务类型: {airline_type.name} (ID: {airline_type.id})")
        
        # 2. 获取需要迁移的订单
        orders_to_migrate = FlightOrder.query.filter(
            FlightOrder.project_header_id.is_(None)
        ).all()
        
        if not orders_to_migrate:
            print("✅ 所有订单都已迁移，无需操作")
            return True
        
        print(f"\n📋 需要迁移 {len(orders_to_migrate)} 个订单")
        
        # 3. 显示迁移计划
        print(f"\n=== 迁移计划 ===")
        print("源表 → 目标表:")
        print("  flight_orders → project_headers + project_refs")
        print("  passengers → project_flight_passengers")
        print("  flight_segments → project_flight_segments")
        
        # 4. 显示字段映射
        print(f"\n=== 字段映射详情 ===")
        print("flight_orders → project_headers:")
        print("  order_number → 生成HID编号")
        print("  passenger_name → desc (项目描述)")
        print("  contact_name → company_name (公司名称)")
        print("  contact_phone → contact (联系人)")
        print("  status → status (状态)")
        print("  created_date → created_at (创建时间)")
        
        print("\nflight_orders → project_refs:")
        print("  order_number → name (REF名称)")
        print("  passenger_name → description (描述)")
        print("  contact_name → contact_name (联系人)")
        print("  contact_phone → contact_phone (联系电话)")
        print("  supplier_name → supplier_id (供应商ID)")
        print("  selling_price → selling_price (销售价格)")
        print("  cost_price → cost_price (成本价格)")
        print("  status → status (状态)")
        print("  payment_status → payment_status (支付状态)")
        print("  departure_date → expected_delivery_date (预计交付日期)")
        
        print("\npassengers → project_flight_passengers:")
        print("  name → name (乘客姓名)")
        print("  passenger_type → passenger_type (乘客类型)")
        print("  selling_price → selling_price (售价)")
        print("  cost_price → cost_price (成本)")
        print("  ticket_number → ticket_number (电子客票号)")
        print("  pnr → pnr (PNR编码)")
        
        print("\nflight_segments → project_flight_segments:")
        print("  flight_number → flight_number (航班号)")
        print("  departure_airport → departure_airport (出发机场)")
        print("  arrival_airport → arrival_airport (到达机场)")
        print("  departure_time → departure_time (起飞时间)")
        print("  arrival_time → arrival_time (到达时间)")
        print("  cabin_class → cabin_class (舱位等级)")
        print("  cabin_code → cabin_code (舱位代码)")
        print("  status → status (航段状态)")
        
        # 5. 显示示例数据
        print(f"\n=== 示例迁移数据 ===")
        sample_orders = orders_to_migrate[:3]  # 显示前3个订单
        
        for i, order in enumerate(sample_orders, 1):
            print(f"\n订单 {i}: {order.order_number}")
            print(f"  乘客姓名: {order.passenger_name}")
            print(f"  联系人: {order.contact_name}")
            print(f"  供应商: {order.supplier_name or '无'}")
            print(f"  出发日期: {order.departure_date}")
            print(f"  售价: {order.selling_price}")
            print(f"  成本: {order.cost_price}")
            print(f"  状态: {order.status}")
            
            # 乘客信息
            passengers = Passenger.query.filter_by(order_id=order.id).all()
            print(f"  乘客数: {len(passengers)}")
            for j, passenger in enumerate(passengers[:2], 1):  # 只显示前2个乘客
                print(f"    乘客{j}: {passenger.name} ({passenger.passenger_type})")
                print(f"      售价: {passenger.selling_price}, 成本: {passenger.cost_price}")
            
            # 航段信息
            segments = FlightSegment.query.filter_by(order_id=order.id).all()
            print(f"  航段数: {len(segments)}")
            for j, segment in enumerate(segments[:2], 1):  # 只显示前2个航段
                print(f"    航段{j}: {segment.flight_number}")
                print(f"      {segment.departure_airport} → {segment.arrival_airport}")
                print(f"      时间: {segment.departure_time} - {segment.arrival_time}")
                print(f"      舱位: {segment.cabin_class} ({segment.cabin_code})")
        
        if len(orders_to_migrate) > 3:
            print(f"\n... 还有 {len(orders_to_migrate) - 3} 个订单")
        
        # 6. 显示统计信息
        print(f"\n=== 数据统计 ===")
        total_passengers = Passenger.query.count()
        total_segments = FlightSegment.query.count()
        
        print(f"总乘客数: {total_passengers}")
        print(f"总航段数: {total_segments}")
        print(f"平均每订单乘客数: {total_passengers / len(orders_to_migrate):.1f}")
        print(f"平均每订单航段数: {total_segments / len(orders_to_migrate):.1f}")
        
        # 7. 显示当前项目数据
        print(f"\n=== 当前项目数据 ===")
        current_headers = ProjectHeader.query.count()
        current_refs = ProjectRef.query.count()
        current_passengers = ProjectFlightPassenger.query.count()
        current_segments = ProjectFlightSegment.query.count()
        
        print(f"现有项目主表: {current_headers}")
        print(f"现有项目明细: {current_refs}")
        print(f"现有乘客信息: {current_passengers}")
        print(f"现有航段信息: {current_segments}")
        
        # 8. 迁移后预估
        print(f"\n=== 迁移后预估 ===")
        print(f"项目主表: {current_headers} → {current_headers + len(orders_to_migrate)}")
        print(f"项目明细: {current_refs} → {current_refs + len(orders_to_migrate)}")
        print(f"乘客信息: {current_passengers} → {current_passengers + total_passengers}")
        print(f"航段信息: {current_segments} → {current_segments + total_segments}")
        
        # 9. 注意事项
        print(f"\n=== 注意事项 ===")
        print("⚠️  迁移过程中会:")
        print("  - 为每个订单创建新的HID和REF编号")
        print("  - 自动创建不存在的供应商")
        print("  - 保持原有的数据关联关系")
        print("  - 更新原订单的project_header_id和project_ref_id")
        
        print("\n⚠️  建议:")
        print("  - 在迁移前备份数据库")
        print("  - 分批迁移大量数据")
        print("  - 迁移后验证数据完整性")
        
        print(f"\n✅ 预览完成")
        print(f"运行 'python scripts/migrate_flight_data.py' 开始迁移")

if __name__ == "__main__":
    preview_flight_migration() 