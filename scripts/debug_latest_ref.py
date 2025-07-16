#!/usr/bin/env python3
"""
调试最新REF为什么没有航段信息
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def debug_latest_ref():
    """调试最新REF为什么没有航段信息"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment, ProjectFlightPassenger
    from App import create_app, db
    from datetime import datetime
    
    app = create_app()
    with app.app_context():
        print("=== 调试最新REF航段信息 ===")
        
        # 获取最新的REF
        latest_ref = ProjectRef.query.order_by(ProjectRef.created_at.desc()).first()
        if not latest_ref:
            print("❌ 没有找到REF记录")
            return
        
        print(f"最新REF ID: {latest_ref.id}")
        print(f"REF名称: {latest_ref.name}")
        print(f"创建时间: {latest_ref.created_at}")
        print(f"业务类型: {latest_ref.ref_type.name if latest_ref.ref_type else '无'}")
        
        # 检查乘客信息
        passengers = ProjectFlightPassenger.query.filter_by(ref_id=latest_ref.id).all()
        print(f"\n乘客信息:")
        print(f"乘客数量: {len(passengers)}")
        for p in passengers:
            print(f"  - {p.name} ({p.passenger_type}): 售价={p.selling_price}, 成本={p.cost_price}")
            print(f"    电子客票号: {p.ticket_number}")
            print(f"    PNR: {p.pnr}")
        
        # 检查航段信息
        segments = ProjectFlightSegment.query.filter_by(ref_id=latest_ref.id).all()
        print(f"\n航段信息:")
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
        
        # 检查REF的基本信息
        print(f"\nREF基本信息:")
        print(f"  供应商ID: {latest_ref.supplier_id}")
        print(f"  联系人: {latest_ref.contact_name}")
        print(f"  联系电话: {latest_ref.contact_phone}")
        print(f"  状态: {latest_ref.status}")
        print(f"  支付状态: {latest_ref.payment_status}")
        print(f"  售价: {latest_ref.selling_price}")
        print(f"  成本: {latest_ref.cost_price}")
        print(f"  备注: {latest_ref.remarks}")
        
        # 检查是否有其他REF也没有航段信息
        print(f"\n=== 检查其他缺少航段的REF ===")
        refs_without_segments = []
        all_refs = ProjectRef.query.order_by(ProjectRef.created_at.desc()).limit(20).all()
        
        for ref in all_refs:
            segment_count = ProjectFlightSegment.query.filter_by(ref_id=ref.id).count()
            if segment_count == 0:
                refs_without_segments.append(ref)
                print(f"  REF ID {ref.id}: {ref.name} (创建时间: {ref.created_at}) - 无航段")
        
        print(f"\n缺少航段的REF数量: {len(refs_without_segments)}")
        
        # 检查航段表的整体情况
        print(f"\n=== 航段表整体情况 ===")
        total_segments = ProjectFlightSegment.query.count()
        total_refs = ProjectRef.query.count()
        refs_with_segments = db.session.query(ProjectFlightSegment.ref_id).distinct().count()
        
        print(f"总航段数: {total_segments}")
        print(f"总REF数: {total_refs}")
        print(f"有航段的REF数: {refs_with_segments}")
        print(f"无航段的REF数: {total_refs - refs_with_segments}")
        
        return True

if __name__ == "__main__":
    debug_latest_ref() 