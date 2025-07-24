#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试机票相关模型
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.projects.BookingProject import ProjectHeader, ProjectRef, ProjectFlightPassenger, ProjectFlightSegment
from App.models.Product.BusinessType import BusinessType
from App.models.Product.Suppliers import Supplier
from App.exts import db
from datetime import datetime

def test_flight_models():
    """测试机票模型"""
    app = create_app()
    
    with app.app_context():
        try:
            # 1. 检查业务类型
            flight_type = BusinessType.query.filter_by(name='机票').first()
            if not flight_type:
                print("❌ 未找到机票业务类型，请先创建")
                return False
            print(f"✅ 找到机票业务类型: {flight_type.name}")
            
            # 2. 检查供应商
            suppliers = Supplier.query.limit(5).all()
            if not suppliers:
                print("❌ 未找到供应商，请先创建")
                return False
            print(f"✅ 找到 {len(suppliers)} 个供应商")
            
            # 3. 检查项目主表
            headers = ProjectHeader.query.limit(3).all()
            if not headers:
                print("❌ 未找到项目主表，请先创建")
                return False
            print(f"✅ 找到 {len(headers)} 个项目主表")
            
            # 4. 测试创建机票REF
            header = headers[0]
            print(f"\n📋 测试创建机票REF，使用项目: {header.hid}")
            
            # 创建REF
            ref_number = ProjectRef.generate_ref_number(header.hid)
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name='测试机票订单',
                ref_type_id=flight_type.id,
                description='测试机票订单描述',
                supplier_id=suppliers[0].supplier_id,
                contact_name='测试联系人',
                contact_phone='12345678',
                contact_email='test@example.com',
                remarks='测试备注',
                status='draft'
            )
            db.session.add(ref)
            db.session.flush()
            print(f"✅ 创建REF成功: {ref.ref_number}")
            
            # 创建乘客
            passenger = ProjectFlightPassenger(
                ref_id=ref.id,
                name='张三',
                passenger_type='adult',
                selling_price=500.00,
                cost_price=400.00,
                ticket_number='1234567890123',
                pnr='ABC123'
            )
            db.session.add(passenger)
            print("✅ 创建乘客成功")
            
            # 创建航段
            segment = ProjectFlightSegment(
                ref_id=ref.id,
                flight_number='CA123',
                departure_airport='SIN',
                arrival_airport='HKG',
                departure_time=datetime(2024, 12, 25, 10, 30),
                arrival_time=datetime(2024, 12, 25, 14, 30),
                cabin_class='Economy',
                cabin_code='Y',
                status='pending'
            )
            db.session.add(segment)
            print("✅ 创建航段成功")
            
            # 提交事务
            db.session.commit()
            print("✅ 所有数据保存成功")
            
            # 测试查询
            print(f"\n📊 查询结果:")
            print(f"REF ID: {ref.id}")
            print(f"乘客数量: {len(ref.flight_passengers)}")
            print(f"航段数量: {len(ref.flight_segments)}")
            print(f"总售价: {ref.total_flight_selling_price}")
            print(f"总成本: {ref.total_flight_cost_price}")
            print(f"利润: {ref.flight_profit}")
            
            # 清理测试数据
            db.session.delete(ref)
            db.session.commit()
            print("✅ 测试数据清理完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("🚀 开始测试机票模型...")
    success = test_flight_models()
    if success:
        print("\n🎉 所有测试通过！")
    else:
        print("\n💥 测试失败！") 