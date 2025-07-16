#!/usr/bin/env python3
"""
检查哪些flight类型的REF缺少航段信息
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_missing_flight_segments():
    """检查哪些flight类型的REF缺少航段信息"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from sqlalchemy.orm import joinedload
    
    app = create_app()
    with app.app_context():
        print("=== 检查flight类型REF缺少航段信息 ===")
        
        # 1. 查找机票业务类型
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return
        
        print(f"✅ 找到机票业务类型: {flight_type.name} (ID: {flight_type.id})")
        
        # 2. 查找所有机票类型的REF
        flight_refs = ProjectRef.query.filter_by(ref_type_id=flight_type.id).all()
        print(f"\n找到 {len(flight_refs)} 个机票REF")
        
        if not flight_refs:
            print("❌ 没有找到机票REF")
            return
        
        # 3. 检查每个REF的航段信息
        refs_without_segments = []
        refs_with_segments = []
        
        for ref in flight_refs:
            # 查询该REF的航段数量
            segment_count = ProjectFlightSegment.query.filter_by(ref_id=ref.id).count()
            
            if segment_count == 0:
                refs_without_segments.append({
                    'id': ref.id,
                    'ref_number': ref.ref_number,
                    'name': ref.name,
                    'created_at': ref.created_at,
                    'segment_count': segment_count
                })
            else:
                refs_with_segments.append({
                    'id': ref.id,
                    'ref_number': ref.ref_number,
                    'name': ref.name,
                    'created_at': ref.created_at,
                    'segment_count': segment_count
                })
        
        # 4. 输出结果
        print(f"\n📊 统计结果:")
        print(f"   有航段的REF: {len(refs_with_segments)} 个")
        print(f"   缺少航段的REF: {len(refs_without_segments)} 个")
        
        if refs_without_segments:
            print(f"\n❌ 缺少航段信息的机票REF:")
            print(f"{'ID':<5} {'REF编号':<15} {'名称':<30} {'创建时间':<20} {'航段数':<8}")
            print("-" * 80)
            for ref in refs_without_segments:
                print(f"{ref['id']:<5} {ref['ref_number']:<15} {ref['name'][:28]:<30} {ref['created_at'].strftime('%Y-%m-%d %H:%M'):<20} {ref['segment_count']:<8}")
        else:
            print("\n✅ 所有机票REF都有航段信息")
        
        if refs_with_segments:
            print(f"\n✅ 有航段信息的机票REF:")
            print(f"{'ID':<5} {'REF编号':<15} {'名称':<30} {'创建时间':<20} {'航段数':<8}")
            print("-" * 80)
            for ref in refs_with_segments[:10]:  # 只显示前10个
                print(f"{ref['id']:<5} {ref['ref_number']:<15} {ref['name'][:28]:<30} {ref['created_at'].strftime('%Y-%m-%d %H:%M'):<20} {ref['segment_count']:<8}")
            if len(refs_with_segments) > 10:
                print(f"   ... 还有 {len(refs_with_segments) - 10} 个")
        
        # 5. 详细检查缺少航段的REF
        if refs_without_segments:
            print(f"\n🔍 详细检查缺少航段的REF:")
            for ref_info in refs_without_segments[:5]:  # 只检查前5个
                ref = ProjectRef.query.get(ref_info['id'])
                print(f"\nREF ID: {ref.id}")
                print(f"  编号: {ref.ref_number}")
                print(f"  名称: {ref.name}")
                print(f"  描述: {ref.description}")
                print(f"  状态: {ref.status}")
                print(f"  创建时间: {ref.created_at}")
                
                # 检查乘客信息
                passenger_count = len(ref.flight_passengers)
                print(f"  乘客数量: {passenger_count}")
                
                # 检查航段信息
                segment_count = len(ref.flight_segments)
                print(f"  航段数量: {segment_count}")
                
                if segment_count == 0:
                    print("  ❌ 确实缺少航段信息")
                else:
                    print("  ✅ 有航段信息")
        
        print(f"\n📋 总结:")
        print(f"   总机票REF数: {len(flight_refs)}")
        print(f"   有航段: {len(refs_with_segments)}")
        print(f"   无航段: {len(refs_without_segments)}")
        print(f"   完整率: {len(refs_with_segments)/len(flight_refs)*100:.1f}%")

if __name__ == "__main__":
    check_missing_flight_segments() 