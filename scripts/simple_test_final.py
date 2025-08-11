#!/usr/bin/env python3
"""
简单的日期转换测试
"""

def convert_singapore_date(date_str):
    """转换新加坡日期格式"""
    try:
        # 分割日期字符串
        parts = date_str.split('/')
        if len(parts) != 3:
            return date_str
        
        year_str, month_str, day_str = parts
        
        # 新的转换规则
        # 原来年份的后两位作为新的日期
        new_day = year_str[-2:] if len(year_str) >= 2 else year_str
        
        # 月份保持不变
        new_month = month_str
        
        # 原来日期前面加上 "20" 变成新的年份
        new_year = "20" + day_str
        
        # 组合成新格式
        result = f"{new_day}/{new_month}/{new_year}"
        
        return result
        
    except Exception as e:
        print(f"转换错误: {e}")
        return date_str

def test_conversion():
    """测试转换函数"""
    test_cases = [
        ("2029/7/25", "29/7/2025"),
        ("2028/12/15", "28/12/2015"),
        ("2030/3/8", "30/3/2008"),
        ("2025/6/20", "25/6/2020"),
    ]
    
    print("测试新的新加坡日期转换规则")
    print("=" * 50)
    
    for input_date, expected in test_cases:
        result = convert_singapore_date(input_date)
        status = "✓" if result == expected else "✗"
        print(f"{status} 输入: {input_date:12} -> 输出: {result:12} (期望: {expected})")
    
    print("\n详细转换过程 (以 2029/7/25 为例):")
    print("1. 分割: year='2029', month='7', day='25'")
    print("2. 新日期: year[-2:] = '29'")
    print("3. 新月份: month = '7'")
    print("4. 新年份: '20' + day = '20' + '25' = '2025'")
    print("5. 结果: '29/7/2025'")

if __name__ == "__main__":
    test_conversion() 