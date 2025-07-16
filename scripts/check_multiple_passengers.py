#!/usr/bin/env python3
"""
检查多位乘客信息的保存和加载问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_multiple_passengers():
    """检查多位乘客信息的保存和加载问题"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightPassenger, ProjectFlightSegment
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from sqlalchemy.orm import joinedload
    
    app = create_app()
    with app.app_context():
        print("=== 检查多位乘客信息保存和加载问题 ===")
        
        # 1. 查找机票业务类型
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return
        
        print(f"✅ 找到机票业务类型: {flight_type.name} (ID: {flight_type.id})")
        
        # 2. 查找有多个乘客的机票REF
        refs_with_multiple_passengers = []
        refs_with_single_passenger = []
        refs_without_passengers = []
        
        flight_refs = ProjectRef.query.filter_by(ref_type_id=flight_type.id).all()
        
        for ref in flight_refs:
            passenger_count = len(ref.flight_passengers)
            segment_count = len(ref.flight_segments)
            
            if passenger_count == 0:
                refs_without_passengers.append({
                    'id': ref.id,
                    'ref_number': ref.ref_number,
                    'name': ref.name,
                    'passenger_count': passenger_count,
                    'segment_count': segment_count,
                    'created_at': ref.created_at
                })
            elif passenger_count == 1:
                refs_with_single_passenger.append({
                    'id': ref.id,
                    'ref_number': ref.ref_number,
                    'name': ref.name,
                    'passenger_count': passenger_count,
                    'segment_count': segment_count,
                    'created_at': ref.created_at
                })
            else:
                refs_with_multiple_passengers.append({
                    'id': ref.id,
                    'ref_number': ref.ref_number,
                    'name': ref.name,
                    'passenger_count': passenger_count,
                    'segment_count': segment_count,
                    'created_at': ref.created_at
                })
        
        # 3. 输出统计结果
        print(f"\n📊 乘客信息统计:")
        print(f"   无乘客的REF: {len(refs_without_passengers)} 个")
        print(f"   单乘客的REF: {len(refs_with_single_passenger)} 个")
        print(f"   多乘客的REF: {len(refs_with_multiple_passengers)} 个")
        print(f"   总REF数: {len(flight_refs)} 个")
        
        # 4. 详细检查多乘客REF
        if refs_with_multiple_passengers:
            print(f"\n🔍 多乘客REF详细信息:")
            for ref_info in refs_with_multiple_passengers:
                ref = ProjectRef.query.options(
                    joinedload(ProjectRef.flight_passengers),
                    joinedload(ProjectRef.flight_segments)
                ).get(ref_info['id'])
                
                print(f"\nREF ID: {ref.id}")
                print(f"  编号: {ref.ref_number}")
                print(f"  名称: {ref.name}")
                print(f"  乘客数量: {len(ref.flight_passengers)}")
                print(f"  航段数量: {len(ref.flight_segments)}")
                print(f"  创建时间: {ref.created_at}")
                
                # 检查乘客详细信息
                print(f"  乘客详情:")
                for i, passenger in enumerate(ref.flight_passengers, 1):
                    print(f"    乘客{i}: {passenger.name} ({passenger.passenger_type})")
                    print(f"      售价: {passenger.selling_price}")
                    print(f"      成本: {passenger.cost_price}")
                    print(f"      电子客票号: {passenger.ticket_number}")
                    print(f"      PNR: {passenger.pnr}")
                
                # 检查航段详细信息
                if ref.flight_segments:
                    print(f"  航段详情:")
                    for i, segment in enumerate(ref.flight_segments, 1):
                        print(f"    航段{i}: {segment.flight_number}")
                        print(f"      路线: {segment.departure_airport} → {segment.arrival_airport}")
                        print(f"      时间: {segment.departure_time} → {segment.arrival_time}")
                        print(f"      舱位: {segment.cabin_code}")
        else:
            print("\n❌ 没有找到多乘客的REF")
        
        # 5. 检查单乘客REF（用于对比）
        if refs_with_single_passenger:
            print(f"\n📋 单乘客REF示例:")
            sample_ref = refs_with_single_passenger[0]
            ref = ProjectRef.query.options(
                joinedload(ProjectRef.flight_passengers),
                joinedload(ProjectRef.flight_segments)
            ).get(sample_ref['id'])
            
            print(f"REF ID: {ref.id}")
            print(f"  编号: {ref.ref_number}")
            print(f"  名称: {ref.name}")
            print(f"  乘客数量: {len(ref.flight_passengers)}")
            
            if ref.flight_passengers:
                passenger = ref.flight_passengers[0]
                print(f"  乘客: {passenger.name} ({passenger.passenger_type})")
                print(f"    售价: {passenger.selling_price}")
                print(f"    成本: {passenger.cost_price}")
                print(f"    电子客票号: {passenger.ticket_number}")
                print(f"    PNR: {passenger.pnr}")
        
        # 6. 检查无乘客REF
        if refs_without_passengers:
            print(f"\n⚠️ 无乘客REF:")
            for ref_info in refs_without_passengers[:3]:  # 只显示前3个
                print(f"  REF ID: {ref_info['id']}, 编号: {ref_info['ref_number']}, 名称: {ref_info['name']}")
        
        # 7. 总结和建议
        print(f"\n📋 总结:")
        print(f"   多乘客REF占比: {len(refs_with_multiple_passengers)/len(flight_refs)*100:.1f}%")
        print(f"   单乘客REF占比: {len(refs_with_single_passenger)/len(flight_refs)*100:.1f}%")
        print(f"   无乘客REF占比: {len(refs_without_passengers)/len(flight_refs)*100:.1f}%")
        
        if refs_with_multiple_passengers:
            print(f"\n✅ 发现 {len(refs_with_multiple_passengers)} 个多乘客REF，可以测试编辑功能")
            print(f"   建议测试REF ID: {refs_with_multiple_passengers[0]['id']}")
        else:
            print(f"\n❌ 没有多乘客REF，建议创建一个包含多个乘客的REF来测试")

if __name__ == "__main__":
    check_multiple_passengers() 