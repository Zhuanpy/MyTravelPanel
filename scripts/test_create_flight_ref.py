#!/usr/bin/env python3
"""
测试创建机票REF的过程，检查航段数据保存问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_create_flight_ref():
    """测试创建机票REF的过程"""
    from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment, ProjectFlightPassenger
    from App.models.Product.BusinessType import BusinessType
    from App import create_app, db
    from datetime import datetime
    
    app = create_app()
    with app.app_context():
        print("=== 测试创建机票REF的过程 ===")
        
        # 1. 查找机票业务类型
        flight_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_type:
            print("❌ 未找到机票业务类型")
            return False
        
        # 2. 查找一个可用的header
        from App.models.projects.BookingProject import ProjectHeader
        header = ProjectHeader.query.first()
        if not header:
            print("❌ 未找到可用的header")
            return False
        
        print(f"✅ 使用header: {header.hid}")
        
        # 3. 模拟创建REF
        ref_number = ProjectRef.generate_ref_number("")
        
        ref = ProjectRef(
            header_id=header.id,
            ref_number=ref_number,
            name='测试机票REF',
            ref_type_id=flight_type.id,
            description='测试机票REF描述',
            supplier_id=None,
            contact_name='测试联系人',
            contact_phone='12345678',
            contact_email='test@example.com',
            remarks='测试备注',
            status='draft',
            payment_status='unpaid'
        )
        
        db.session.add(ref)
        db.session.flush()  # 获取ref.id
        print(f"✅ 创建REF成功: {ref.ref_number} (ID: {ref.id})")
        
        # 4. 模拟添加乘客
        passenger = ProjectFlightPassenger(
            ref_id=ref.id,
            name='张三',
            passenger_type='adult',
            selling_price=500.00,
            cost_price=450.00,
            ticket_number=None,
            pnr=None
        )
        db.session.add(passenger)
        print("✅ 添加乘客成功")
        
        # 5. 模拟添加航段
        try:
            # 模拟表单提交的航段数据
            flight_numbers = ['SQ123', 'SQ456']
            cabin_codes = ['Y', 'Y']
            departure_airports = ['SIN', 'BKK']
            arrival_airports = ['BKK', 'SIN']
            departure_dates = ['2025-08-15', '2025-08-20']
            departure_times = ['10:30', '14:30']
            arrival_dates = ['2025-08-15', '2025-08-20']
            arrival_times = ['12:30', '16:30']
            
            print(f"模拟航段数据:")
            print(f"  航班号: {flight_numbers}")
            print(f"  舱位代码: {cabin_codes}")
            print(f"  出发机场: {departure_airports}")
            print(f"  到达机场: {arrival_airports}")
            print(f"  出发日期: {departure_dates}")
            print(f"  出发时间: {departure_times}")
            print(f"  到达日期: {arrival_dates}")
            print(f"  到达时间: {arrival_times}")
            
            # 处理航段数据
            for i in range(len(flight_numbers)):
                print(f"\n处理航段 {i+1}:")
                
                # 安全获取日期和时间
                dep_date = departure_dates[i] if i < len(departure_dates) and departure_dates[i] else datetime.now().strftime('%Y-%m-%d')
                dep_time = departure_times[i] if i < len(departure_times) and departure_times[i] else '00:00'
                arr_date = arrival_dates[i] if i < len(arrival_dates) and arrival_dates[i] else dep_date
                arr_time = arrival_times[i] if i < len(arrival_times) and arrival_times[i] else '00:00'
                
                print(f"  出发日期: '{dep_date}', 出发时间: '{dep_time}'")
                print(f"  到达日期: '{arr_date}', 到达时间: '{arr_time}'")
                
                # 合并日期和时间
                dep_datetime = datetime.strptime(f"{dep_date} {dep_time}", '%Y-%m-%d %H:%M')
                arr_datetime = datetime.strptime(f"{arr_date} {arr_time}", '%Y-%m-%d %H:%M')
                
                print(f"  解析后的出发时间: {dep_datetime}")
                print(f"  解析后的到达时间: {arr_datetime}")
                
                # 创建航段
                segment = ProjectFlightSegment(
                    ref_id=ref.id,
                    flight_number=flight_numbers[i] if i < len(flight_numbers) and flight_numbers[i] else '',
                    departure_airport=departure_airports[i] if i < len(departure_airports) else '',
                    arrival_airport=arrival_airports[i] if i < len(arrival_airports) else '',
                    departure_time=dep_datetime,
                    arrival_time=arr_datetime,
                    cabin_class=cabin_codes[i] if i < len(cabin_codes) else '',
                    cabin_code=cabin_codes[i] if i < len(cabin_codes) else '',
                    status='pending'
                )
                db.session.add(segment)
                print(f"  ✅ 航段{i+1} 创建成功")
            
            # 提交事务
            db.session.commit()
            print(f"\n✅ 所有数据保存成功")
            
            # 验证保存结果
            saved_segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).all()
            print(f"验证结果:")
            print(f"  保存的航段数量: {len(saved_segments)}")
            
            for i, segment in enumerate(saved_segments, 1):
                print(f"  航段{i}: {segment.flight_number} {segment.departure_airport}-{segment.arrival_airport}")
                print(f"    出发时间: {segment.departure_time}")
                print(f"    到达时间: {segment.arrival_time}")
                print(f"    舱位代码: {segment.cabin_code}")
            
            # 清理测试数据
            db.session.delete(ref)
            db.session.commit()
            print(f"\n✅ 测试数据已清理")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 保存失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"\n✅ 测试完成")
        return True

if __name__ == '__main__':
    test_create_flight_ref() 