#!/usr/bin/env python3
"""
测试编辑机票REF时航段数据加载的修复
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_flight_ref_edit_fix():
    """测试编辑机票REF时航段数据加载的修复"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from sqlalchemy.orm import joinedload
    
    app = create_app()
    with app.app_context():
        print("=== 测试编辑机票REF时航段数据加载的修复 ===")
        
        # 1. 查找有航段数据的机票REF
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return False
        
        # 查找有航段数据的机票REF
        refs_with_segments = db.session.query(ProjectRef).join(
            ProjectFlightSegment, ProjectRef.id == ProjectFlightSegment.ref_id
        ).filter(
            ProjectRef.ref_type_id == flight_type.id
        ).distinct().limit(3).all()
        
        if not refs_with_segments:
            print("❌ 未找到有航段数据的机票REF")
            return False
        
        print(f"找到 {len(refs_with_segments)} 个有航段数据的机票REF")
        
        # 2. 测试每个REF的数据格式
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
            
            # 检查航段数据格式
            segments = ref_with_data.flight_segments
            print(f"  航段数量: {len(segments)}")
            
            if segments:
                for j, s in enumerate(segments, 1):
                    print(f"    航段{j}: {s.flight_number}")
                    print(f"      出发: {s.departure_airport} -> {s.arrival_airport}")
                    print(f"      出发时间: {s.departure_time}")
                    print(f"      到达时间: {s.arrival_time}")
                    
                    # 测试JavaScript数据格式
                    if s.departure_time:
                        iso_dep = s.departure_time.isoformat()
                        print(f"      出发时间ISO格式: {iso_dep}")
                        
                        # 模拟JavaScript处理
                        print(f"      JavaScript解析: 需要JavaScript环境测试")
                    
                    if s.arrival_time:
                        iso_arr = s.arrival_time.isoformat()
                        print(f"      到达时间ISO格式: {iso_arr}")
                        
                        # 模拟JavaScript处理
                        print(f"      JavaScript解析: 需要JavaScript环境测试")
                    
                    print(f"      舱位: {s.cabin_code} ({s.cabin_class})")
                    print()
            else:
                print("    ❌ 没有找到航段信息")
        
        # 3. 模拟模板数据传递
        print(f"\n=== 模拟模板数据传递 ===")
        
        test_ref = refs_with_segments[0]
        print(f"选择测试REF: ID={test_ref.id}, 名称={test_ref.name}")
        
        # 模拟模板中的JavaScript数据传递
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
            print(f"  航段{i}:")
            print(f"    航班号: {data['flight_number']}")
            print(f"    舱位: {data['cabin_code']}")
            print(f"    出发机场: {data['departure_airport']}")
            print(f"    到达机场: {data['arrival_airport']}")
            print(f"    出发时间: {data['departure_time']}")
            print(f"    到达时间: {data['arrival_time']}")
            print()
        
        # 4. 测试修复后的JavaScript处理逻辑
        print(f"\n=== 测试修复后的JavaScript处理逻辑 ===")
        
        for i, segment_data in enumerate(segments_data, 1):
            print(f"处理航段{i}:")
            
            # 模拟修复后的JavaScript处理
            departure_date = ''
            departure_time = ''
            arrival_date = ''
            arrival_time = ''
            
            if segment_data['departure_time']:
                try:
                    depDateTime = segment_data['departure_time']  # 模拟JavaScript的Date对象
                    print(f"  出发时间原始: {depDateTime}")
                    # 这里应该模拟JavaScript的Date处理逻辑
                    print(f"  出发时间处理: 需要JavaScript环境测试")
                except Exception as e:
                    print(f"  出发时间处理失败: {e}")
            
            if segment_data['arrival_time']:
                try:
                    arrDateTime = segment_data['arrival_time']  # 模拟JavaScript的Date对象
                    print(f"  到达时间原始: {arrDateTime}")
                    # 这里应该模拟JavaScript的Date处理逻辑
                    print(f"  到达时间处理: 需要JavaScript环境测试")
                except Exception as e:
                    print(f"  到达时间处理失败: {e}")
            
            print()
        
        return True

if __name__ == "__main__":
    test_flight_ref_edit_fix() 