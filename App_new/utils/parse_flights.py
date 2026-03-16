"""
航班信息解析工具

支持解析以下格式的航班信息：
- Trip.com / Ctrip 网页复制格式
- 携程 (Ctrip) 网页复制格式
- Google Flights 网页复制格式
- Scoot 酷航网页复制格式
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

    # 依次尝试各种格式
    for parser, name in [
        (parse_format_trip, "Trip.com"),
        (parse_format_ctrip, "Ctrip/携程"),
        (parse_format_scoot, "Scoot/酷航"),
        (parse_format_google, "Google Flights"),
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
