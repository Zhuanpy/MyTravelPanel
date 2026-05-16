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


def parse_format_airline_web(text, year=None):
    """解析航空公司官网/OTA网页复制格式（通用）

    支持土耳其航空、新加坡航空等网页复制格式，特征：
    - 时间+城市名在同一行: "20:05Panama City" 或 "17:05Istanbul"
    - 机场代码在括号中: "(PTY)" 或 "(IST)"
    - 航班号: "Turkish Airlines - TK900" 或 "TK900"
    - 日期: "Wednesday, April 29" 或 "Thursday, April 30"

    示例输入：
    20:05Panama City
    Tocumen International Airport (PTY)
    Turkish Airlines - TK900
    17:05Istanbul
    Wednesday, April 29
    Istanbul Airport (IST)
    """
    if year is None:
        year = datetime.now().year

    flights = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # 提取所有时间+城市行: "20:05Panama City" 或 "08:45Singapore"
    time_city_indices = []
    for i, line in enumerate(lines):
        m = re.match(r'^(\d{1,2}:\d{2})\s*(.+)', line)
        if m:
            time_city_indices.append((i, m.group(1), m.group(2).strip()))

    # 提取所有机场代码行: "... (PTY)" 或 "(IST)"
    airport_map = {}
    for i, line in enumerate(lines):
        m = re.search(r'\(([A-Z]{3})\)\s*$', line)
        if m:
            airport_map[i] = m.group(1)

    # 提取所有航班号: "TK900" 或 "Turkish Airlines - TK900"
    flight_num_map = {}
    for i, line in enumerate(lines):
        m = re.search(r'(?:^|\s|-\s*)([A-Z]{2})(\d{2,5})\b', line)
        if m:
            # 排除时间行和机场代码行的误匹配
            if not re.match(r'^\d{1,2}:\d{2}', line) and 'Airport' not in line and 'Terminal' not in line:
                flight_num_map[i] = (m.group(1), m.group(2))

    # 提取所有日期行: "Wednesday, April 29" 或 "Friday, May 1"
    date_map = {}
    for i, line in enumerate(lines):
        m = re.match(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(\w+)\s+(\d{1,2})', line)
        if m:
            try:
                dt = datetime.strptime(f'{m.group(1)} {m.group(2)} {year}', '%B %d %Y')
                date_map[i] = dt
            except ValueError:
                pass

    # 时间+城市必须成对出现（出发+到达），每对构成一个航段
    if len(time_city_indices) < 2:
        return []

    # 逐对配对
    seg_idx = 0
    while seg_idx + 1 < len(time_city_indices):
        dep_idx, dep_time, dep_city = time_city_indices[seg_idx]
        arr_idx, arr_time, arr_city = time_city_indices[seg_idx + 1]

        # 找出发机场代码（dep_idx之后最近的机场代码行）
        dep_code = None
        for j in range(dep_idx + 1, arr_idx):
            if j in airport_map:
                dep_code = airport_map[j]
                break

        # 找到达机场代码（arr_idx之后最近的机场代码行）
        arr_code = None
        next_seg_idx = time_city_indices[seg_idx + 2][0] if seg_idx + 2 < len(time_city_indices) else len(lines)
        for j in range(arr_idx + 1, next_seg_idx):
            if j in airport_map:
                arr_code = airport_map[j]
                break

        # 找航班号（在出发和到达之间，或紧接其后）
        airline = None
        number = None
        for j in range(dep_idx, min(arr_idx + 5, len(lines))):
            if j in flight_num_map:
                airline, number = flight_num_map[j]
                break

        # 找日期（在到达行附近）
        dep_dt = None
        # 先找到达时间附近的日期（通常日期在到达时间行之后）
        for j in range(arr_idx - 2, min(arr_idx + 3, len(lines))):
            if j in date_map:
                dep_dt = date_map[j]
                break
        # 再找出发时间附近的日期
        if dep_dt is None:
            for j in range(dep_idx - 2, arr_idx):
                if j in date_map:
                    dep_dt = date_map[j]
                    break

        if not airline or not dep_code or not arr_code:
            seg_idx += 1
            continue

        # 计算出发日期：到达日期行标注的是到达日期
        # 如果到达时间 < 出发时间，说明出发在前一天
        dep_time_int = int(dep_time.replace(':', ''))
        arr_time_int = int(arr_time.replace(':', ''))
        next_day = False

        if dep_dt:
            # dep_dt 可能是到达日期，如果出发时间>到达时间，出发日期=到达日期-1天
            if dep_time_int > arr_time_int:
                # 跨天：出发在前一天
                from datetime import timedelta
                dep_date_obj = dep_dt - timedelta(days=1)
                next_day = True
            else:
                dep_date_obj = dep_dt
            dep_date_str = dep_date_obj.strftime('%d%b').upper()
            dep_day = DAY_ABBR[dep_date_obj.weekday()]
        else:
            dep_date_str = '01JAN'
            dep_day = 'MO'

        flights.append({
            'airline': airline,
            'number': number,
            'dep_code': dep_code,
            'arr_code': arr_code,
            'dep_time': dep_time.replace(':', ''),
            'arr_time': arr_time.replace(':', ''),
            'dep_date': dep_date_str,
            'dep_day': dep_day,
            'next_day': next_day,
        })

        seg_idx += 2

    return flights


def parse_format_ctrip_detail(text, year=None):
    """解析携程/Trip.com航班详情页格式

    特征：
    - 航班号独立一行: "CX636"
    - 时间独立一行: "20:05"
    - 机场行以IATA代码开头: "SIN Singapore ChangiT4"
    - 日期行: "Apr 20"
    - 航空公司名称行: "Cathay Pacific"

    示例：
    20:05
    SIN Singapore ChangiT4
    Cathay Pacific
    CX636
    ...
    Apr 20
    00:10
    HKG Hong Kong Intl.T1
    """
    if year is None:
        year = datetime.now().year

    flights = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # 找所有航班号行（独立一行，格式: CX636 / TK900 / SQ321）
    fn_indices = []
    for i, line in enumerate(lines):
        if re.match(r'^([A-Z\d]{2})(\d{2,5})$', line):
            fn_indices.append(i)

    if not fn_indices:
        return []

    # 预扫描：从头部查找行程日期（如 "...Fri, Apr 17Duration 23h 25m"）
    header_date = None
    for line in lines:
        dm = re.search(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+(\w{3})\s+(\d{1,2})', line)
        if dm:
            try:
                header_date = datetime.strptime(f'{dm.group(1)} {dm.group(2)} {year}', '%b %d %Y')
                break
            except ValueError:
                pass

    for fn_idx in fn_indices:
        m = re.match(r'^([A-Z\d]{2})(\d{2,5})$', lines[fn_idx])
        airline = m.group(1)
        number = m.group(2)

        # 向上查找出发时间和出发机场（在航班号行之前）
        dep_time = None
        dep_code = None
        for j in range(fn_idx - 1, max(fn_idx - 8, -1), -1):
            line = lines[j]
            # 机场行: "SIN Singapore ChangiT4" — 以IATA代码开头
            if dep_code is None:
                am = re.match(r'^([A-Z]{3})\s+\S', line)
                if am:
                    dep_code = am.group(1)
                    continue
            # 时间行: "20:05"
            if dep_time is None:
                tm = re.match(r'^(\d{2}:\d{2})$', line)
                if tm:
                    dep_time = tm.group(1)
                    break

        # 向下查找到达日期、时间和机场（在航班号行之后）
        arr_time = None
        arr_code = None
        arr_date_str = None
        for j in range(fn_idx + 1, min(fn_idx + 10, len(lines))):
            line = lines[j]
            # 遇到下一个航班号就停止
            if re.match(r'^[A-Z\d]{2}\d{2,5}$', line):
                break
            # 日期行: "Apr 20"
            if arr_date_str is None:
                dm = re.match(r'^(\w{3})\s+(\d{1,2})$', line)
                if dm:
                    try:
                        datetime.strptime(f'{dm.group(1)} {dm.group(2)}', '%b %d')
                        arr_date_str = f'{dm.group(1)} {dm.group(2)}'
                    except ValueError:
                        pass
                    continue
            # 时间行: "00:10"（可能在日期行之后，也可能没有日期行）
            if arr_time is None:
                tm = re.match(r'^(\d{2}:\d{2})$', line)
                if tm:
                    arr_time = tm.group(1)
                    continue
            # 机场行: "HKG Hong Kong Intl.T1"
            if arr_time and arr_code is None:
                am = re.match(r'^([A-Z]{3})\s+\S', line)
                if am:
                    arr_code = am.group(1)
                    break

        if not dep_time or not dep_code or not arr_time or not arr_code:
            continue

        # 出发日期：从行首 "Sun, Apr 19" 或从到达日期推算
        dep_dt = None
        arr_dt = None

        if arr_date_str:
            arr_dt = datetime.strptime(f'{arr_date_str} {year}', '%b %d %Y')

        # 向上查找出发日期: "...Fri, Apr 17Duration..." 或 "Apr 19"
        for j in range(fn_idx - 1, -1, -1):
            line = lines[j]
            dm = re.search(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+(\w{3})\s+(\d{1,2})', line)
            if dm:
                try:
                    dep_dt = datetime.strptime(f'{dm.group(1)} {dm.group(2)} {year}', '%b %d %Y')
                    break
                except ValueError:
                    pass

        # 使用头部日期作为兜底
        if dep_dt is None and header_date:
            dep_dt = header_date

        # 如果没有找到出发日期，用到达日期推算
        if dep_dt is None and arr_dt:
            dep_time_int = int(dep_time.replace(':', ''))
            arr_time_int = int(arr_time.replace(':', ''))
            if dep_time_int > arr_time_int:
                from datetime import timedelta
                dep_dt = arr_dt - timedelta(days=1)
            else:
                dep_dt = arr_dt

        if dep_dt is None:
            continue

        if arr_dt:
            next_day = arr_dt.date() > dep_dt.date()
        else:
            # 没有到达日期时，简单判断：到达时间 < 出发时间视为跨天
            dep_time_int = int(dep_time.replace(':', ''))
            arr_time_int = int(arr_time.replace(':', ''))
            next_day = arr_time_int < dep_time_int

        flights.append({
            'airline': airline,
            'number': number,
            'dep_code': dep_code,
            'arr_code': arr_code,
            'dep_time': dep_time.replace(':', ''),
            'arr_time': arr_time.replace(':', ''),
            'dep_date': dep_dt.strftime('%d%b').upper(),
            'dep_day': DAY_ABBR[dep_dt.weekday()],
            'next_day': next_day,
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
        # 英文: Flight No: BS 310 或 Flight No: BS310 或 Flight No: 6E1002
        # 中文: 航班号：GJ6030 或 航班号: GJ 6030
        # 航空公司代码支持字母+数字组合（如 6E、3K、9W）
        fn_m = re.search(
            r'(?:Flight\s*No[:：]?\s*|航班号[:：]?\s*)([A-Z\d]{2})\s*(\d{2,5})',
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
        # 英文: Departure: 15:25 - Arrival: 17:35 或 Arrival: #06:00（#表示次日到达）
        # 中文: 出发：15:00 - 抵达：20:05
        time_m = re.search(
            r'(?:Departure|出发)[:：]?\s*(\d{1,2}:\d{2})\s*[-–—]\s*(?:Arrival|抵达|到达)[:：]?\s*(#?)(\d{1,2}:\d{2})',
            rest, re.IGNORECASE
        )
        if not time_m:
            continue
        dep_time = time_m.group(1).replace(":", "")
        arr_next_day_mark = time_m.group(2)  # '#' 表示次日到达
        arr_time = time_m.group(3).replace(":", "")

        # 判断是否跨天：有#标记 或 到达时间小于出发时间
        next_day = bool(arr_next_day_mark) or int(arr_time) < int(dep_time)

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


def parse_format_sq_itinerary(text, year=None):
    """解析新加坡航空 / Google 风格"展开详情"行程（支持转机多航段）

    特征（每一程 leg，在 "More details" … "Less details" 详情区内）：
        SIN 01:20            <- 出发：IATA + 时间
        Singapore            <- 城市
        31 Jul (Fri)         <- 日期 DD Mon (Day)
        Changi               <- 机场名
        Terminal 2           <- 航站楼（可选）
        FUK 08:20            <- 到达：IATA + 时间
        Fukuoka
        31 Jul (Fri)
        Fukuoka Intl
        Terminal Intl
        Singapore Airlines airline logo, flight detail   <- 可有可无
        Singapore Airlines
        •
        SQ 656               <- 航班号（承运/市场号，取此行）
        Boeing 787-10        <- 机型
        Economy              <- 舱位

    转机：详情区里连续多段 leg 依次出现，每段独立成航段。
    "Operated by XXX" 代码共享时仍取 • 后那行的航班号（市场号）。
    """
    if year is None:
        year = datetime.now().year

    # 只解析"展开详情"区，避开摘要区（摘要区航班号是合并列出的，且只有总O/D）
    detail_blocks = re.findall(r'More details(.*?)Less details', text, re.DOTALL)
    if not detail_blocks:
        return []

    anchor_re = re.compile(r'^([A-Z]{3})\s+(\d{1,2}:\d{2})$')
    date_re = re.compile(r'^(\d{1,2})\s+([A-Za-z]{3,9})\s+\([A-Za-z]{2,9}\)$')
    code_re = re.compile(r'^([A-Z0-9]{2})\s*(\d{1,4})$')

    flights = []

    for block in detail_blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]

        # 收集 IATA+时间 锚点（详情区里依次为 leg1出发, leg1到达, leg2出发, ...）
        anchors = [(i, m.group(1), m.group(2))
                   for i, l in enumerate(lines)
                   for m in [anchor_re.match(l)] if m]

        # 成对配对：(出发, 到达)
        k = 0
        while k + 1 < len(anchors):
            dep_i, dep_code, dep_t = anchors[k]
            arr_i, arr_code, arr_t = anchors[k + 1]
            # 下一段出发锚点的位置，作为本段搜索航班号的右边界
            next_dep_i = anchors[k + 2][0] if k + 2 < len(anchors) else len(lines)

            def _find_date(start, end):
                for j in range(start, min(end, len(lines))):
                    dm = date_re.match(lines[j])
                    if dm:
                        try:
                            return datetime.strptime(
                                f"{dm.group(1)} {dm.group(2)[:3]} {year}", "%d %b %Y")
                        except ValueError:
                            return None
                return None

            dep_dt = _find_date(dep_i + 1, arr_i)
            arr_dt = _find_date(arr_i + 1, next_dep_i)

            # 航班号：到达块之后第一个 "•" 行的下一行
            airline = number = None
            for j in range(arr_i + 1, min(next_dep_i, len(lines))):
                if lines[j] == '•' or lines[j].startswith('•'):
                    if j + 1 < len(lines):
                        cm = code_re.match(lines[j + 1].strip())
                        if cm:
                            airline, number = cm.group(1), cm.group(2)
                    break

            if not (airline and number and dep_dt):
                k += 2
                continue

            next_day = bool(arr_dt and arr_dt.date() > dep_dt.date())

            flights.append({
                "airline": airline,
                "number": number,
                "dep_code": dep_code,
                "arr_code": arr_code,
                "dep_time": dep_t.replace(":", "").zfill(4),
                "arr_time": arr_t.replace(":", "").zfill(4),
                "dep_date": dep_dt.strftime("%d%b").upper(),
                "dep_day": DAY_ABBR[dep_dt.weekday()],
                "next_day": next_day,
            })
            k += 2

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
        (parse_format_sq_itinerary, "新加坡航空/转机详情"),
        (parse_format_trip, "Trip.com"),
        (parse_format_ctrip, "Ctrip/携程"),
        (parse_format_ctrip_order, "Ctrip/携程(订单)"),
        (parse_format_ctrip_detail, "Ctrip/携程(详情)"),
        (parse_format_scoot, "Scoot/酷航"),
        (parse_format_airline_web, "航空公司官网"),
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
