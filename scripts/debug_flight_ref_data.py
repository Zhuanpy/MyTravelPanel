#!/usr/bin/env python3
"""
调试机票REF数据加载问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def debug_flight_ref_data():
    """调试机票REF数据加载"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightPassenger, ProjectFlightSegment
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from sqlalchemy.orm import joinedload
    
    app = create_app()
    with app.app_context():
        print("=== 调试机票REF数据加载 ===")
        
        # 查找机票业务类型
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return
        
        print(f"✅ 机票业务类型ID: {flight_type.id}")
        
        # 查找所有机票REF
        refs = ProjectRef.query.filter_by(ref_type_id=flight_type.id).all()
        print(f"\n找到 {len(refs)} 个机票REF:")
        
        for i, ref in enumerate(refs, 1):
            print(f"\n--- REF {i}: {ref.ref_number} ---")
            print(f"   名称: {ref.name}")
            print(f"   状态: {ref.status}")
            print(f"   支付状态: {ref.payment_status}")
            
            # 检查乘客数据
            passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).all()
            print(f"   乘客数量: {len(passengers)}")
            for j, passenger in enumerate(passengers, 1):
                print(f"     乘客{j}: {passenger.name} ({passenger.passenger_type})")
                print(f"       售价: {passenger.selling_price}")
                print(f"       成本: {passenger.cost_price}")
            
            # 检查航段数据
            segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).all()
            print(f"   航段数量: {len(segments)}")
            for j, segment in enumerate(segments, 1):
                print(f"     航段{j}: {segment.flight_number}")
                print(f"       出发: {segment.departure_airport} -> 到达: {segment.arrival_airport}")
                print(f"       出发时间: {segment.departure_time}")
                print(f"       到达时间: {segment.arrival_time}")
                print(f"       舱位: {segment.cabin_code}")
        
        # 如果有航段数据的REF，测试预加载
        refs_with_segments = []
        for ref in refs:
            segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).all()
            if segments:
                refs_with_segments.append(ref)
        
        if refs_with_segments:
            print(f"\n=== 测试有航段数据的REF ===")
            test_ref = refs_with_segments[0]
            print(f"测试REF: {test_ref.ref_number}")
            
            # 测试预加载
            ref_with_data = ProjectRef.query.options(
                joinedload(ProjectRef.flight_passengers),
                joinedload(ProjectRef.flight_segments)
            ).filter_by(id=test_ref.id).first()
            
            print(f"   乘客数量: {len(ref_with_data.flight_passengers)}")
            print(f"   航段数量: {len(ref_with_data.flight_segments)}")
            
            # 测试JSON序列化
            print(f"\n测试JSON序列化:")
            try:
                import json
                passenger_data = []
                for passenger in ref_with_data.flight_passengers:
                    passenger_data.append({
                        'name': passenger.name,
                        'passenger_type': passenger.passenger_type,
                        'selling_price': float(passenger.selling_price) if passenger.selling_price else 0,
                        'cost_price': float(passenger.cost_price) if passenger.cost_price else 0,
                        'ticket_number': passenger.ticket_number or '',
                        'pnr': passenger.pnr or ''
                    })
                
                segment_data = []
                for segment in ref_with_data.flight_segments:
                    segment_data.append({
                        'flight_number': segment.flight_number,
                        'cabin_code': segment.cabin_code,
                        'departure_airport': segment.departure_airport,
                        'arrival_airport': segment.arrival_airport,
                        'departure_time': segment.departure_time.isoformat() if segment.departure_time else '',
                        'arrival_time': segment.arrival_time.isoformat() if segment.arrival_time else ''
                    })
                
                print("✅ JSON序列化成功")
                print(f"   乘客数据: {json.dumps(passenger_data, ensure_ascii=False, indent=2)}")
                print(f"   航段数据: {json.dumps(segment_data, ensure_ascii=False, indent=2)}")
                
            except Exception as e:
                print(f"❌ JSON序列化失败: {e}")
        else:
            print("\n❌ 没有找到包含航段数据的REF")

if __name__ == "__main__":
    debug_flight_ref_data() 