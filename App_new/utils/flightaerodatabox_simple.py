# -*- coding: utf-8 -*-
"""
Aerodatabox 简化版本 - 只获取最近一次航班信息
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import requests

# RapidAPI 配置
RAPIDAPI_KEY = "***REMOVED***"
RAPIDAPI_HOST = "aerodatabox.p.rapidapi.com"

def get_latest_flight_info(flight_number: str, days_back: int = 7) -> Optional[Dict]:
    """
    获取最近一次航班信息
    
    参数:
    - flight_number: 航班号 (如 "TR156")
    - days_back: 向前查找的天数，默认7天
    
    返回:
    - 包含航班信息的字典，如果未找到则返回None
    """
    try:
        # 构建时间窗口：从今天往前查找指定天数
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        start_str = start_date.strftime("%Y-%m-%dT%H:%M")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M")
        
        # 构建URL
        url = f"https://{RAPIDAPI_HOST}/flights/number/{flight_number}/{start_str}/{end_str}"
        
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        print(f"正在查询航班 {flight_number} 的最近信息...")
        print(f"查询时间范围: {start_str} 到 {end_str}")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 检查是否有数据
        if not data or not isinstance(data, list) or len(data) == 0:
            print(f"未找到航班 {flight_number} 的信息")
            return None
        
        # 取第一条（最新的）航班信息
        flight = data[0]
        print(f"找到 {len(data)} 条航班记录，返回最新的一条")
        
        # 提取信息
        dep = flight.get("departure", {})
        arr = flight.get("arrival", {})
        aircraft = flight.get("aircraft", {})
        
        # 获取机场信息
        dep_airport = dep.get("airport", {})
        arr_airport = arr.get("airport", {})
        
        # 格式化时间
        def format_time(time_str):
            if not time_str:
                return "Unknown"
            try:
                # 处理ISO时间格式
                if 'T' in time_str:
                    dt = datetime.fromisoformat(time_str.replace('Z', ''))
                    return dt.strftime('%H%M')
                return time_str
            except:
                return "Unknown"
        
        result = {
            "flight_number": flight_number,
            "schedule_city": f"{dep_airport.get('iata', 'Unknown')} {arr_airport.get('iata', 'Unknown')}",
            "schedule_timing": f"{format_time(dep.get('scheduledTimeLocal'))} {format_time(arr.get('scheduledTimeLocal'))}",
            "departure_terminal": dep.get("terminal", "Unknown"),
            "departure_gate": dep.get("gate", "Unknown"),
            "arrival_terminal": arr.get("terminal", "Unknown"),
            "arrival_gate": arr.get("gate", "Unknown"),
            "aircraft": aircraft.get("model", "Unknown"),
            "status": flight.get("status", "Unknown"),
            "data_source": "Aerodatabox (Latest)",
            "flight_date": flight.get("departure", {}).get("scheduledTimeLocal", "Unknown")[:10] if flight.get("departure", {}).get("scheduledTimeLocal") else "Unknown"
        }
        
        print(f"成功获取航班 {flight_number} 的最近信息")
        return result
        
    except requests.RequestException as e:
        print(f"网络请求失败: {e}")
        return None
    except Exception as e:
        print(f"获取航班信息时出错: {e}")
        return None

def test_latest_flight():
    """测试获取最近航班信息"""
    print("=" * 50)
    print("测试获取最近航班信息")
    print("=" * 50)
    
    test_flights = ["TR156", "SQ876", "MU544"]
    
    for flight_num in test_flights:
        print(f"\n测试航班: {flight_num}")
        result = get_latest_flight_info(flight_num)
        
        if result:
            print("✅ 成功获取航班信息:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print("❌ 获取航班信息失败")
        print("-" * 30)

if __name__ == "__main__":
    test_latest_flight()
