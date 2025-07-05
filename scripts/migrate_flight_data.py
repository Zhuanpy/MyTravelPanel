#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移flight_orders、passengers、flight_segments数据到新的项目结构
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.Flightmodels import FlightOrder, Passenger, FlightSegment
from App.models.projects.BookingProject import ProjectHeader, ProjectRef, ProjectFlightPassenger, ProjectFlightSegment
from App.models.Product.BusinessType import BusinessType
from App.models.Product.Suppliers import Supplier
from App.exts import db
from datetime import datetime
import traceback

def migrate_flight_data():
    """迁移机票数据到新的项目结构"""
    app = create_app()
    
    with app.app_context():
        print("=== 机票数据迁移 ===")
        
        try:
            # 1. 检查业务类型
            airline_type = BusinessType.query.filter_by(code='airline').first()
            if not airline_type:
                print("❌ 未找到机票业务类型，请先创建")
                return False
            
            print(f"✅ 使用机票业务类型: {airline_type.name} (ID: {airline_type.id})")
            
            # 2. 获取需要迁移的订单
            orders_to_migrate = FlightOrder.query.filter(
                FlightOrder.project_header_id.is_(None)
            ).all()
            
            if not orders_to_migrate:
                print("✅ 所有订单都已迁移，无需操作")
                return True
            
            print(f"📋 需要迁移 {len(orders_to_migrate)} 个订单")
            
            # 3. 确认迁移
            response = input(f"\n是否开始迁移？(y/N): ")
            if response.lower() != 'y':
                print("❌ 取消迁移操作")
                return False
            
            # 4. 开始迁移
            migrated_count = 0
            error_count = 0
            
            for i, order in enumerate(orders_to_migrate, 1):
                try:
                    print(f"\n[{i}/{len(orders_to_migrate)}] 迁移订单: {order.order_number}")
                    
                    # 4.1 生成HID编号
                    hid = ProjectHeader.generate_hid()
                    
                    # 4.2 映射状态值
                    def map_status(old_status):
                        """映射状态值"""
                        status_mapping = {
                            'pending': 'active',
                            'confirmed': 'active', 
                            'processing': 'active',
                            'completed': 'completed',
                            'cancelled': 'cancelled',
                            'draft': 'draft'
                        }
                        return status_mapping.get(old_status, 'active')
                    
                    # 4.3 创建项目主表
                    header = ProjectHeader(
                        hid=hid,
                        desc=f"机票订单项目 - {order.order_number}",
                        company_name=order.contact_name or "默认客户",
                        contact=order.contact_name,
                        staff_name="系统管理员",
                        currency="SGD",
                        type="机票",
                        source="数据迁移",
                        status=map_status(order.status),
                        created_at=order.created_date or datetime.now(),
                        updated_at=datetime.now(),
                        last_updated_by="数据迁移"
                    )
                    db.session.add(header)
                    db.session.flush()  # 获取header.id
                    
                    # 4.3 生成REF编号
                    ref_number = ProjectRef.generate_ref_number()
                    
                    # 4.4 查找或创建供应商
                    supplier_id = None
                    if order.supplier_name:
                        supplier = Supplier.query.filter_by(name=order.supplier_name).first()
                        if not supplier:
                            # 创建新供应商
                            supplier = Supplier(
                                name=order.supplier_name,
                                supplier_type="flight",
                                contact_person=order.contact_name,
                                phone=order.contact_phone,
                                email="",
                                address="",
                                status="active",
                                created_at=datetime.now(),
                                last_updated=datetime.now()
                            )
                            db.session.add(supplier)
                            db.session.flush()
                        supplier_id = supplier.supplier_id
                    
                    # 4.6 映射REF状态值
                    def map_ref_status(old_status):
                        """映射REF状态值"""
                        ref_status_mapping = {
                            'pending': 'processing',
                            'confirmed': 'processing',
                            'processing': 'processing',
                            'completed': 'completed',
                            'cancelled': 'cancelled',
                            'draft': 'draft'
                        }
                        return ref_status_mapping.get(old_status, 'completed')
                    
                    def map_payment_status(old_payment_status):
                        """映射支付状态值"""
                        payment_status_mapping = {
                            'pending': 'unpaid',
                            'partial': 'partial',
                            'paid': 'paid',
                            'refunded': 'refunded'
                        }
                        return payment_status_mapping.get(old_payment_status, 'paid')
                    
                    # 4.7 创建项目明细
                    ref = ProjectRef(
                        header_id=header.id,
                        ref_number=ref_number,
                        name=f"机票订单 - {order.order_number}",
                        ref_type_id=airline_type.id,
                        description=f"机票订单：{order.order_number} - {order.passenger_name}",
                        supplier_id=supplier_id,
                        supplier_contact=order.contact_name,
                        supplier_phone=order.contact_phone,
                        contact_name=order.contact_name,
                        contact_phone=order.contact_phone,
                        selling_price=order.selling_price,
                        cost_price=order.cost_price,
                        currency="SGD",
                        expected_delivery_date=order.departure_date,
                        status=map_ref_status(order.status),
                        payment_status=map_payment_status(order.payment_status),
                        remarks=order.remarks,
                        created_at=order.created_date or datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.session.add(ref)
                    db.session.flush()  # 获取ref.id
                    
                    # 4.6 迁移乘客数据
                    passengers = Passenger.query.filter_by(order_id=order.id).all()
                    for passenger in passengers:
                        new_passenger = ProjectFlightPassenger(
                            ref_id=ref.id,
                            name=passenger.name,
                            passenger_type=passenger.passenger_type,
                            selling_price=passenger.selling_price,
                            cost_price=passenger.cost_price,
                            ticket_number=passenger.ticket_number,
                            pnr=passenger.pnr,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db.session.add(new_passenger)
                    
                    # 4.7 迁移航段数据
                    segments = FlightSegment.query.filter_by(order_id=order.id).all()
                    for segment in segments:
                        new_segment = ProjectFlightSegment(
                            ref_id=ref.id,
                            flight_number=segment.flight_number,
                            departure_airport=segment.departure_airport,
                            arrival_airport=segment.arrival_airport,
                            departure_time=segment.departure_time,
                            arrival_time=segment.arrival_time,
                            cabin_class=segment.cabin_class,
                            cabin_code=segment.cabin_code,
                            status=segment.status,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db.session.add(new_segment)
                    
                    # 4.8 更新原订单的关联关系
                    order.project_header_id = header.id
                    order.project_ref_id = ref.id
                    
                    migrated_count += 1
                    print(f"  ✅ 成功迁移: HID={hid}, REF={ref_number}")
                    print(f"     乘客: {len(passengers)} 人, 航段: {len(segments)} 个")
                    
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ 迁移失败: {str(e)}")
                    db.session.rollback()
                    continue
            
            # 5. 提交所有更改
            db.session.commit()
            
            # 6. 输出迁移结果
            print(f"\n=== 迁移完成 ===")
            print(f"✅ 成功迁移: {migrated_count} 个订单")
            print(f"❌ 迁移失败: {error_count} 个订单")
            
            # 7. 验证迁移结果
            print(f"\n=== 验证结果 ===")
            total_headers = ProjectHeader.query.count()
            total_refs = ProjectRef.query.count()
            total_passengers = ProjectFlightPassenger.query.count()
            total_segments = ProjectFlightSegment.query.count()
            
            print(f"项目主表: {total_headers} 条")
            print(f"项目明细: {total_refs} 条")
            print(f"乘客信息: {total_passengers} 条")
            print(f"航段信息: {total_segments} 条")
            
            # 8. 显示示例数据
            if migrated_count > 0:
                print(f"\n=== 示例迁移数据 ===")
                latest_header = ProjectHeader.query.order_by(ProjectHeader.id.desc()).first()
                if latest_header:
                    print(f"最新项目: {latest_header.hid} - {latest_header.desc}")
                    if latest_header.refs:
                        ref = latest_header.refs[0]
                        print(f"REF: {ref.ref_number} - {ref.name}")
                        print(f"乘客数: {len(ref.flight_passengers)}")
                        print(f"航段数: {len(ref.flight_segments)}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 迁移过程中发生错误: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")
            return False

if __name__ == "__main__":
    migrate_flight_data() 