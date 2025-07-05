#!/usr/bin/env python3
"""
测试REF和乘客价格计算逻辑
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_price_calculation():
    """测试价格计算逻辑"""
    
    # 模拟乘客价格数据
    passenger_data = [
        {'name': '张三', 'selling_price': 500.00, 'cost_price': 400.00},
        {'name': '李四', 'selling_price': 450.00, 'cost_price': 380.00},
        {'name': '王五', 'selling_price': 300.00, 'cost_price': 250.00},
    ]
    
    print("乘客价格数据:")
    for i, passenger in enumerate(passenger_data, 1):
        print(f"  乘客{i}: {passenger['name']} - 售价: {passenger['selling_price']}, 成本: {passenger['cost_price']}")
    
    # 计算总价
    total_selling_price = sum(p['selling_price'] for p in passenger_data)
    total_cost_price = sum(p['cost_price'] for p in passenger_data)
    
    print(f"\n计算结果:")
    print(f"  总售价: {total_selling_price}")
    print(f"  总成本: {total_cost_price}")
    print(f"  总利润: {total_selling_price - total_cost_price}")
    print(f"  利润率: {((total_selling_price - total_cost_price) / total_selling_price * 100):.2f}%")
    
    # 测试边界情况
    print(f"\n边界情况测试:")
    
    # 空价格处理
    empty_prices = [
        {'name': '测试1', 'selling_price': '', 'cost_price': '100'},
        {'name': '测试2', 'selling_price': '200', 'cost_price': ''},
        {'name': '测试3', 'selling_price': '0', 'cost_price': '50'},
    ]
    
    print("空价格处理:")
    for passenger in empty_prices:
        selling_price = float(passenger['selling_price']) if passenger['selling_price'] and passenger['selling_price'] != '0' else 0
        cost_price = float(passenger['cost_price']) if passenger['cost_price'] and passenger['cost_price'] != '0' else 0
        
        print(f"  {passenger['name']}: 售价={selling_price}, 成本={cost_price}")
    
    print("\n✅ 价格计算逻辑测试完成")

def test_model_properties():
    """测试模型计算属性"""
    print("\n=== 模型计算属性测试 ===")
    
    # 模拟ProjectRef的计算属性
    class MockProjectRef:
        def __init__(self, passengers):
            self.flight_passengers = passengers
        
        @property
        def total_flight_selling_price(self):
            """计算机票总售价"""
            return sum(p.get('selling_price', 0) or 0 for p in self.flight_passengers)
        
        @property
        def total_flight_cost_price(self):
            """计算机票总成本"""
            return sum(p.get('cost_price', 0) or 0 for p in self.flight_passengers)
        
        @property
        def flight_profit(self):
            """计算机票利润"""
            return self.total_flight_selling_price - self.total_flight_cost_price
    
    # 测试数据
    passengers = [
        {'selling_price': 500.00, 'cost_price': 400.00},
        {'selling_price': 450.00, 'cost_price': 380.00},
        {'selling_price': None, 'cost_price': 250.00},  # 测试None值
        {'selling_price': 0, 'cost_price': 100.00},     # 测试0值
    ]
    
    ref = MockProjectRef(passengers)
    
    print(f"总售价: {ref.total_flight_selling_price}")
    print(f"总成本: {ref.total_flight_cost_price}")
    print(f"总利润: {ref.flight_profit}")
    
    print("\n✅ 模型计算属性测试完成")

if __name__ == "__main__":
    test_price_calculation()
    test_model_properties() 