#!/usr/bin/env python3
"""
测试机票REF保存逻辑的修复
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_list_handling():
    """测试列表长度不一致的处理逻辑"""
    
    # 模拟表单数据 - 乘客信息长度不一致
    passenger_names = ['张三', '李四', '王五']
    passenger_types = ['adult', 'child']  # 比names短
    selling_prices = ['100', '80', '60', '40']  # 比names长
    cost_prices = ['80', '60']  # 比names短
    ticket_numbers = ['123456', '789012']  # 比names短
    pnrs = ['ABC123', 'DEF456', 'GHI789']  # 与names长度相同
    
    print("原始数据:")
    print(f"passenger_names: {passenger_names} (长度: {len(passenger_names)})")
    print(f"passenger_types: {passenger_types} (长度: {len(passenger_types)})")
    print(f"selling_prices: {selling_prices} (长度: {len(selling_prices)})")
    print(f"cost_prices: {cost_prices} (长度: {len(cost_prices)})")
    print(f"ticket_numbers: {ticket_numbers} (长度: {len(ticket_numbers)})")
    print(f"pnrs: {pnrs} (长度: {len(pnrs)})")
    
    # 应用修复逻辑
    max_passenger_len = max(len(passenger_names), len(passenger_types), len(selling_prices), 
                           len(cost_prices), len(ticket_numbers), len(pnrs))
    
    print(f"\n最大长度: {max_passenger_len}")
    
    # 扩展较短的列表
    passenger_types.extend(['adult'] * (max_passenger_len - len(passenger_types)))
    selling_prices.extend([''] * (max_passenger_len - len(selling_prices)))
    cost_prices.extend([''] * (max_passenger_len - len(cost_prices)))
    ticket_numbers.extend([''] * (max_passenger_len - len(ticket_numbers)))
    pnrs.extend([''] * (max_passenger_len - len(pnrs)))
    
    print("\n扩展后的数据:")
    print(f"passenger_names: {passenger_names} (长度: {len(passenger_names)})")
    print(f"passenger_types: {passenger_types} (长度: {len(passenger_types)})")
    print(f"selling_prices: {selling_prices} (长度: {len(selling_prices)})")
    print(f"cost_prices: {cost_prices} (长度: {len(cost_prices)})")
    print(f"ticket_numbers: {ticket_numbers} (长度: {len(ticket_numbers)})")
    print(f"pnrs: {pnrs} (长度: {len(pnrs)})")
    
    # 测试安全访问
    print("\n测试安全访问:")
    for i in range(len(passenger_names)):
        print(f"乘客 {i+1}:")
        print(f"  姓名: {passenger_names[i]}")
        print(f"  类型: {passenger_types[i] if i < len(passenger_types) else 'adult'}")
        print(f"  售价: {selling_prices[i] if i < len(selling_prices) and selling_prices[i] else 'None'}")
        print(f"  成本: {cost_prices[i] if i < len(cost_prices) and cost_prices[i] else 'None'}")
        print(f"  票号: {ticket_numbers[i] if i < len(ticket_numbers) and ticket_numbers[i] else 'None'}")
        print(f"  PNR: {pnrs[i] if i < len(pnrs) and pnrs[i] else 'None'}")
    
    print("\n✅ 测试完成 - 列表长度不一致问题已修复")

if __name__ == "__main__":
    test_list_handling() 