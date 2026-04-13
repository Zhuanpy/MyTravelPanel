"""
航班信息解析工具

支持解析以下格式的航班信息：
- Trip.com / Ctrip 网页复制格式
- 携程 (Ctrip) 网页复制格式
- Google Flights 网页复制格式
- Scoot 酷航网页复制格式
- 手动输入格式（中英文）
"""
import re
from datetime import datetime

DAY_ABBR = {0: "MO", 1: "TU", 2: "WE", 3: "TH", 4: "FR", 5: "SA", 6: "SU"}


def parse_format_trip(text):
    """解析 Trip.com 格式"""
    flights = []
    flight_blocks = re.split(
        r"Leg \d+ flight with [^.]+\. Flight number ", text
    )
    for block in flight_blocks[1:]:
        flight = {}
        m = re.match(r"([A-Z\d]{2})(\d+)", block)
        if not m:
            continue
        flight["airline"] = m.group(1)
        flight["number"] = m.group(2)

        m = re.search(
            r"Departing from ([^,]+),\s*(\d{2}:\d{2}),\s*(\d{1,2} \w+ \d{4})", block
        )
        if not m:
            continue
        flight["dep_airport_name"] = m.group(1).strip()
        flight["dep_time"] = m.group(2).replace(":", "")
        dep_date = datetime.strptime(m.group(3), "%d %B %Y")
        flight["dep_date"] = dep_date.strftime("%d%b").upper()
        flight["dep_day"] = DAY_ABBR[dep_date.weekday()]

        m = re.search(
            r"Arriving at ([^,]+),\s*(\d{2}:\d{2}),\s*(\d{1,2} \w+ \d{4})", block
        )
        if not m:
            continue
        flight["arr_time"] = m.group(2).replace(":", "")
        arr_date = datetime.strptime(m.group(3), "%d %B %Y")
        flight["next_day"] = arr_date.date() > dep_date.date()

        dep_code = re.search(
            r"\b([A-Z]{3})\s+" + re.escape(flight["dep_airport_name"]), block
        )
        arr_code = re.search(
            r"\b([A-Z]{3})\s+" + re.escape(m.group(1).strip()), block
        )
        flight["dep_code"] = dep_code.group(1) if dep_code else "???"
        flight["arr_code"] = arr_code.group(1) if arr_code else "???"
        flights.append(flight)
    return flights


def parse_format_ctrip(text, year=None):
    """解析携程网页复制格式"""
    if year is None:
        year = datetime.now().year

    flights = []
    header = re.match(
        r"[^()\n]*\(([A-Z]{3})\)[^()\n]*\(([A-Z]{3})\)\w{3},\s*(\w{3} \d{1,2})",
        text,
    )
    if not header:
        return []

    base_date = datetime.strptime(f"{header.group(3)} {year}", "%b %d %Y")

    for fn_match in re.finditer(r"\n([A-Z\d]{2})(\d{2,5})\n", text):
        airline = fn_match.group(1)
        number = fn_match.group(2)

        before = text[: fn_match.start()]
        after = text[fn_match.end():]

        dep_matches = list(
            re.finditer(
                r"(?:(\w{3} \d{1,2})\n)?(\d{2}:\d{2})\n([A-Z]{3})\s", before
            )
        )
        if not dep_matches:
            continue
        dep_m = dep_matches[-1]
        dep_time = dep_m.group(2)
        dep_code = dep_m.group(3)
        dep_date = (
            datetime.strptime(f"{dep_m.group(1)} {year}", "%b %d %Y")
            if dep_m.group(1)
            else base_date
        )

        arr_m = re.search(
            r"(?:(\w{3} \d{1,2})\n)?(\d{2}:\d{2})\n([A-Z]{3})\s", after
        )
        if not arr_m:
            continue
        arr_time = arr_m.group(2)
        arr_code = arr_m.group(3)
        arr_date = (
            datetime.strptime(f"{arr_m.group(1)} {year}", "%b %d %Y")
            if arr_m.group(1)
            else dep_date
        )

        flights.append({
            "airline": airline,
            "number": number,
            "dep_code": dep_code,
            "arr_code": arr_code,
            "dep_time": dep_time.replace(":", ""),
            "arr_time": arr_time.replace(":", ""),
            "dep_date": dep_date.strftime("%d%b").upper(),
            "dep_day": DAY_ABBR[dep_date.weekday()],
            "next_day": arr_date.date() > dep_date.date(),
        })

    return flights


def parse_format_ctrip_order(text, year=None):
    """解析携程已完成订单复制格式

    示例格式：
    1
    Wed, Apr 8
    Chongqing - Shenzhen
    17:25
    CKGChongqing Jiangbei Intl. T3
    2h 10m
    19:35
    SZXShenzhen Bao'an Intl. T3
    airline logoChina Southern AirlinesCZ2345On schedule
    Economy classAirbus A320-212 (Mid-sized)Meal
    """
    if year is None:
        year = datetime.now().year

    flights = []

    # 按空行分段，每段是一个航段
    segments = re.split(r"\n\s*\n", text.strip())

    for seg in segments:
        lines = [l.strip() for l in seg.strip().split("\n") if l.strip()]

        # 查找日期行: "Wed, Apr 8" 或 "Fri, Apr 10"
        date_line = None
        date_idx = -1
        for i, line in enumerate(lines):
            m = re.match(
                r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+(\w{3})\s+(\d{1,2})", line
            )
            if m:
                date_line = m
                date_idx = i
                break
        if not date_line:
            continue

        dep_date = datetime.strptime(
            f"{date_line.group(1)} {date_line.group(2)} {year}", "%b %d %Y"
        )

        # 日期行之后依次查找：出发时间、出发机场、飞行时长、到达时间、到达机场
        after_date = lines[date_idx + 1:]  # 跳过日期行后面的内容

        # 跳过城市路线行（如 "Chongqing - Shenzhen"）
        start = 0
        if after_date and re.match(r".+\s*-\s*.+", after_date[0]) and not re.match(r"\d{2}:\d{2}", after_date[0]):
            start = 1

        remaining = after_date[start:]
        if len(remaining) < 5:
            continue

        # 提取出发时间
        dep_time_m = re.match(r"(\d{2}:\d{2})", remaining[0])
        if not dep_time_m:
            continue
        dep_time = dep_time_m.group(1)

        # 提取出发机场代码：行首3个大写字母
        dep_code_m = re.match(r"([A-Z]{3})", remaining[1])
        if not dep_code_m:
            continue
        dep_code = dep_code_m.group(1)

        # 跳过飞行时长行（如 "2h 10m"），找到到达时间
        arr_idx = None
        for j in range(2, len(remaining)):
            if re.match(r"(\d{2}:\d{2})", remaining[j]):
                arr_idx = j
                break
        if arr_idx is None or arr_idx + 1 >= len(remaining):
            continue

        arr_time_m = re.match(r"(\d{2}:\d{2})", remaining[arr_idx])
        arr_time = arr_time_m.group(1)

        # 提取到达机场代码
        arr_code_m = re.match(r"([A-Z]{3})", remaining[arr_idx + 1])
        if not arr_code_m:
            continue
        arr_code = arr_code_m.group(1)

        # 提取航班号：在 airline logo 行中查找，格式如 "...CZ2345On schedule"
        airline = None
        number = None
        for line in remaining:
            fn_m = re.search(r"([A-Z\d]{2})(\d{3,5})(?:On schedule|Delayed|Cancelled|Arrived|$)", line)
            if fn_m:
                airline = fn_m.group(1)
                number = fn_m.group(2)
                break

        if not airline or not number:
            continue

        # 判断是否跨天：到达时间 < 出发时间视为跨天
        next_day = arr_time.replace(":", "") < dep_time.replace(":", "")

        flights.append({
            "airline": airline,
            "number": number,
            "dep_code": dep_code,
            "arr_code": arr_code,
            "dep_time": dep_time.replace(":", ""),
            "arr_time": arr_time.replace(":", ""),
            "dep_date": dep_date.strftime("%d%b").upper(),
            "dep_day": DAY_ABBR[dep_date.weekday()],
            "next_day": next_day,
        })

    return flights


def parse_format_google(text, year=None):
    """解析 Google Flights 格式"""
    if year is None:
        year = datetime.now().year

    flights = []
    segments = re.split(
        r"(?=\w[^()\n]*\([A-Z]{3}\)\w[^()\n]*\([A-Z]{3}\)\w{3},\s*\w+ \d{1,2})",
        text,
    )

    for seg in segments:
        header = re.match(
            r"[^()\n]*\(([A-Z]{3})\)[^()\n]*\(([A-Z]{3})\)(\w{3}),\s*(\w+ \d{1,2})",
            seg,
        )
        if not header:
            continue

        dep_code = header.group(1)
        arr_code = header.group(2)
        date_str = header.group(4)
        dep_date = datetime.strptime(f"{date_str} {year}", "%b %d %Y")

        rest = seg[header.end():]
        dep_m = re.search(r"(\d{2}:\d{2})", rest)
        if not dep_m:
            continue
        dep_time = dep_m.group(1).replace(":", "")

        fn_m = re.search(r"\n([A-Z]{2})(\d{2,5})\s*\n", rest)
        if not fn_m:
            continue
        airline = fn_m.group(1)
        number = fn_m.group(2)

        after_fn = rest[fn_m.end():]
        next_day = False
        arr_next = re.search(r"(\w+ \d{1,2})\n(\d{2}:\d{2})\n", after_fn)
        arr_same = re.search(r"(\d{2}:\d{2})\n", after_fn)

        if arr_next:
            arr_time = arr_next.group(2).replace(":", "")
            try:
                arr_date = datetime.strptime(f"{arr_next.group(1)} {year}", "%B %d %Y")
                next_day = arr_date.date() > dep_date.date()
            except ValueError:
                pass
        elif arr_same:
            arr_time = arr_same.group(1).replace(":", "")
        else:
            continue

        flights.append({
            "airline": airline,
            "number": number,
            "dep_code": dep_code,
            "arr_code": arr_code,
            "dep_time": dep_time,
            "arr_time": arr_time,
            "dep_date": dep_date.strftime("%d%b").upper(),
            "dep_day": DAY_ABBR[dep_date.weekday()],
            "next_day": next_day,
        })

    return flights


def parse_format_scoot(text, year=None):
    """解析酷航 Scoot 网页格式"""
    if year is None:
        year = datetime.now().year

    flights = []
    segments = re.split(r"(?=\d+\.\s+(?:Depart|Return)\s+-\s+)", text)

    for seg in segments:
        header = re.match(
            r"\d+\.\s+(?:Depart|Return)\s+-\s+([A-Z]{3})\s+to\s+([A-Z]{3})", seg
        )
        if not header:
            continue

        dep_code = header.group(1)
        arr_code = header.group(2)

        fn_m = re.search(r"Scoot\n([A-Z]{2})(\d{2,5})", seg)
        if not fn_m:
            continue
        airline = fn_m.group(1)
        number = fn_m.group(2)

        times = re.findall(r"^(\d{2}:\d{2})$", seg, re.MULTILINE)
        if len(times) < 2:
            continue
        dep_time = times[0].replace(":", "")
        arr_time = times[1].replace(":", "")

        dates = re.findall(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+(\d{1,2}\s+\w{3})", seg)
        if not dates:
            continue
        dep_date = datetime.strptime(f"{dates[0]} {year}", "%d %b %Y")
        arr_date = (
            datetime.strptime(f"{dates[1]} {year}", "%d %b %Y")
            if len(dates) > 1
            else dep_date
        )

        flights.append({
            "airline": airline,
            "number": number,
            "dep_code": dep_code,
            "arr_code": arr_code,
            "dep_time": dep_time,
            "arr_time": arr_time,
            "dep_date": dep_date.strftime("%d%b").upper(),
            "dep_day": DAY_ABBR[dep_date.weekday()],
            "next_day": arr_date.date() > dep_date.date(),
        })

    return flights


# 中文月份映射
_CN_MONTH_MAP = {
    '01': 'JAN', '02': 'FEB', '03': 'MAR', '04': 'APR',
    '05': 'MAY', '06': 'JUN', '07': 'JUL', '08': 'AUG',
    '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC',
    '1': 'JAN', '2': 'FEB', '3': 'MAR', '4': 'APR',
    '5': 'MAY', '6': 'JUN', '7': 'JUL', '8': 'AUG',
    '9': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC',
}

# 英文月份缩写映射
_EN_MONTH_MAP = {
    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
}


def _parse_manual_date(date_str, year=None):
    """解析手动输入的日期字符串，返回 (dep_date_str, dep_day)

    支持格式：
    - 22APR / 22Apr
    - 05月29号 / 5月29日
    - 2026-05-29 / 2026/05/29
    """
    if year is None:
        year = datetime.now().year

    date_str = date_str.strip()

    # 格式：22APR 或 22Apr
    m = re.match(r'(\d{1,2})\s*([A-Za-z]{3})', date_str)
    if m:
        day = int(m.group(1))
        month_abbr = m.group(2).upper()
        if month_abbr in _EN_MONTH_MAP:
            dt = datetime(year, _EN_MONTH_MAP[month_abbr], day)
            return dt.strftime("%d%b").upper(), DAY_ABBR[dt.weekday()], dt

    # 格式：05月29号 / 5月29日
    m = re.match(r'(\d{1,2})月(\d{1,2})[号日]?', date_str)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        dt = datetime(year, month, day)
        return dt.strftime("%d%b").upper(), DAY_ABBR[dt.weekday()], dt

    # 格式：2026-05-29 / 2026/05/29
    m = re.match(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', date_str)
    if m:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return dt.strftime("%d%b").upper(), DAY_ABBR[dt.weekday()], dt

    return None, None, None


def parse_format_manual(text, year=None):
    """解析手动输入格式（中英文）

    支持格式：
    英文: 1.SINGAPORE - DHAKA, Flight No: BS 310, 22APR, Departure: 15:25 - Arrival: 17:35
    中文: 1.新加坡（樟宜机场） - 温州永强机场, 航班号：GJ6030，05月29号，出发：15:00 - 抵达：20:05

    返回的航班数据中 dep_code/arr_code 存储城市/机场名称（而非IATA代码），
    需要调用方通过 resolve_airport_codes() 解析为IATA代码。
    """
    if year is None:
        year = datetime.now().year

    flights = []
    # 将文本按航段拆分（每段以 数字. 开头）
    # 先合并换行（有些格式跨两行）
    text = re.sub(r'\n\s+', ' ', text.strip())
    segments = re.split(r'(?=\d+\s*[.、])', text.strip())

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        # 去掉开头的序号
        seg = re.sub(r'^\d+\s*[.、]\s*', '', seg)

        # 提取出发地 - 目的地
        # 英文: SINGAPORE - DHAKA, ...
        # 中文: 新加坡（樟宜机场） - 温州永强机场, ...
        route_m = re.match(r'(.+?)\s*[-–—]\s*(.+?)\s*[,，]', seg)
        if not route_m:
            continue
        dep_name = route_m.group(1).strip()
        arr_name = route_m.group(2).strip()

        rest = seg[route_m.end():]

        # 提取航班号
        # 英文: Flight No: BS 310 或 Flight No: BS310
        # 中文: 航班号：GJ6030 或 航班号: GJ 6030
        fn_m = re.search(
            r'(?:Flight\s*No[:：]?\s*|航班号[:：]?\s*)([A-Z]{2})\s*(\d{2,5})',
            rest, re.IGNORECASE
        )
        if not fn_m:
            continue
        airline = fn_m.group(1).upper()
        number = fn_m.group(2)

        # 提取日期
        # 英文: 22APR
        # 中文: 05月29号 / 05月29日
        date_m = re.search(
            r'(\d{1,2}\s*[A-Za-z]{3}|\d{1,2}月\d{1,2}[号日]?|\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            rest
        )
        if not date_m:
            continue
        dep_date_str, dep_day, dep_dt = _parse_manual_date(date_m.group(1), year)
        if not dep_date_str:
            continue

        # 提取出发时间和到达时间
        # 英文: Departure: 15:25 - Arrival: 17:35
        # 中文: 出发：15:00 - 抵达：20:05
        time_m = re.search(
            r'(?:Departure|出发)[:：]?\s*(\d{1,2}:\d{2})\s*[-–—]\s*(?:Arrival|抵达|到达)[:：]?\s*(\d{1,2}:\d{2})',
            rest, re.IGNORECASE
        )
        if not time_m:
            continue
        dep_time = time_m.group(1).replace(":", "")
        arr_time = time_m.group(2).replace(":", "")

        # 判断是否跨天（到达时间小于出发时间）
        next_day = int(arr_time) < int(dep_time)

        flights.append({
            "airline": airline,
            "number": number,
            "dep_code": dep_name,  # 暂存城市/机场名称
            "arr_code": arr_name,  # 暂存城市/机场名称
            "dep_time": dep_time,
            "arr_time": arr_time,
            "dep_date": dep_date_str,
            "dep_day": dep_day,
            "next_day": next_day,
            "_needs_iata_lookup": True,  # 标记需要IATA代码查找
        })

    return flights


def resolve_airport_codes(flights, lookup_fn):
    """将航班中的城市/机场名称解析为IATA代码

    Args:
        flights: 航班列表
        lookup_fn: 查找函数，接受城市/机场名称，返回IATA代码或None
    """
    for f in flights:
        if not f.get('_needs_iata_lookup'):
            continue
        # 保存原始名称用于提示未识别的机场
        f['_original_dep'] = f['dep_code']
        f['_original_arr'] = f['arr_code']
        dep_code = lookup_fn(f['dep_code'])
        arr_code = lookup_fn(f['arr_code'])
        f['dep_code'] = dep_code or '???'
        f['arr_code'] = arr_code or '???'
        f.pop('_needs_iata_lookup', None)
    return flights


def format_segments(flights):
    """格式化为航段信息（Athina格式）"""
    lines = []
    for i, f in enumerate(flights, 1):
        num = f["number"]
        if len(num) <= 3:
            fn = f"{f['airline']}  {num:>3}"
        else:
            fn = f"{f['airline']} {num:>4}"

        arr_prefix = "#" if f["next_day"] else " "
        arr_time = f"{arr_prefix}{f['arr_time']}"

        line = (
            f"{i}. {fn} Y  {f['dep_date']} "
            f"{f['dep_code']}{f['arr_code']} HK1  "
            f"{f['dep_time']}  {arr_time}  O        E {f['dep_day']}"
        )
        lines.append(line)
    return "\n".join(lines)


def parse_flights(text):
    """
    解析航班信息文本，返回结构化数据和格式化输出

    Returns:
        dict: {
            'success': bool,
            'flights': list,         # 结构化航班数据
            'segments': str,         # 航段信息文本（Athina格式）
            'format_detected': str   # 检测到的格式
        }
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 依次尝试各种格式（手动格式放最后，因为匹配比较宽松）
    for parser, name in [
        (parse_format_trip, "Trip.com"),
        (parse_format_ctrip, "Ctrip/携程"),
        (parse_format_ctrip_order, "Ctrip/携程(订单)"),
        (parse_format_scoot, "Scoot/酷航"),
        (parse_format_google, "Google Flights"),
        (parse_format_manual, "手动输入"),
    ]:
        flights = parser(text)
        if flights:
            segments = format_segments(flights)
            return {
                'success': True,
                'flights': flights,
                'segments': segments,
                'format_detected': name
            }

    return {
        'success': False,
        'flights': [],
        'segments': '',
        'format_detected': None
    }
