# -*- coding: utf-8 -*-
"""
Aviationstack 航班数据获取模块

本模块提供从Aviationstack API获取航班信息的功能，包括航站楼和登机口信息。

主要功能:
1. 根据航班号获取航班详细信息 (起飞时间、到达时间、航线等)
2. 获取航站楼和登机口信息
3. 处理API响应和错误处理
4. 支持多种数据格式的解析

技术说明:
- 使用requests库进行HTTP请求
- 支持JSON响应解析
- 提供完整的错误处理和重试机制
- 支持航站楼和登机口信息的提取

使用示例:
```python
from App_new.utils.flightAviationstack import get_flight_from_aviationstack, extract_aviationstack_data

# 获取航班SQ876的信息
flight_info = get_flight_from_aviationstack('SQ876')
if flight_info:
    data = extract_aviationstack_data(flight_info, 'SQ876')
    print(data)
```

注意事项:
- 需要有效的API密钥
- API有请求频率限制
- 某些航班可能没有航站楼信息
- 建议在生产环境中添加缓存机制

"""

import requests
import json
from typing import Dict, Optional
from datetime import datetime, timedelta

# Aviationstack API配置
AVIATIONSTACK_API_KEY = '***REMOVED***'
AVIATIONSTACK_BASE_URL = 'http://api.aviationstack.com/v1/flights'

def get_flight_from_aviationstack(
    flight_number: str,
    api_key: str = None,
    dep_iata: Optional[str] = None,
    arr_iata: Optional[str] = None,
    flight_date: Optional[str] = None,
) -> Optional[Dict]:
    """
    从Aviationstack API获取航班信息
    
    Args:
        flight_number (str): 航班号，例如 'SQ876'
        api_key (str, optional): API密钥，如果不提供则使用默认密钥
        
    Returns:
        Optional[Dict]: API响应数据，如果失败则返回None
    """
    try:
        # 使用提供的API密钥或默认密钥
        if api_key is None:
            api_key = AVIATIONSTACK_API_KEY
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }

        print(f"\n正在从Aviationstack API获取航班 {flight_number} 的信息...")

        def attempt(params_label: str, params: Dict) -> Optional[Dict]:
            # 发送请求
            response = requests.get(AVIATIONSTACK_BASE_URL, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            print(f"API响应状态({params_label}): {response.status_code}")
            print(f"响应数据长度({params_label}): {len(str(data))} 字符")
            if 'error' in data:
                print(f"Aviationstack API 错误({params_label}): {data['error']}")
                return None
            if data.get('data') and len(data['data']) > 0:
                print(f"成功获取到 {len(data['data'])} 条航班数据 ({params_label})")
                return data
            return None

        # 生成不同尝试组合：优先使用提供的 dep/arr/date 过滤，否则逐步放宽
        today = datetime.utcnow().date()
        dates = []
        if flight_date:
            dates = [flight_date]
        else:
            dates = [today.isoformat(), (today - timedelta(days=1)).isoformat(), (today + timedelta(days=1)).isoformat()]

        # 尝试顺序：flight_iata + (dep/arr 可选) + date + limit=1
        for d in dates:
            base_params = {
                'access_key': api_key,
                'flight_iata': flight_number,
                'limit': 1,
                'flight_date': d,
            }
            if dep_iata:
                base_params['dep_iata'] = dep_iata
            if arr_iata:
                base_params['arr_iata'] = arr_iata
            data = attempt(f"flight_date={d}, dep={dep_iata}, arr={arr_iata}", base_params)
            if data:
                return data

        # 最后回退：不带日期，仅 flight_iata（limit=1）
        fallback_params = {
            'access_key': api_key,
            'flight_iata': flight_number,
            'limit': 1,
        }
        if dep_iata:
            fallback_params['dep_iata'] = dep_iata
        if arr_iata:
            fallback_params['arr_iata'] = arr_iata
        data = attempt("no_date_fallback", fallback_params)
        if data:
            return data

        print(f"Aviationstack API未找到航班 {flight_number} 的信息")
        return None
    
    except requests.exceptions.Timeout:
        print(f"Aviationstack API请求超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Aviationstack API请求错误: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Aviationstack API响应解析错误: {e}")
        return None
    except Exception as e:
        print(f"处理Aviationstack数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_aviationstack_data(data: Dict, flight_number: str) -> Optional[Dict]:
    """
    从Aviationstack API响应中提取和格式化航班数据
    
    Args:
        data (Dict): Aviationstack API的响应数据
        flight_number (str): 航班号
        
    Returns:
        Optional[Dict]: 格式化后的航班信息，如果提取失败则返回None
    """
    try:
        if not data.get('data') or len(data['data']) == 0:
            return None
            
        flight_data = data['data'][0]  # 获取第一个航班的数据
        
        print(f"\n提取Aviationstack航班数据:")
        print(f"航班号: {flight_number}")
        
        # 提取出发信息（兼容字段为null的情况）
        departure = (flight_data.get('departure') or {})
        departure_iata = departure.get('iata') or 'Unknown'
        departure_airport = departure.get('airport') or 'Unknown'
        departure_terminal = departure.get('terminal') or 'Unknown'
        departure_gate = departure.get('gate') or 'Unknown'
        departure_scheduled = departure.get('scheduled') or 'Unknown'
        departure_actual = departure.get('actual') or 'Unknown'
        
        print(f"出发信息:")
        print(f"  机场: {departure_iata} - {departure_airport}")
        print(f"  航站楼: {departure_terminal}")
        print(f"  登机口: {departure_gate}")
        print(f"  计划时间: {departure_scheduled}")
        print(f"  实际时间: {departure_actual}")
        
        # 提取到达信息（兼容字段为null的情况）
        arrival = (flight_data.get('arrival') or {})
        arrival_iata = arrival.get('iata') or 'Unknown'
        arrival_airport = arrival.get('airport') or 'Unknown'
        arrival_terminal = arrival.get('terminal') or 'Unknown'
        arrival_gate = arrival.get('gate') or 'Unknown'
        arrival_scheduled = arrival.get('scheduled') or 'Unknown'
        arrival_actual = arrival.get('actual') or 'Unknown'
        
        print(f"到达信息:")
        print(f"  机场: {arrival_iata} - {arrival_airport}")
        print(f"  航站楼: {arrival_terminal}")
        print(f"  登机口: {arrival_gate}")
        print(f"  计划时间: {arrival_scheduled}")
        print(f"  实际时间: {arrival_actual}")
        
        # 提取航班基本信息（兼容字段为null的情况）
        flight_info = (flight_data.get('flight') or {})
        airline_info = (flight_data.get('airline') or {})
        aircraft_info = (flight_data.get('aircraft') or {})
        
        flight_number_full = flight_info.get('iata') or flight_number
        flight_number_short = flight_info.get('number') or (flight_number[2:] if len(flight_number) > 2 else '')
        airline_code = airline_info.get('iata') or (flight_number[:2] if len(flight_number) >= 2 else '')
        airline_name = airline_info.get('name') or 'Unknown'
        aircraft_type = aircraft_info.get('iata') or 'Unknown'
        
        # 提取航班状态
        flight_status = flight_data.get('flight_status', 'Unknown')
        flight_date = flight_data.get('flight_date', 'Unknown')
        
        print(f"航班信息:")
        print(f"  完整航班号: {flight_number_full}")
        print(f"  航班编号: {flight_number_short}")
        print(f"  航空公司: {airline_code} - {airline_name}")
        print(f"  飞机型号: {aircraft_type}")
        print(f"  状态: {flight_status}")
        print(f"  日期: {flight_date}")
        
        # 格式化时间
        formatted_dep_time = format_time(departure_scheduled)
        formatted_arr_time = format_time(arrival_scheduled)
        
        # 检查是否有航站楼信息
        has_terminal_info = (
            departure_terminal != 'Unknown' or departure_gate != 'Unknown' or
            arrival_terminal != 'Unknown' or arrival_gate != 'Unknown'
        )
        
        if has_terminal_info:
            print(f"\n✅ Aviationstack提供航站楼信息:")
            if departure_terminal != 'Unknown':
                print(f"  - 出发航站楼: {departure_terminal}")
            if departure_gate != 'Unknown':
                print(f"  - 出发登机口: {departure_gate}")
            if arrival_terminal != 'Unknown':
                print(f"  - 到达航站楼: {arrival_terminal}")
            if arrival_gate != 'Unknown':
                print(f"  - 到达登机口: {arrival_gate}")
        else:
            print(f"\n⚠️ Aviationstack未提供航站楼信息")
        
        # 构建返回结果
        result = {
            'flight_number': flight_number,
            'airline': airline_code,
            'airline_num': flight_number_short,
            'airline_name': airline_name,
            'schedule_city': f"{departure_iata} {arrival_iata}",
            'schedule_timing': f"{formatted_dep_time} {formatted_arr_time}",
            'departure_terminal': departure_terminal,
            'departure_gate': departure_gate,
            'arrival_terminal': arrival_terminal,
            'arrival_gate': arrival_gate,
            'aircraft': aircraft_type,
            'status': flight_status,
            'date': flight_date,
            'departure_airport': departure_airport,
            'arrival_airport': arrival_airport,
            'departure_scheduled': departure_scheduled,
            'departure_actual': departure_actual,
            'arrival_scheduled': arrival_scheduled,
            'arrival_actual': arrival_actual,
            'data_source': 'Aviationstack'
        }
        
        return result
        
    except Exception as e:
        print(f"提取Aviationstack数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def format_time(time_str: str) -> str:
    """
    格式化时间字符串
    
    Args:
        time_str (str): 时间字符串，可能是ISO格式或HH:MM格式
        
    Returns:
        str: 格式化后的时间字符串 (HHMM格式)
    """
    if not time_str or time_str == 'Unknown':
        return 'Unknown'
    
    try:
        # 如果已经是HH:MM格式，移除冒号
        if ':' in time_str and len(time_str) == 5:
            return time_str.replace(':', '')
        
        # 如果是ISO格式，解析并转换
        if 'T' in time_str:
            # 处理ISO格式时间
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime('%H%M')
        
        return 'Unknown'
    except Exception as e:
        print(f"时间格式化错误: {e}, 输入: {time_str}")
        return 'Unknown'

def get_flight_info_aviationstack(
    flight_number: str,
    dep_iata: Optional[str] = None,
    arr_iata: Optional[str] = None,
    flight_date: Optional[str] = None,
) -> Optional[Dict]:
    """
    获取航班信息的简化函数 (Aviationstack专用)
    
    Args:
        flight_number (str): 航班号，例如 'SQ876'
        
    Returns:
        Optional[Dict]: 包含航班信息的字典，如果获取失败则返回None
    """
    try:
        # 从Aviationstack获取原始数据
        raw_data = get_flight_from_aviationstack(
            flight_number,
            dep_iata=dep_iata,
            arr_iata=arr_iata,
            flight_date=flight_date,
        )
        
        if raw_data:
            # 提取和格式化数据
            return extract_aviationstack_data(raw_data, flight_number)
        
        return None
        
    except Exception as e:
        print(f"获取Aviationstack航班信息时出错: {e}")
        return None

def test_aviationstack_connection() -> bool:
    """
    测试Aviationstack API连接
    
    Returns:
        bool: 连接是否成功
    """
    try:
        print("测试Aviationstack API连接...")
        
        # 使用一个常见的航班号进行测试
        test_flight = "SQ876"
        data = get_flight_from_aviationstack(test_flight)
        
        if data and data.get('data'):
            print("✅ Aviationstack API连接成功")
            return True
        else:
            print("❌ Aviationstack API连接失败")
            return False
            
    except Exception as e:
        print(f"❌ Aviationstack API连接测试失败: {e}")
        return False

if __name__ == "__main__":
    # 测试Aviationstack模块
    print("=" * 60)
    print("测试Aviationstack模块")
    print("=" * 60)
    
    # 测试连接
    if test_aviationstack_connection():
        print("\n" + "=" * 60)
        print("测试航班信息获取")
        print("=" * 60)
        
        # 测试获取航班信息
        test_flights = ["SQ876", "MU544", "CA123"]
        
        for flight in test_flights:
            print(f"\n测试航班: {flight}")
            flight_info = get_flight_info_aviationstack(flight)
            
            if flight_info:
                print(f"✅ 成功获取航班信息:")
                print(f"  航班号: {flight_info.get('flight_number')}")
                print(f"  航线: {flight_info.get('schedule_city')}")
                print(f"  出发航站楼: {flight_info.get('departure_terminal')}")
                print(f"  出发登机口: {flight_info.get('departure_gate')}")
                print(f"  到达航站楼: {flight_info.get('arrival_terminal')}")
                print(f"  到达登机口: {flight_info.get('arrival_gate')}")
            else:
                print(f"❌ 获取航班信息失败")
    else:
        print("❌ 无法连接到Aviationstack API，请检查网络连接和API密钥")
