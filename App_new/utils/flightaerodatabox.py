# -*- coding: utf-8 -*-
"""
Aerodatabox 航班数据获取模块（轻量封装）

功能
- 通过航班号 + 日期时间窗口，查询航班基础信息，包含航站楼/登机口（如数据源提供）。
- 兼容两种认证方式：
  1) 直连 Aerodatabox（请求头: X-Api-Key）
  2) 通过 RapidAPI（请求头: X-RapidAPI-Key / X-RapidAPI-Host）

用法示例
    from App_new.utils.flightaerodatabox import get_flight_info_aerodatabox
    data = get_flight_info_aerodatabox(
        "MU544", dep_iata="SIN", arr_iata="PVG", flight_date="2025-10-06"
    )
    print(data)

说明
- Aerodatabox 时间窗口采用本地或UTC时间段，本文实现使用“当天 00:00~23:59（本地）”的宽窗口；
  如需更严谨，可切换为 UTC 并传入具体时区。
- 返回字段不足时，统一回退为 'Unknown'。
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import requests


# ============================= 配置 =============================
# 直连模式（推荐自备Key）
AERODATABOX_API_KEY: str = ""  # 如直连使用，填入 X-Api-Key
AERODATABOX_BASE_URL: str = "https://aerodatabox.com/api/v1"

# RapidAPI 模式（如使用 RapidAPI）
RAPIDAPI_KEY: str = "***REMOVED***"
RAPIDAPI_HOST: str = "aerodatabox.p.rapidapi.com"
RAPIDAPI_BASE_URL: str = f"https://{RAPIDAPI_HOST}"

# 调试开关
DEBUG_MODE: bool = True  # 启用调试模式


def _fmt_hhmm(iso_time: Optional[str]) -> str:
    """将 ISO 时间（如 2025-10-06T08:20）格式化为 HHMM。"""
    if not iso_time:
        return "Unknown"
    try:
        # 处理带时区的ISO时间格式
        if iso_time.endswith('Z'):
            # UTC时间
            ts = iso_time.replace("Z", "+00:00")
        elif '+' in iso_time or iso_time.count('-') > 2:
            # 带时区的时间，直接使用
            ts = iso_time
        else:
            # 没有时区信息的时间
            ts = iso_time
        
        # 解析时间
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H%M")
    except Exception as e:
        if DEBUG_MODE:
            print(f"时间格式化错误: {e}, 输入: {iso_time}")
        return "Unknown"


def get_flight_from_aerodatabox(
    flight_number: str,
    *,
    dep_iata: Optional[str] = None,
    arr_iata: Optional[str] = None,
    flight_date: Optional[str] = None,
    use_rapidapi: bool = False,
) -> Optional[Dict]:
    """
    直接调用 Aerodatabox 接口，返回原始响应（已基础校验）。

    参数
    - flight_number: 航班号（如 MU544）
    - dep_iata/arr_iata: 出发/到达 IATA（可选，用于过滤）
    - flight_date: 日期 'YYYY-MM-DD'，若为空则使用今日
    - use_rapidapi: 是否通过 RapidAPI 访问
    """
    try:
        if not flight_number:
            return None

        # 生成时间窗口（本地日期 00:00~23:59）
        if flight_date:
            try:
                base = datetime.fromisoformat(flight_date)
            except Exception:
                base = datetime.utcnow()
        else:
            base = datetime.utcnow()
        start_dt = base.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = base.replace(hour=23, minute=59, second=59, microsecond=0)
        start_str = start_dt.strftime("%Y-%m-%dT%H:%M")
        end_str = end_dt.strftime("%Y-%m-%dT%H:%M")

        # 构造 URL（Aerodatabox: /flights/number/{flight}/{from}/{to}）
        if use_rapidapi:
            base_url = RAPIDAPI_BASE_URL
        else:
            base_url = AERODATABOX_BASE_URL
        url = f"{base_url}/flights/number/{flight_number}/{start_str}/{end_str}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        if use_rapidapi:
            headers.update({
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": RAPIDAPI_HOST,
            })
        else:
            headers.update({
                "X-Api-Key": AERODATABOX_API_KEY,
            })

        params = {}
        if dep_iata:
            params["depIata"] = dep_iata
        if arr_iata:
            params["arrIata"] = arr_iata

        if DEBUG_MODE:
            print(f"\n=== Aerodatabox API 调用调试 ===")
            print(f"请求URL: {url}")
            print(f"请求参数: {params}")
            print(f"请求头: {headers}")
        
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if DEBUG_MODE:
            print(f"响应状态码: {resp.status_code}")
            print(f"响应头: {dict(resp.headers)}")
            print(f"原始响应数据: {data}")
            print(f"响应数据类型: {type(data)}")

        # 返回结果通常是列表或包含 'items' 的对象
        if isinstance(data, dict) and data.get("items"):
            items = data["items"]
        elif isinstance(data, list):
            items = data
        else:
            items = []

        if DEBUG_MODE:
            print(f"提取的items: {items}")
            print(f"items数量: {len(items) if items else 0}")

        if not items:
            if DEBUG_MODE:
                print("没有找到航班数据")
            return None

        if DEBUG_MODE:
            print("找到航班数据，返回第一条记录")
            print(f"第一条记录详情: {items[0] if items else 'None'}")

        return {"data": items}
    except requests.RequestException:
        return None
    except Exception:
        return None


def get_flight_info_aerodatabox(
    flight_number: str,
    *,
    dep_iata: Optional[str] = None,
    arr_iata: Optional[str] = None,
    flight_date: Optional[str] = None,
    use_rapidapi: bool = False,
    latest_only: bool = False,
) -> Optional[Dict]:
    """
    高级封装：提取并统一返回系统需要的核心字段。
    
    参数:
    - latest_only: 如果为True，查找最近7天内的最新航班；如果为False，使用指定的flight_date
    
    返回结构：
    {
        'flight_number': str,
        'schedule_city': 'SIN PVG',
        'schedule_timing': 'HHMM HHMM',
        'departure_terminal': 'Unknown'|str,
        'departure_gate': 'Unknown'|str,
        'arrival_terminal': 'Unknown'|str,
        'arrival_gate': 'Unknown'|str,
        'aircraft': 'Unknown'|str,
        'status': 'Unknown'|str,
    }
    """
    # 如果要求最近航班，使用最近7天的时间窗口
    if latest_only:
        # 使用最近7天的时间窗口查找最新航班
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        flight_date = start_date.strftime('%Y-%m-%d')
        if DEBUG_MODE:
            print(f"查找最近航班，时间窗口: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    
    if DEBUG_MODE:
        print(f"\n=== 开始处理航班 {flight_number} ===")
        print(f"参数: dep_iata={dep_iata}, arr_iata={arr_iata}, flight_date={flight_date}")
        print(f"use_rapidapi={use_rapidapi}, latest_only={latest_only}")

    raw = get_flight_from_aerodatabox(
        flight_number,
        dep_iata=dep_iata,
        arr_iata=arr_iata,
        flight_date=flight_date,
        use_rapidapi=use_rapidapi,
    )
    
    if DEBUG_MODE:
        print(f"原始API响应: {raw}")
    
    if not raw or not raw.get("data"):
        if DEBUG_MODE:
            print("API响应为空或没有data字段")
        return None

    # 取第一条匹配项
    item = raw["data"][0]
    
    if DEBUG_MODE:
        print(f"处理第一条记录: {item}")

    dep = (item.get("departure") or {})
    arr = (item.get("arrival") or {})
    aircraft = (item.get("aircraft") or {})
    status = item.get("status") or item.get("statusText") or "Unknown"
    
    if DEBUG_MODE:
        print(f"departure对象: {dep}")
        print(f"arrival对象: {arr}")
        print(f"aircraft对象: {aircraft}")
        print(f"status: {status}")

    # 从airport对象中获取IATA代码
    dep_airport = dep.get("airport") or {}
    arr_airport = arr.get("airport") or {}
    dep_i = dep_airport.get("iata") or dep.get("iata") or (dep_iata or "Unknown")
    arr_i = arr_airport.get("iata") or arr.get("iata") or (arr_iata or "Unknown")
    # 优先顺序：scheduledLocal → scheduledUtc → estimatedLocal → actualLocal → 其他
    def pick_time(block: dict) -> Optional[str]:
        # 处理Aerodatabox的时间格式：scheduledTime是一个包含utc和local的字典
        scheduled_time = block.get("scheduledTime")
        if scheduled_time and isinstance(scheduled_time, dict):
            # 优先使用local时间，如果没有则使用utc时间
            return scheduled_time.get("local") or scheduled_time.get("utc")
        
        # 处理其他时间格式
        revised_time = block.get("revisedTime")
        if revised_time and isinstance(revised_time, dict):
            return revised_time.get("local") or revised_time.get("utc")
        
        predicted_time = block.get("predictedTime")
        if predicted_time and isinstance(predicted_time, dict):
            return predicted_time.get("local") or predicted_time.get("utc")
        
        # 兼容旧格式
        return (
            block.get("scheduledTimeLocal")
            or block.get("scheduledTimeUtc")
            or block.get("estimatedTimeLocal")
            or block.get("actualTimeLocal")
            or block.get("estimatedTimeUtc")
            or block.get("actualTimeUtc")
        )

    dep_time = pick_time(dep)
    arr_time = pick_time(arr)
    
    if DEBUG_MODE:
        print(f"提取的时间信息:")
        print(f"  dep_time: {dep_time}")
        print(f"  arr_time: {arr_time}")
        print(f"  dep_i: {dep_i}")
        print(f"  arr_i: {arr_i}")

    # 构建数据源标识
    data_source = "Aerodatabox"
    if latest_only:
        data_source += " (Latest)"
    
    result: Dict[str, str] = {
        "flight_number": flight_number,
        "schedule_city": f"{dep_i} {arr_i}",
        "schedule_timing": f"{_fmt_hhmm(dep_time)} {_fmt_hhmm(arr_time)}",
        "departure_terminal": dep.get("terminal") or "Unknown",
        "departure_gate": dep.get("gate") or "Unknown",
        "arrival_terminal": arr.get("terminal") or "Unknown",
        "arrival_gate": arr.get("gate") or "Unknown",
        "aircraft": aircraft.get("model") or aircraft.get("iata") or "Unknown",
        "status": status,
        "data_source": data_source,
        "flight_date": dep_time[:10] if dep_time and len(dep_time) >= 10 else "Unknown",
    }
    
    if DEBUG_MODE:
        print(f"\n=== 最终处理结果 ===")
        for key, value in result.items():
            print(f"  {key}: {value}")
        print("=" * 50)

    return result


def test_aerodatabox():
    """测试Aerodatabox功能"""
    global DEBUG_MODE
    DEBUG_MODE = True  # 启用调试模式
    
    test_flights = [
        {"flight_number": "TR156", "flight_date": "2025-10-05"},
        {"flight_number": "SQ876", "flight_date": "2025-10-05"},
        {"flight_number": "MU544", "flight_date": "2025-10-05"},
    ]
    
    print("测试Aerodatabox模块")
    print("=" * 50)
    
    for test in test_flights:
        print(f"\n测试航班: {test['flight_number']}")
        result = get_flight_info_aerodatabox(
            test["flight_number"],
            flight_date=test["flight_date"],
            use_rapidapi=True
        )
        
        if result:
            print("成功获取航班信息:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print("获取航班信息失败")
        print("-" * 30)

if __name__ == "__main__":
    test_aerodatabox()


