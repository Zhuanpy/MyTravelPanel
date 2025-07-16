#!/usr/bin/env python3
"""
调试创建机票REF时航段数据保存的问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def debug_flight_segment_save():
    """调试创建机票REF时航段数据保存的问题"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment, ProjectFlightPassenger
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from datetime import datetime
    
    app = create_app()
    with app.app_context():
        print("=== 调试创建机票REF时航段数据保存的问题 ===")
        
        # 1. 查找最近的机票REF
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return False
        
        # 查找最近创建的机票REF
        recent_refs = ProjectRef.query.filter_by(ref_type_id=flight_type.id).order_by(ProjectRef.created_at.desc()).limit(5).all()
        
        if not recent_refs:
            print("❌ 未找到机票REF")
            return False
        
        print(f"找到 {len(recent_refs)} 个最近的机票REF:")
        
        for i, ref in enumerate(recent_refs, 1):
            print(f"\n{i}. REF ID: {ref.id}")
            print(f"   名称: {ref.name}")
            print(f"   创建时间: {ref.created_at}")
            print(f"   航段数量: {len(ref.flight_segments)}")
            print(f"   乘客数量: {len(ref.flight_passengers)}")
            
            # 检查航段数据
            if ref.flight_segments:
                for j, segment in enumerate(ref.flight_segments, 1):
                    print(f"     航段{j}: {segment.flight_number} {segment.departure_airport}-{segment.arrival_airport}")
                    print(f"       出发时间: {segment.departure_time}")
                    print(f"       到达时间: {segment.arrival_time}")
                    print(f"       舱位代码: {segment.cabin_code}")
            else:
                print("     ❌ 没有航段数据")
        
        # 2. 模拟表单提交数据
        print(f"\n=== 模拟表单提交数据 ===")
        
        # 模拟一个简单的表单数据
        mock_form_data = {
            'header_id': recent_refs[0].header_id,
            'ref_id': '',  # 创建新REF
            'name': '测试机票REF',
            'description': '测试机票REF描述',
            'supplier_id': '',
            'contact_name': '测试联系人',
            'contact_phone': '12345678',
            'contact_email': 'test@example.com',
            'remarks': '测试备注',
            'status': 'draft',
            'payment_status': 'unpaid',
            'flight_number[]': ['SQ123', 'SQ456'],
            'cabin_code[]': ['Y', 'Y'],
            'departure_airport[]': ['SIN', 'BKK'],
            'arrival_airport[]': ['BKK', 'SIN'],
            'departure_date[]': ['2025-08-15', '2025-08-20'],
            'departure_time[]': ['2025-08-15 10:30', '2025-08-20 14:30'],
            'arrival_date[]': ['2025-08-15', '2025-08-20'],
            'arrival_time[]': ['2025-08-15 12:30', '2025-08-20 16:30'],
            'passenger_name[]': ['张三'],
            'passenger_type[]': ['adult'],
            'selling_price[]': ['500.00'],
            'cost_price[]': ['450.00'],
            'ticket_number[]': [''],
            'pnr[]': ['']
        }
        
        print("模拟表单数据:")
        print(f"  航段数量: {len(mock_form_data['flight_number[]'])}")
        print(f"  乘客数量: {len(mock_form_data['passenger_name[]'])}")
        
        # 3. 分析保存逻辑中的问题
        print(f"\n=== 分析保存逻辑中的问题 ===")
        
        # 检查航段保存逻辑
        flight_numbers = mock_form_data['flight_number[]']
        cabin_codes = mock_form_data['cabin_code[]']
        departure_airports = mock_form_data['departure_airport[]']
        arrival_airports = mock_form_data['arrival_airport[]']
        departure_dates = mock_form_data['departure_date[]']
        departure_times = mock_form_data['departure_time[]']
        arrival_dates = mock_form_data['arrival_date[]']
        arrival_times = mock_form_data['arrival_time[]']
        
        print("航段数据:")
        for i in range(len(flight_numbers)):
            print(f"  航段{i+1}:")
            print(f"    航班号: '{flight_numbers[i]}'")
            print(f"    舱位代码: '{cabin_codes[i]}'")
            print(f"    出发机场: '{departure_airports[i]}'")
            print(f"    到达机场: '{arrival_airports[i]}'")
            print(f"    出发日期: '{departure_dates[i]}'")
            print(f"    出发时间: '{departure_times[i]}'")
            print(f"    到达日期: '{arrival_dates[i]}'")
            print(f"    到达时间: '{arrival_times[i]}'")
        
        # 4. 检查可能的问题
        print(f"\n=== 检查可能的问题 ===")
        
        # 问题1: 检查是否有空航班号
        empty_flight_numbers = [i for i, fn in enumerate(flight_numbers) if not fn.strip()]
        if empty_flight_numbers:
            print(f"❌ 发现空航班号: 索引 {empty_flight_numbers}")
        else:
            print("✅ 所有航班号都不为空")
        
        # 问题2: 检查日期时间格式
        for i in range(len(departure_times)):
            try:
                dep_datetime = datetime.strptime(departure_times[i], '%Y-%m-%d %H:%M')
                print(f"✅ 航段{i+1} 出发时间解析成功: {dep_datetime}")
            except ValueError as e:
                print(f"❌ 航段{i+1} 出发时间解析失败: {e}")
        
        # 问题3: 检查字段长度一致性
        max_segment_len = max(len(flight_numbers), len(cabin_codes), len(departure_airports),
                             len(arrival_airports), len(departure_dates), len(departure_times),
                             len(arrival_dates), len(arrival_times))
        
        print(f"字段长度检查:")
        print(f"  航班号: {len(flight_numbers)}")
        print(f"  舱位代码: {len(cabin_codes)}")
        print(f"  出发机场: {len(departure_airports)}")
        print(f"  到达机场: {len(arrival_airports)}")
        print(f"  出发日期: {len(departure_dates)}")
        print(f"  出发时间: {len(departure_times)}")
        print(f"  到达日期: {len(arrival_dates)}")
        print(f"  到达时间: {len(arrival_times)}")
        print(f"  最大长度: {max_segment_len}")
        
        if all(len(field) == max_segment_len for field in [flight_numbers, cabin_codes, departure_airports, 
                                                          arrival_airports, departure_dates, departure_times,
                                                          arrival_dates, arrival_times]):
            print("✅ 所有字段长度一致")
        else:
            print("❌ 字段长度不一致")
        
        # 5. 检查最新的REF是否有航段数据
        print(f"\n=== 检查最新REF的航段数据 ===")
        
        latest_ref = recent_refs[0]
        segments = ProjectFlightSegment.query.filter_by(ref_id=latest_ref.id).all()
        
        print(f"最新REF ID: {latest_ref.id}")
        print(f"数据库中的航段数量: {len(segments)}")
        
        if segments:
            for i, segment in enumerate(segments, 1):
                print(f"  航段{i}: {segment.flight_number} {segment.departure_airport}-{segment.arrival_airport}")
        else:
            print("  ❌ 数据库中没有找到航段数据")
            
            # 检查是否有其他REF的航段数据
            all_segments = ProjectFlightSegment.query.all()
            print(f"数据库中总航段数量: {len(all_segments)}")
            
            if all_segments:
                print("最近的航段数据:")
                for segment in all_segments[-5:]:  # 显示最近5个航段
                    print(f"  REF ID {segment.ref_id}: {segment.flight_number} {segment.departure_airport}-{segment.arrival_airport}")
        
        print(f"\n✅ 调试完成")
        return True

if __name__ == '__main__':
    debug_flight_segment_save() 