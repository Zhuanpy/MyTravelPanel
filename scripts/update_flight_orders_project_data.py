#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新flight_orders表中的项目关联数据
"""

from App import create_app
from App.models.Flightmodels import FlightOrder
from App.models.projects.BookingProject import ProjectHeader, ProjectRef
from App.models.Product.BusinessType import BusinessType
from App.exts import db
from datetime import datetime
import traceback

def update_flight_orders_project_data():
    """更新flight_orders表的项目关联数据"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始更新flight_orders表的项目关联数据...")
            
            # 1. 查看现有数据情况
            total_orders = FlightOrder.query.count()
            orders_with_header = FlightOrder.query.filter(FlightOrder.project_header_id.isnot(None)).count()
            orders_with_ref = FlightOrder.query.filter(FlightOrder.project_ref_id.isnot(None)).count()
            orders_without_project = FlightOrder.query.filter(
                FlightOrder.project_header_id.is_(None),
                FlightOrder.project_ref_id.is_(None)
            ).count()
            
            print(f"数据统计:")
            print(f"  总订单数: {total_orders}")
            print(f"  已关联HID的订单: {orders_with_header}")
            print(f"  已关联REF的订单: {orders_with_ref}")
            print(f"  未关联项目的订单: {orders_without_project}")
            
            # 2. 查看现有项目数据
            total_headers = ProjectHeader.query.count()
            total_refs = ProjectRef.query.count()
            print(f"\n项目数据统计:")
            print(f"  项目主表(HID)数量: {total_headers}")
            print(f"  项目明细(REF)数量: {total_refs}")
            
            # 3. 获取机票业务类型ID
            airline_type = BusinessType.query.filter_by(code='airline').first()
            if not airline_type:
                print("警告: 未找到机票业务类型，将使用ID 1作为默认值")
                airline_type_id = 1
            else:
                airline_type_id = airline_type.id
                print(f"使用机票业务类型ID: {airline_type_id}")
            
            # 4. 为没有关联的订单创建项目
            orders_to_update = FlightOrder.query.filter(
                FlightOrder.project_header_id.is_(None)
            ).all()
            
            if not orders_to_update:
                print("所有订单都已关联项目，无需更新")
                return
            
            print(f"\n开始为 {len(orders_to_update)} 个订单创建项目...")
            
            created_headers = 0
            created_refs = 0
            
            for order in orders_to_update:
                try:
                    # 生成HID编号
                    hid = f"H{order.created_date.strftime('%Y%m%d')}{order.id:03d}"
                    
                    # 检查是否已存在相同的HID
                    existing_header = ProjectHeader.query.filter_by(hid=hid).first()
                    if existing_header:
                        print(f"  订单 {order.order_number}: HID {hid} 已存在，跳过")
                        continue
                    
                    # 创建项目主表记录
                    header = ProjectHeader(
                        hid=hid,
                        desc=f"机票订单项目 - {order.order_number}",
                        company_name=order.contact_person or "默认客户",
                        staff_name="系统管理员",
                        status="active",
                        created_at=order.created_date or datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.session.add(header)
                    db.session.flush()  # 获取header.id
                    
                    # 创建项目明细记录
                    ref = ProjectRef(
                        header_id=header.id,
                        ref_number=f"{hid}-R01",
                        name=f"机票订单 - {order.order_number}",
                        ref_type_id=airline_type_id,
                        description=f"机票订单：{order.order_number} - {order.passenger_name}",
                        supplier_id=None,
                        currency="SGD",
                        status="completed",
                        payment_status="paid",
                        created_at=order.created_date or datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.session.add(ref)
                    db.session.flush()  # 获取ref.id
                    
                    # 更新订单关联
                    order.project_header_id = header.id
                    order.project_ref_id = ref.id
                    
                    created_headers += 1
                    created_refs += 1
                    
                    print(f"  订单 {order.order_number}: 创建HID {hid} 和REF {ref.ref_number}")
                    
                except Exception as e:
                    print(f"  订单 {order.order_number}: 创建项目失败 - {str(e)}")
                    db.session.rollback()
                    continue
            
            # 提交所有更改
            db.session.commit()
            
            print(f"\n更新完成!")
            print(f"  创建的项目主表: {created_headers}")
            print(f"  创建的项目明细: {created_refs}")
            
            # 5. 验证更新结果
            total_orders_after = FlightOrder.query.count()
            orders_with_header_after = FlightOrder.query.filter(FlightOrder.project_header_id.isnot(None)).count()
            orders_with_ref_after = FlightOrder.query.filter(FlightOrder.project_ref_id.isnot(None)).count()
            orders_without_project_after = FlightOrder.query.filter(
                FlightOrder.project_header_id.is_(None),
                FlightOrder.project_ref_id.is_(None)
            ).count()
            
            print(f"\n更新后统计:")
            print(f"  总订单数: {total_orders_after}")
            print(f"  已关联HID的订单: {orders_with_header_after}")
            print(f"  已关联REF的订单: {orders_with_ref_after}")
            print(f"  未关联项目的订单: {orders_without_project_after}")
            
            if orders_without_project_after == 0:
                print("✅ 所有订单都已成功关联项目!")
            else:
                print(f"⚠️  仍有 {orders_without_project_after} 个订单未关联项目")
            
        except Exception as e:
            print(f"更新过程中发生错误: {str(e)}")
            print(traceback.format_exc())
            db.session.rollback()

if __name__ == "__main__":
    update_flight_orders_project_data() 