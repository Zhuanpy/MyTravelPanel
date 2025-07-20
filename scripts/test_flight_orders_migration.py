#!/usr/bin/env python3
"""
测试机票订单列表数据迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.BookingProject import ProjectFlightSegment, ProjectRef, ProjectHeader, ProjectFlightPassenger
from App.models.Product.BusinessType import BusinessType

def test_flight_orders_migration():
    """测试机票订单列表数据迁移"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始测试机票订单列表数据迁移...")
            
            # 1. 检查业务类型
            print("\n=== 检查业务类型 ===")
            business_types = BusinessType.query.all()
            for bt in business_types:
                print(f"ID: {bt.id}, 名称: {bt.name}, 代码: {bt.code}")
            
            # 2. 检查机票相关的REF数量
            print("\n=== 检查机票REF数量 ===")
            flight_refs = ProjectRef.query.filter_by(ref_type_id=1).count()
            print(f"机票REF总数: {flight_refs}")
            
            # 3. 检查航段数据
            print("\n=== 检查航段数据 ===")
            flight_segments = ProjectFlightSegment.query.count()
            print(f"航段总数: {flight_segments}")
            
            # 4. 检查乘客数据
            print("\n=== 检查乘客数据 ===")
            passengers = ProjectFlightPassenger.query.count()
            print(f"乘客总数: {passengers}")
            
            # 5. 测试查询逻辑
            print("\n=== 测试查询逻辑 ===")
            query = db.session.query(
                ProjectRef,
                ProjectHeader,
                db.func.count(ProjectFlightPassenger.id).label('passenger_count'),
                db.func.sum(ProjectFlightPassenger.selling_price).label('total_selling_price'),
                db.func.sum(ProjectFlightPassenger.cost_price).label('total_cost_price'),
                db.func.min(ProjectFlightSegment.departure_time).label('first_departure_time'),
                db.func.max(ProjectFlightSegment.arrival_time).label('last_arrival_time')
            ).join(
                ProjectHeader, ProjectRef.header_id == ProjectHeader.id
            ).outerjoin(
                ProjectFlightPassenger, ProjectRef.id == ProjectFlightPassenger.ref_id
            ).outerjoin(
                ProjectFlightSegment, ProjectRef.id == ProjectFlightSegment.ref_id
            ).filter(
                ProjectRef.ref_type_id == 1  # 机票业务类型ID
            ).group_by(
                ProjectRef.id,
                ProjectHeader.id
            ).order_by(ProjectRef.created_at.desc()).limit(5)
            
            results = query.all()
            print(f"查询结果数量: {len(results)}")
            
            for i, result in enumerate(results, 1):
                ref, header, passenger_count, total_selling, total_cost, first_departure_time, last_arrival_time = result
                print(f"\n订单 {i}:")
                print(f"  REF编号: {ref.ref_number}")
                print(f"  联系人: {ref.contact_name}")
                print(f"  供应商: {ref.supplier.name if ref.supplier else '未指定'}")
                print(f"  乘客数: {passenger_count}")
                print(f"  总售价: {float(total_selling) if total_selling else 0}")
                print(f"  总成本: {float(total_cost) if total_cost else 0}")
                print(f"  状态: {ref.status}")
                print(f"  支付状态: {ref.payment_status}")
                print(f"  首次出发时间: {first_departure_time}")
                print(f"  最后到达时间: {last_arrival_time}")
                
                # 获取航段信息
                segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).order_by(ProjectFlightSegment.departure_time).all()
                print(f"  航段数: {len(segments)}")
                for j, segment in enumerate(segments, 1):
                    print(f"    航段{j}: {segment.departure_airport} → {segment.arrival_airport} ({segment.flight_number})")
            
            # 6. 检查数据完整性
            print("\n=== 检查数据完整性 ===")
            
            # 检查是否有REF但没有航段
            refs_without_segments = db.session.query(ProjectRef).filter(
                ProjectRef.ref_type_id == 1,
                ~ProjectRef.id.in_(
                    db.session.query(ProjectFlightSegment.ref_id).distinct()
                )
            ).count()
            print(f"有REF但没有航段的记录数: {refs_without_segments}")
            
            # 检查是否有REF但没有乘客
            refs_without_passengers = db.session.query(ProjectRef).filter(
                ProjectRef.ref_type_id == 1,
                ~ProjectRef.id.in_(
                    db.session.query(ProjectFlightPassenger.ref_id).distinct()
                )
            ).count()
            print(f"有REF但没有乘客的记录数: {refs_without_passengers}")
            
            print("\n机票订单列表数据迁移测试完成！")
                
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_flight_orders_migration() 