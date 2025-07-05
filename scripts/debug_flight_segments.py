#!/usr/bin/env python3
"""
调试航段数据问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def debug_flight_segments():
    """调试航段数据问题"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment
    from App import create_app, db
    from sqlalchemy import text
    
    app = create_app()
    with app.app_context():
        # 检查REF ID=90
        ref = ProjectRef.query.get(90)
        if not ref:
            print("❌ REF ID=90 不存在")
            return
        
        print(f"✅ REF ID: {ref.id}")
        print(f"   名称: {ref.name}")
        print(f"   类型: {ref.ref_type.name if ref.ref_type else '无'}")
        print(f"   编号: {ref.ref_number}")
        
        # 检查航段数据
        segments = ProjectFlightSegment.query.filter_by(ref_id=90).all()
        print(f"\n航段数据:")
        print(f"   数量: {len(segments)}")
        
        if segments:
            for i, segment in enumerate(segments, 1):
                print(f"   航段{i}: {segment.flight_number} {segment.departure_airport}-{segment.arrival_airport}")
        else:
            print("   ❌ 没有找到航段数据")
        
        # 检查所有航段表数据
        all_segments = ProjectFlightSegment.query.all()
        print(f"\n整个航段表数据:")
        print(f"   总数量: {len(all_segments)}")
        
        if all_segments:
            print("   前5条记录:")
            for i, segment in enumerate(all_segments[:5], 1):
                print(f"   {i}. ref_id={segment.ref_id}, 航班={segment.flight_number}, 路线={segment.departure_airport}-{segment.arrival_airport}")
        else:
            print("   ❌ 整个航段表都是空的")
        
        # 检查乘客数据
        passengers = ref.flight_passengers
        print(f"\n乘客数据:")
        print(f"   数量: {len(passengers)}")
        
        if passengers:
            for i, passenger in enumerate(passengers, 1):
                print(f"   乘客{i}: {passenger.name} ({passenger.passenger_type})")
        
        # 检查数据库表结构
        print(f"\n数据库表检查:")
        try:
            # 检查表是否存在
            result = db.session.execute(text("SHOW TABLES LIKE 'project_flight_segments'"))
            if result.fetchone():
                print("   ✅ project_flight_segments 表存在")
                
                # 检查表结构
                result = db.session.execute(text("DESCRIBE project_flight_segments"))
                columns = result.fetchall()
                print(f"   表字段: {[col[0] for col in columns]}")
                
                # 检查是否有数据
                result = db.session.execute(text("SELECT COUNT(*) FROM project_flight_segments"))
                count = result.fetchone()[0]
                print(f"   总记录数: {count}")
                
            else:
                print("   ❌ project_flight_segments 表不存在")
        except Exception as e:
            print(f"   ❌ 检查表结构时出错: {e}")

if __name__ == "__main__":
    debug_flight_segments() 