#!/usr/bin/env python3
"""
最终测试机票订单列表功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.BookingProject import ProjectFlightSegment, ProjectRef, ProjectHeader, ProjectFlightPassenger
from App.models.Product.BusinessType import BusinessType

def test_flight_orders_final():
    """最终测试机票订单列表功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始最终测试机票订单列表功能...")
            
            # 1. 测试查询逻辑
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
            ).order_by(ProjectRef.created_at.desc()).limit(10)
            
            results = query.all()
            print(f"查询结果数量: {len(results)}")
            
            # 2. 测试数据转换
            print("\n=== 测试数据转换 ===")
            orders_data = []
            for result in results:
                ref, header, passenger_count, total_selling, total_cost, first_departure_time, last_arrival_time = result
                
                # 获取乘客信息
                passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).all()
                
                # 获取航段信息
                flight_segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).order_by(ProjectFlightSegment.departure_time).all()
                
                # 构建行程信息
                itinerary_parts = []
                for segment in flight_segments:
                    itinerary_parts.append(f"{segment.departure_airport}-{segment.arrival_airport}")
                itinerary = '/'.join(itinerary_parts) if itinerary_parts else ''
                
                # 构建订单数据
                order_data = {
                    'id': ref.id,
                    'order_number': ref.ref_number,
                    'contact_name': ref.contact_name,
                    'contact_person': ref.contact_name,
                    'contact_phone': ref.contact_phone,
                    'supplier_name': ref.supplier.name if ref.supplier else '',
                    'passenger_name': f"{passenger_count}人" if passenger_count else "0人",
                    'departure_date': first_departure_time.date() if first_departure_time else None,
                    'departure_city': flight_segments[0].departure_airport if flight_segments else '',
                    'arrival_city': flight_segments[-1].arrival_airport if flight_segments else '',
                    'flight_number': flight_segments[0].flight_number if flight_segments else '',
                    'departure_time': first_departure_time,
                    'itinerary': itinerary,
                    'selling_price': float(total_selling) if total_selling else 0,
                    'cost_price': float(total_cost) if total_cost else 0,
                    'order_status': ref.status,
                    'payment_status': ref.payment_status,
                    'status': ref.status,
                    'created_date': ref.created_at,
                    'remarks': ref.remarks,
                    'header': header,
                    'ref': ref,
                    'passengers': passengers,
                    'flight_segments': flight_segments
                }
                orders_data.append(order_data)
                
                print(f"\n订单 {len(orders_data)}:")
                print(f"  REF编号: {order_data['order_number']}")
                print(f"  联系人: {order_data['contact_name']}")
                print(f"  供应商: {order_data['supplier_name']}")
                print(f"  乘客数: {order_data['passenger_name']}")
                print(f"  总售价: {order_data['selling_price']}")
                print(f"  总成本: {order_data['cost_price']}")
                print(f"  状态: {order_data['order_status']}")
                print(f"  支付状态: {order_data['payment_status']}")
                print(f"  行程: {order_data['itinerary']}")
                print(f"  出发时间: {order_data['departure_time']}")
                print(f"  航段数: {len(order_data['flight_segments'])}")
                print(f"  乘客数: {len(order_data['passengers'])}")
            
            # 3. 测试筛选功能
            print("\n=== 测试筛选功能 ===")
            
            # 测试状态筛选
            status_filter_query = db.session.query(
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
                ProjectRef.ref_type_id == 1,
                ProjectRef.status == 'completed'
            ).group_by(
                ProjectRef.id,
                ProjectHeader.id
            )
            completed_count = status_filter_query.count()
            print(f"已完成状态的订单数: {completed_count}")
            
            # 测试供应商筛选
            supplier_filter_query = db.session.query(
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
                ProjectRef.ref_type_id == 1,
                ProjectRef.supplier.has(name='LEGEND TRAVEL')
            ).group_by(
                ProjectRef.id,
                ProjectHeader.id
            )
            legend_travel_count = supplier_filter_query.count()
            print(f"LEGEND TRAVEL供应商的订单数: {legend_travel_count}")
            
            # 测试联系人筛选
            contact_filter_query = db.session.query(
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
                ProjectRef.ref_type_id == 1,
                ProjectRef.contact_name.like('%YIN%')
            ).group_by(
                ProjectRef.id,
                ProjectHeader.id
            )
            yin_contact_count = contact_filter_query.count()
            print(f"联系人包含YIN的订单数: {yin_contact_count}")
            
            # 4. 测试分页功能
            print("\n=== 测试分页功能 ===")
            pagination_query = db.session.query(
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
                ProjectRef.ref_type_id == 1
            ).group_by(
                ProjectRef.id,
                ProjectHeader.id
            ).order_by(ProjectRef.created_at.desc())
            
            paginated_results = pagination_query.paginate(page=1, per_page=5, error_out=False)
            print(f"分页结果: 第{paginated_results.page}页，共{paginated_results.pages}页，总计{paginated_results.total}条记录")
            print(f"当前页记录数: {len(paginated_results.items)}")
            
            # 5. 验证数据完整性
            print("\n=== 验证数据完整性 ===")
            
            # 检查所有机票REF都有航段
            flight_refs = ProjectRef.query.filter_by(ref_type_id=1).all()
            refs_without_segments = 0
            refs_without_passengers = 0
            
            for ref in flight_refs:
                segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).count()
                passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).count()
                
                if segments == 0:
                    refs_without_segments += 1
                if passengers == 0:
                    refs_without_passengers += 1
            
            print(f"机票REF总数: {len(flight_refs)}")
            print(f"没有航段的REF数: {refs_without_segments}")
            print(f"没有乘客的REF数: {refs_without_passengers}")
            
            if refs_without_segments == 0 and refs_without_passengers == 0:
                print("✅ 数据完整性检查通过")
            else:
                print("⚠️ 数据完整性检查发现问题")
            
            print("\n机票订单列表功能测试完成！")
                
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_flight_orders_final() 