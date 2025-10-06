"""
机场官网抓取器集合

包含针对部分机场（如 SIN 樟宜、PVG 浦东）的官方页面抓取逻辑。
各抓取器需暴露统一函数签名：

    fetch_terminal_gate(flight_number: str, flight_date: Optional[str], direction_hint: Optional[str]) -> Optional[Dict]

返回示例：
{
    'departure_terminal': '3',
    'departure_gate': 'A2',
    'arrival_terminal': '2',
    'arrival_gate': 'D6'
}

未能获取时返回 None。
"""


