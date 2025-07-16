#!/usr/bin/env python3
"""
测试机票REF的航段数据保存和读取流程
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_flight_ref_data_flow():
    """测试机票REF的航段数据保存和读取流程"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment, ProjectFlightPassenger
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from sqlalchemy.orm import joinedload
    from datetime import datetime
    
    app = create_app()
    with app.app_context():
        print("=== 测试机票REF的航段数据保存和读取流程 ===")
        
        # 1. 查找机票业务类型
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return False
        
        print(f"✅ 找到机票业务类型: {flight_type.name}")
        
        # 2. 查找有航段数据的机票REF
        refs_with_segments = db.session.query(ProjectRef).join(
            ProjectFlightSegment, ProjectRef.id == ProjectFlightSegment.ref_id
        ).filter(
            ProjectRef.ref_type_id == flight_type.id
        ).options(
            joinedload(ProjectRef.flight_segments),
            joinedload(ProjectRef.flight_passengers)
        ).limit(5).all()
        
        if not refs_with_segments:
            print("❌ 未找到有航段数据的机票REF")
            return False
        
        print(f"\n找到 {len(refs_with_segments)} 个有航段数据的机票REF:")
        
        for i, ref in enumerate(refs_with_segments, 1):
            print(f"\n{i}. REF ID: {ref.id}")
            print(f"   名称: {ref.name}")
            print(f"   创建时间: {ref.created_at}")
            print(f"   航段数量: {len(ref.flight_segments)}")
            print(f"   乘客数量: {len(ref.flight_passengers)}")
            
            # 显示航段详情
            for j, segment in enumerate(ref.flight_segments, 1):
                print(f"     航段{j}: {segment.flight_number} {segment.departure_airport}-{segment.arrival_airport}")
                print(f"       出发时间: {segment.departure_time}")
                print(f"       到达时间: {segment.arrival_time}")
                print(f"       舱位代码: {segment.cabin_code}")
            
            # 显示乘客详情
            for j, passenger in enumerate(ref.flight_passengers, 1):
                print(f"     乘客{j}: {passenger.name} ({passenger.passenger_type})")
                print(f"       售价: {passenger.selling_price}")
                print(f"       成本: {passenger.cost_price}")
        
        # 3. 测试编辑模式的数据读取
        print(f"\n=== 测试编辑模式的数据读取 ===")
        
        # 选择一个有数据的REF进行测试
        test_ref = refs_with_segments[0]
        print(f"测试REF ID: {test_ref.id}")
        
        # 模拟编辑路由的数据查询
        edit_ref = ProjectRef.query.options(
            joinedload(ProjectRef.flight_passengers),
            joinedload(ProjectRef.flight_segments)
        ).get(test_ref.id)
        
        if not edit_ref:
            print("❌ 无法读取REF数据")
            return False
        
        print(f"✅ 成功读取REF数据")
        print(f"   航段数量: {len(edit_ref.flight_segments)}")
        print(f"   乘客数量: {len(edit_ref.flight_passengers)}")
        
        # 4. 测试模板数据传递
        print(f"\n=== 测试模板数据传递 ===")
        
        # 模拟模板中的JavaScript数据
        segments_data = []
        for segment in edit_ref.flight_segments:
            segment_data = {
                "flight_number": segment.flight_number or '',
                "cabin_code": segment.cabin_code or '',
                "departure_airport": segment.departure_airport or '',
                "arrival_airport": segment.arrival_airport or '',
                "departure_time": segment.departure_time.isoformat() if segment.departure_time else '',
                "arrival_time": segment.arrival_time.isoformat() if segment.arrival_time else ''
            }
            segments_data.append(segment_data)
        
        passengers_data = []
        for passenger in edit_ref.flight_passengers:
            passenger_data = {
                "name": passenger.name or '',
                "passenger_type": passenger.passenger_type or 'adult',
                "selling_price": passenger.selling_price or 0,
                "cost_price": passenger.cost_price or 0,
                "ticket_number": passenger.ticket_number or '',
                "pnr": passenger.pnr or ''
            }
            passengers_data.append(passenger_data)
        
        print(f"   传递给JavaScript的航段数据: {len(segments_data)} 条")
        for i, segment in enumerate(segments_data, 1):
            print(f"     航段{i}: {segment['flight_number']} {segment['departure_airport']}-{segment['arrival_airport']}")
            print(f"       出发时间: {segment['departure_time']}")
            print(f"       到达时间: {segment['arrival_time']}")
        
        print(f"   传递给JavaScript的乘客数据: {len(passengers_data)} 条")
        for i, passenger in enumerate(passengers_data, 1):
            print(f"     乘客{i}: {passenger['name']} ({passenger['passenger_type']})")
        
        # 5. 测试保存逻辑
        print(f"\n=== 测试保存逻辑 ===")
        
        # 模拟表单数据
        form_data = {
            'header_id': test_ref.header_id,
            'ref_id': test_ref.id,
            'name': test_ref.name,
            'description': test_ref.description,
            'supplier_id': test_ref.supplier_id,
            'contact_name': test_ref.contact_name,
            'contact_phone': test_ref.contact_phone,
            'contact_email': test_ref.contact_email,
            'remarks': test_ref.remarks,
            'status': test_ref.status,
            'payment_status': test_ref.payment_status,
            'flight_number[]': [seg.flight_number for seg in edit_ref.flight_segments],
            'cabin_code[]': [seg.cabin_code for seg in edit_ref.flight_segments],
            'departure_airport[]': [seg.departure_airport for seg in edit_ref.flight_segments],
            'arrival_airport[]': [seg.arrival_airport for seg in edit_ref.flight_segments],
            'departure_date[]': [seg.departure_time.strftime('%Y-%m-%d') if seg.departure_time else '' for seg in edit_ref.flight_segments],
            'departure_time[]': [f"{seg.departure_time.strftime('%Y-%m-%d')} {seg.departure_time.strftime('%H:%M')}" if seg.departure_time else '' for seg in edit_ref.flight_segments],
            'arrival_date[]': [seg.arrival_time.strftime('%Y-%m-%d') if seg.arrival_time else '' for seg in edit_ref.flight_segments],
            'arrival_time[]': [f"{seg.arrival_time.strftime('%Y-%m-%d')} {seg.arrival_time.strftime('%H:%M')}" if seg.arrival_time else '' for seg in edit_ref.flight_segments],
            'passenger_name[]': [p.name for p in edit_ref.flight_passengers],
            'passenger_type[]': [p.passenger_type for p in edit_ref.flight_passengers],
            'selling_price[]': [str(p.selling_price or 0) for p in edit_ref.flight_passengers],
            'cost_price[]': [str(p.cost_price or 0) for p in edit_ref.flight_passengers],
            'ticket_number[]': [p.ticket_number or '' for p in edit_ref.flight_passengers],
            'pnr[]': [p.pnr or '' for p in edit_ref.flight_passengers]
        }
        
        print(f"   模拟表单数据:")
        print(f"     航段数量: {len(form_data['flight_number[]'])}")
        print(f"     乘客数量: {len(form_data['passenger_name[]'])}")
        
        # 验证数据完整性
        max_segment_len = max(len(form_data['flight_number[]']), len(form_data['cabin_code[]']), 
                             len(form_data['departure_airport[]']), len(form_data['arrival_airport[]']),
                             len(form_data['departure_date[]']), len(form_data['departure_time[]']),
                             len(form_data['arrival_date[]']), len(form_data['arrival_time[]']))
        
        max_passenger_len = max(len(form_data['passenger_name[]']), len(form_data['passenger_type[]']),
                               len(form_data['selling_price[]']), len(form_data['cost_price[]']),
                               len(form_data['ticket_number[]']), len(form_data['pnr[]']))
        
        print(f"   数据完整性检查:")
        print(f"     航段字段长度: {max_segment_len}")
        print(f"     乘客字段长度: {max_passenger_len}")
        
        if max_segment_len == len(edit_ref.flight_segments) and max_passenger_len == len(edit_ref.flight_passengers):
            print("   ✅ 数据完整性检查通过")
        else:
            print("   ❌ 数据完整性检查失败")
        
        print(f"\n✅ 测试完成")
        return True

if __name__ == '__main__':
    test_flight_ref_data_flow() 