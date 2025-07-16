#!/usr/bin/env python3
"""
测试编辑机票REF时航段数据的加载情况
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_flight_ref_edit():
    """测试编辑机票REF时航段数据的加载情况"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment, ProjectFlightPassenger
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from sqlalchemy.orm import joinedload
    
    app = create_app()
    with app.app_context():
        print("=== 测试编辑机票REF时航段数据的加载情况 ===")
        
        # 1. 查找机票类型的REF
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return False
        
        # 查找有航段数据的机票REF
        refs_with_segments = db.session.query(ProjectRef).join(
            ProjectFlightSegment, ProjectRef.id == ProjectFlightSegment.ref_id
        ).filter(
            ProjectRef.ref_type_id == flight_type.id
        ).distinct().limit(5).all()
        
        if not refs_with_segments:
            print("❌ 未找到有航段数据的机票REF")
            return False
        
        print(f"找到 {len(refs_with_segments)} 个有航段数据的机票REF")
        
        # 2. 测试每个REF的数据加载
        for i, ref in enumerate(refs_with_segments, 1):
            print(f"\n--- 测试REF {i}: ID={ref.id} ---")
            
            # 使用与编辑路由相同的方式加载数据
            ref_with_data = ProjectRef.query.options(
                joinedload(ProjectRef.flight_passengers),
                joinedload(ProjectRef.flight_segments)
            ).get(ref.id)
            
            if not ref_with_data:
                print(f"  ❌ 无法加载REF ID {ref.id}")
                continue
            
            print(f"  REF名称: {ref_with_data.name}")
            print(f"  业务类型: {ref_with_data.ref_type.name if ref_with_data.ref_type else '无'}")
            
            # 检查乘客数据
            passengers = ref_with_data.flight_passengers
            print(f"  乘客数量: {len(passengers)}")
            for p in passengers:
                print(f"    - {p.name} ({p.passenger_type}): 售价={p.selling_price}, 成本={p.cost_price}")
            
            # 检查航段数据
            segments = ref_with_data.flight_segments
            print(f"  航段数量: {len(segments)}")
            
            if segments:
                for s in segments:
                    print(f"    - {s.flight_number}: {s.departure_airport}-{s.arrival_airport}")
                    print(f"      出发: {s.departure_time}")
                    print(f"      到达: {s.arrival_time}")
                    print(f"      舱位: {s.cabin_code} ({s.cabin_class})")
                    print(f"      状态: {s.status}")
            else:
                print("    ❌ 没有找到航段信息")
            
            # 检查数据是否可以通过模板变量访问
            print(f"  检查模板变量访问:")
            print(f"    ref.flight_passengers: {hasattr(ref_with_data, 'flight_passengers')}")
            print(f"    ref.flight_segments: {hasattr(ref_with_data, 'flight_segments')}")
            
            if hasattr(ref_with_data, 'flight_passengers'):
                print(f"    flight_passengers 类型: {type(ref_with_data.flight_passengers)}")
                print(f"    flight_passengers 长度: {len(ref_with_data.flight_passengers)}")
            
            if hasattr(ref_with_data, 'flight_segments'):
                print(f"    flight_segments 类型: {type(ref_with_data.flight_segments)}")
                print(f"    flight_segments 长度: {len(ref_with_data.flight_segments)}")
        
        # 3. 测试模板数据传递
        print(f"\n=== 测试模板数据传递 ===")
        
        # 选择一个有航段数据的REF进行详细测试
        test_ref = refs_with_segments[0]
        print(f"选择测试REF: ID={test_ref.id}, 名称={test_ref.name}")
        
        # 模拟模板中的数据传递
        segments_data = []
        for s in test_ref.flight_segments:
            segment_data = {
                "flight_number": s.flight_number or '',
                "cabin_code": s.cabin_code or '',
                "departure_airport": s.departure_airport or '',
                "arrival_airport": s.arrival_airport or '',
                "departure_time": s.departure_time.isoformat() if s.departure_time else '',
                "arrival_time": s.arrival_time.isoformat() if s.arrival_time else ''
            }
            segments_data.append(segment_data)
        
        print(f"模拟的航段数据:")
        for i, data in enumerate(segments_data, 1):
            print(f"  航段{i}: {data}")
        
        # 4. 检查JavaScript数据传递
        print(f"\n=== 检查JavaScript数据传递 ===")
        
        # 模拟模板中的JavaScript数据传递
        js_segments_data = []
        for s in test_ref.flight_segments:
            js_data = {
                "flight_number": s.flight_number or '',
                "cabin_code": s.cabin_code or '',
                "departure_airport": s.departure_airport or '',
                "arrival_airport": s.arrival_airport or '',
                "departure_time": s.departure_time.isoformat() if s.departure_time else '',
                "arrival_time": s.arrival_time.isoformat() if s.arrival_time else ''
            }
            js_segments_data.append(js_data)
        
        print(f"JavaScript航段数据:")
        for i, data in enumerate(js_segments_data, 1):
            print(f"  航段{i}: {data}")
        
        # 5. 检查日期时间格式
        print(f"\n=== 检查日期时间格式 ===")
        for s in test_ref.flight_segments:
            print(f"  航班: {s.flight_number}")
            print(f"    出发时间: {s.departure_time} (类型: {type(s.departure_time)})")
            print(f"    到达时间: {s.arrival_time} (类型: {type(s.arrival_time)})")
            if s.departure_time:
                print(f"    出发时间ISO格式: {s.departure_time.isoformat()}")
            if s.arrival_time:
                print(f"    到达时间ISO格式: {s.arrival_time.isoformat()}")
        
        return True

if __name__ == "__main__":
    test_flight_ref_edit() 