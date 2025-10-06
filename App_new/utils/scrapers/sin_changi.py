# -*- coding: utf-8 -*-
"""
SIN 樟宜机场官网抓取器（轻量版）

目标：根据航班号与日期，从官方出发/到达页提取 Terminal/Gate。
说明：官网结构可能调整，本实现尽量使用稳健选择器并容错。
"""

import re
import json
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.changiairport.com/cag-web/flights/{direction}?searchType=byFlightNo&searchText={flight}&date={date}"
# direction: arrivals / departures


def fetch_terminal_gate(flight_number: str, flight_date: Optional[str] = None, direction_hint: Optional[str] = None) -> Optional[Dict]:
    try:
        flight = flight_number.strip().upper()
        if not flight:
            return None

        # 默认尝试 departures 后 arrivals
        directions = ["departures", "arrivals"]
        if direction_hint in ("departures", "arrivals"):
            directions = [direction_hint] + [d for d in directions if d != direction_hint]

        # 默认日期为今天（由官网端处理），若提供则拼接
        date_param = flight_date or ""

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        for direction in directions:
            url = BASE_URL.format(direction=direction, flight=flight, date=date_param)
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # 页面通常有嵌入的 JSON 数据或直接 DOM 列表
            # 1) 尝试从 data-flight 属性或脚本中找结构化数据
            text = soup.get_text(" ", strip=True)

            # 2) 直接在 DOM 中找 Terminal / Gate 关键词
            terminal = None
            gate = None

            # 常见标注: Terminal 3 / T3
            terminal_match = re.search(r"Terminal\s*([A-Z0-9]+)|\bT(\d+)\b", text, re.IGNORECASE)
            if terminal_match:
                terminal = terminal_match.group(1) or terminal_match.group(2)

            gate_match = re.search(r"Gate\s*([A-Z0-9]+)|\bG(\d+)\b", text, re.IGNORECASE)
            if gate_match:
                gate = gate_match.group(1) or gate_match.group(2)

            if terminal or gate:
                if direction == "departures":
                    return {
                        "departure_terminal": terminal or "Unknown",
                        "departure_gate": gate or "Unknown",
                    }
                else:
                    return {
                        "arrival_terminal": terminal or "Unknown",
                        "arrival_gate": gate or "Unknown",
                    }

        return None
    except Exception:
        return None


