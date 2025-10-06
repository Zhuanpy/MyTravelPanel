# -*- coding: utf-8 -*-
"""
PVG 上海浦东机场官网抓取器（轻量版）

目标：根据航班号与日期，从官方出发/到达页提取 Terminal/Gate（若官网提供）。
官网结构、域名可能会变化，故实现以容错正则为主。
"""

import re
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup


# 机场集团可能的查询入口（示意，实际项目中需按线上可用页面更新）：
CANDIDATE_URLS = [
    # 到达/出发查询示例入口（需按实际线上可用路径调整）
    "https://www.shairport.com/mt_cn/flights?keywords={flight}",
    "https://www.shairport.com/portal/flight?kw={flight}",
]


def fetch_terminal_gate(flight_number: str, flight_date: Optional[str] = None, direction_hint: Optional[str] = None) -> Optional[Dict]:
    try:
        flight = flight_number.strip().upper()
        if not flight:
            return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        for tpl in CANDIDATE_URLS:
            url = tpl.format(flight=flight)
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(" ", strip=True)

            # 常见中文标注：航站楼 1/2/3/..., 登机口 A/B/C + 数字
            terminal = None
            gate = None

            terminal_match = re.search(r"航站楼\s*([A-Z0-9]+)|Terminal\s*([A-Z0-9]+)|\bT(\d+)\b", text, re.IGNORECASE)
            if terminal_match:
                terminal = terminal_match.group(1) or terminal_match.group(2) or terminal_match.group(3)

            gate_match = re.search(r"登机口\s*([A-Z0-9]+)|Gate\s*([A-Z0-9]+)|\bG(\d+)\b", text, re.IGNORECASE)
            if gate_match:
                gate = gate_match.group(1) or gate_match.group(2) or gate_match.group(3)

            if terminal or gate:
                # 无法稳定判断方向时，仅返回可用字段，统一由上层合并
                data: Dict[str, str] = {}
                if direction_hint == "departures":
                    data["departure_terminal"] = terminal or "Unknown"
                    data["departure_gate"] = gate or "Unknown"
                elif direction_hint == "arrivals":
                    data["arrival_terminal"] = terminal or "Unknown"
                    data["arrival_gate"] = gate or "Unknown"
                else:
                    # 未给方向时，先返回通用键位，由上层结合 dep/arr 语义合并
                    data["terminal"] = terminal or "Unknown"
                    data["gate"] = gate or "Unknown"
                return data

        return None
    except Exception:
        return None


