#!/usr/bin/env python3
"""
测试REF详情页面路由逻辑
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_ref_detail_routing():
    """测试REF详情页面路由逻辑"""
    
    # 模拟不同的业务类型
    business_types = [
        {'name': '机票', 'expected_route': 'flight_ref_detail'},
        {'name': '酒店', 'expected_route': 'hotel_ref_detail'},
        {'name': '签证', 'expected_route': 'visa_ref_detail'},
        {'name': '旅游团', 'expected_route': 'tour_ref_detail'},
        {'name': '保险', 'expected_route': 'insurance_ref_detail'},
        {'name': '交通', 'expected_route': 'transport_ref_detail'},
        {'name': '其他', 'expected_route': 'ref_detail'},  # 通用详情页面
        {'name': None, 'expected_route': 'ref_detail'},    # 未分类
    ]
    
    print("REF详情页面路由测试:")
    print("=" * 50)
    
    for i, business_type in enumerate(business_types, 1):
        type_name = business_type['name'] or '未分类'
        expected_route = business_type['expected_route']
        
        print(f"{i}. 业务类型: {type_name}")
        print(f"   预期路由: {expected_route}")
        
        # 模拟路由逻辑
        if business_type['name'] == '机票':
            actual_route = 'flight_ref_detail'
        elif business_type['name'] == '酒店':
            actual_route = 'hotel_ref_detail'
        elif business_type['name'] == '签证':
            actual_route = 'visa_ref_detail'
        elif business_type['name'] == '旅游团':
            actual_route = 'tour_ref_detail'
        elif business_type['name'] == '保险':
            actual_route = 'insurance_ref_detail'
        elif business_type['name'] == '交通':
            actual_route = 'transport_ref_detail'
        else:
            actual_route = 'ref_detail'  # 通用详情页面
        
        print(f"   实际路由: {actual_route}")
        print(f"   结果: {'✅ 正确' if actual_route == expected_route else '❌ 错误'}")
        print()
    
    print("路由逻辑总结:")
    print("- 机票REF → flight_ref_detail.html (显示乘客、航段信息)")
    print("- 酒店REF → hotel_ref_detail.html (显示房间、入住信息)")
    print("- 签证REF → visa_ref_detail.html (显示申请人、签证信息)")
    print("- 旅游团REF → tour_ref_detail.html (显示团期、行程信息)")
    print("- 保险REF → insurance_ref_detail.html (显示保险信息)")
    print("- 交通REF → transport_ref_detail.html (显示交通信息)")
    print("- 其他类型 → ref_detail.html (通用详情页面)")
    
    print("\n✅ 路由逻辑测试完成")

def test_template_structure():
    """测试模板结构"""
    print("\n=== 模板结构测试 ===")
    
    templates = [
        'App/templates/projects/BookingProject/flight_ref_detail.html',
        'App/templates/projects/BookingProject/hotel_ref_detail.html',
        'App/templates/projects/BookingProject/visa_ref_detail.html',
        'App/templates/projects/BookingProject/tour_ref_detail.html',
        'App/templates/projects/BookingProject/insurance_ref_detail.html',
        'App/templates/projects/BookingProject/transport_ref_detail.html',
        'App/templates/projects/BookingProject/ref_detail.html',
    ]
    
    for template in templates:
        if os.path.exists(template):
            print(f"✅ {template} - 存在")
        else:
            print(f"❌ {template} - 不存在")
    
    print("\n✅ 模板结构测试完成")

if __name__ == "__main__":
    test_ref_detail_routing()
    test_template_structure() 