#!/usr/bin/env python3
"""
测试航段保存逻辑
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_flight_segment_save():
    """测试航段保存逻辑"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment
    from App import create_app, db
    from datetime import datetime
    
    app = create_app()
    with app.app_context():
        # 获取REF ID=90
        ref = ProjectRef.query.get(90)
        if not ref:
            print("❌ REF ID=90 不存在")
            return
        
        print(f"✅ 找到REF: {ref.ref_number}")
        
        # 模拟航段数据
        test_segments = [
            {
                'flight_number': 'SQ123',
                'departure_airport': 'SIN',
                'arrival_airport': 'BKK',
                'departure_time': datetime(2025, 7, 15, 10, 30),
                'arrival_time': datetime(2025, 7, 15, 12, 30),
                'cabin_class': 'Y',
                'cabin_code': 'Y',
                'status': 'pending'
            },
            {
                'flight_number': 'SQ456',
                'departure_airport': 'BKK',
                'arrival_airport': 'SIN',
                'departure_time': datetime(2025, 7, 20, 14, 30),
                'arrival_time': datetime(2025, 7, 20, 16, 30),
                'cabin_class': 'Y',
                'cabin_code': 'Y',
                'status': 'pending'
            }
        ]
        
        print(f"\n测试保存航段数据...")
        
        try:
            # 删除现有航段
            ProjectFlightSegment.query.filter_by(ref_id=ref.id).delete()
            print("   已删除现有航段")
            
            # 添加测试航段
            for i, segment_data in enumerate(test_segments, 1):
                segment = ProjectFlightSegment(
                    ref_id=ref.id,
                    **segment_data
                )
                db.session.add(segment)
                print(f"   添加航段{i}: {segment_data['flight_number']} {segment_data['departure_airport']}-{segment_data['arrival_airport']}")
            
            # 提交事务
            db.session.commit()
            print("   ✅ 航段数据保存成功")
            
            # 验证保存结果
            saved_segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).all()
            print(f"\n验证结果:")
            print(f"   保存的航段数量: {len(saved_segments)}")
            
            for i, segment in enumerate(saved_segments, 1):
                print(f"   航段{i}: {segment.flight_number} {segment.departure_airport}-{segment.arrival_airport}")
            
            # 测试ORM关系
            print(f"\n测试ORM关系:")
            print(f"   ref.flight_segments 数量: {len(ref.flight_segments)}")
            
            for i, segment in enumerate(ref.flight_segments, 1):
                print(f"   通过关系获取航段{i}: {segment.flight_number}")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ 保存失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_flight_segment_save() 