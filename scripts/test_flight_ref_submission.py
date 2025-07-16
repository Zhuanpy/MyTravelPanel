#!/usr/bin/env python3
"""
测试机票REF提交时航段信息的保存
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_flight_ref_submission():
    """测试机票REF提交时航段信息的保存"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment, ProjectFlightPassenger
    from App.models.Product.BusinessType import BusinessType
    from App.models.Product.Suppliers import Supplier
    from App import create_app, db
    from datetime import datetime
    
    app = create_app()
    with app.app_context():
        print("=== 测试机票REF提交时航段信息的保存 ===")
        
        # 1. 检查必要的业务类型和供应商
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return False
        
        suppliers = Supplier.query.limit(1).all()
        if not suppliers:
            print("❌ 未找到供应商")
            return False
        
        print(f"✅ 找到机票业务类型: {flight_type.name}")
        print(f"✅ 找到供应商: {suppliers[0].name}")
        
        # 2. 查找最近的机票REF
        recent_refs = ProjectRef.query.filter_by(ref_type_id=flight_type.id).order_by(ProjectRef.created_at.desc()).limit(5).all()
        
        if not recent_refs:
            print("❌ 未找到机票REF记录")
            return False
        
        print(f"\n找到 {len(recent_refs)} 个机票REF:")
        for i, ref in enumerate(recent_refs, 1):
            print(f"{i}. REF ID: {ref.id}, 名称: {ref.name}, 创建时间: {ref.created_at}")
        
        # 3. 检查每个REF的航段信息
        for ref in recent_refs:
            print(f"\n--- 检查REF ID: {ref.id} ---")
            
            # 检查乘客信息
            passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).all()
            print(f"乘客数量: {len(passengers)}")
            for p in passengers:
                print(f"  - {p.name} ({p.passenger_type}): 售价={p.selling_price}, 成本={p.cost_price}")
            
            # 检查航段信息
            segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).all()
            print(f"航段数量: {len(segments)}")
            
            if segments:
                for s in segments:
                    print(f"  - {s.flight_number}: {s.departure_airport}-{s.arrival_airport}")
                    print(f"    出发: {s.departure_time}")
                    print(f"    到达: {s.arrival_time}")
                    print(f"    舱位: {s.cabin_code} ({s.cabin_class})")
                    print(f"    状态: {s.status}")
            else:
                print("  ❌ 没有找到航段信息")
        
        # 4. 检查整个航段表的数据
        print(f"\n=== 整个航段表数据统计 ===")
        total_segments = ProjectFlightSegment.query.count()
        print(f"总航段数量: {total_segments}")
        
        if total_segments > 0:
            # 按REF分组统计
            from sqlalchemy import func
            segment_stats = db.session.query(
                ProjectFlightSegment.ref_id,
                func.count(ProjectFlightSegment.id).label('segment_count')
            ).group_by(ProjectFlightSegment.ref_id).all()
            
            print(f"有航段数据的REF数量: {len(segment_stats)}")
            for ref_id, count in segment_stats:
                ref_name = ProjectRef.query.get(ref_id).name if ProjectRef.query.get(ref_id) else "未知"
                print(f"  REF ID {ref_id} ({ref_name}): {count} 个航段")
        
        # 5. 检查最近提交的航段
        recent_segments = ProjectFlightSegment.query.order_by(ProjectFlightSegment.created_at.desc()).limit(10).all()
        print(f"\n=== 最近10个航段 ===")
        for i, segment in enumerate(recent_segments, 1):
            ref_name = segment.ref.name if segment.ref else "未知"
            print(f"{i}. REF: {ref_name} ({segment.ref_id})")
            print(f"   航班: {segment.flight_number}")
            print(f"   路线: {segment.departure_airport}-{segment.arrival_airport}")
            print(f"   时间: {segment.departure_time} - {segment.arrival_time}")
            print(f"   舱位: {segment.cabin_code}")
            print(f"   创建时间: {segment.created_at}")
            print()
        
        return True

if __name__ == "__main__":
    test_flight_ref_submission() 