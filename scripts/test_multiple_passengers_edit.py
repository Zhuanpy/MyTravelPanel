#!/usr/bin/env python3
"""
测试多乘客REF的编辑功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_multiple_passengers_edit():
    """测试多乘客REF的编辑功能"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightPassenger, ProjectFlightSegment
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from sqlalchemy.orm import joinedload
    
    app = create_app()
    with app.app_context():
        print("=== 测试多乘客REF编辑功能 ===")
        
        # 1. 查找机票业务类型
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return
        
        # 2. 查找一个多乘客的REF进行测试
        test_ref = ProjectRef.query.filter_by(ref_type_id=flight_type.id).options(
            joinedload(ProjectRef.flight_passengers),
            joinedload(ProjectRef.flight_segments)
        ).filter(
            ProjectRef.id == 150  # 使用我们之前发现的多乘客REF
        ).first()
        
        if not test_ref:
            print("❌ 未找到测试REF (ID: 150)")
            return
        
        print(f"✅ 找到测试REF: {test_ref.ref_number}")
        print(f"   名称: {test_ref.name}")
        print(f"   乘客数量: {len(test_ref.flight_passengers)}")
        print(f"   航段数量: {len(test_ref.flight_segments)}")
        
        # 3. 检查乘客数据
        print(f"\n📋 乘客数据:")
        for i, passenger in enumerate(test_ref.flight_passengers, 1):
            print(f"   乘客{i}: {passenger.name} ({passenger.passenger_type})")
            print(f"     售价: {passenger.selling_price}")
            print(f"     成本: {passenger.cost_price}")
            print(f"     电子客票号: {passenger.ticket_number}")
            print(f"     PNR: {passenger.pnr}")
        
        # 4. 检查航段数据
        print(f"\n✈️ 航段数据:")
        for i, segment in enumerate(test_ref.flight_segments, 1):
            print(f"   航段{i}: {segment.flight_number}")
            print(f"     路线: {segment.departure_airport} → {segment.arrival_airport}")
            print(f"     时间: {segment.departure_time} → {segment.arrival_time}")
            print(f"     舱位: {segment.cabin_code}")
        
        # 5. 模拟模板数据传递
        print(f"\n🔍 模拟模板数据传递:")
        
        # 模拟乘客数据传递给JavaScript
        passengers_js = []
        for p in test_ref.flight_passengers:
            passenger_data = {
                "name": p.name or '',
                "passenger_type": p.passenger_type or 'adult',
                "selling_price": float(p.selling_price) if p.selling_price else 0,
                "cost_price": float(p.cost_price) if p.cost_price else 0,
                "ticket_number": p.ticket_number or '',
                "pnr": p.pnr or ''
            }
            passengers_js.append(passenger_data)
        
        print(f"   传递给JavaScript的乘客数据:")
        for i, p_data in enumerate(passengers_js, 1):
            print(f"     乘客{i}: {p_data}")
        
        # 6. 模拟航段数据传递
        segments_js = []
        for s in test_ref.flight_segments:
            segment_data = {
                "flight_number": s.flight_number or '',
                "cabin_code": s.cabin_code or '',
                "departure_airport": s.departure_airport or '',
                "arrival_airport": s.arrival_airport or '',
                "departure_time": s.departure_time.isoformat() if s.departure_time else '',
                "arrival_time": s.arrival_time.isoformat() if s.arrival_time else ''
            }
            segments_js.append(segment_data)
        
        print(f"\n   传递给JavaScript的航段数据:")
        for i, s_data in enumerate(segments_js, 1):
            print(f"     航段{i}: {s_data}")
        
        # 7. 验证数据完整性
        print(f"\n✅ 数据完整性验证:")
        print(f"   乘客数据完整性: {'✅' if len(passengers_js) == len(test_ref.flight_passengers) else '❌'}")
        print(f"   航段数据完整性: {'✅' if len(segments_js) == len(test_ref.flight_segments) else '❌'}")
        
        # 8. 测试建议
        print(f"\n💡 测试建议:")
        print(f"   1. 访问编辑页面: /projects/flight-ref/edit/{test_ref.id}")
        print(f"   2. 检查浏览器控制台，查看乘客数据和航段数据是否正确加载")
        print(f"   3. 验证页面上的乘客信息是否与数据库一致")
        print(f"   4. 尝试修改乘客信息并保存，检查是否正常工作")
        
        # 9. 检查可能的问题
        print(f"\n🔍 潜在问题检查:")
        
        # 检查是否有空值
        empty_passengers = [p for p in test_ref.flight_passengers if not p.name]
        if empty_passengers:
            print(f"   ⚠️ 发现 {len(empty_passengers)} 个乘客姓名为空")
        
        # 检查价格数据
        price_issues = [p for p in test_ref.flight_passengers if p.selling_price is None or p.cost_price is None]
        if price_issues:
            print(f"   ⚠️ 发现 {len(price_issues)} 个乘客价格数据为空")
        
        # 检查航段数据
        empty_segments = [s for s in test_ref.flight_segments if not s.flight_number]
        if empty_segments:
            print(f"   ⚠️ 发现 {len(empty_segments)} 个航段航班号为空")
        
        if not empty_passengers and not price_issues and not empty_segments:
            print(f"   ✅ 数据完整性良好，没有发现明显问题")

if __name__ == "__main__":
    test_multiple_passengers_edit() 