"""
OCR航班图片解析模块

通过 Tesseract OCR 从机票截图中提取航班信息，
解析后返回结构化数据用于自动填充订单表单。

目前支持的航司/平台:
- US Bangla Airlines (Amadeus出票界面)
- IndiGo Airlines (IndiGo官网确认页截图)

后续可按需添加新的解析器（每个平台一个 parse_ 函数）。
"""

import re
import base64
import io
from datetime import datetime

import pytesseract
from PIL import Image

# Tesseract安装路径（Windows/Linux自动适配）
import platform
import shutil
if platform.system() == 'Windows':
    _tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if not shutil.which('tesseract') and __import__('os').path.exists(_tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = _tesseract_path

# 月份缩写映射
MONTH_MAP = {
    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12',
}


def image_from_base64(data_url: str) -> Image.Image:
    """从base64 data URL解码为PIL Image"""
    if ',' in data_url:
        data_url = data_url.split(',', 1)[1]
    img_bytes = base64.b64decode(data_url)
    return Image.open(io.BytesIO(img_bytes))


def preprocess_image(img: Image.Image) -> Image.Image:
    """预处理图片以提高OCR识别率"""
    # 转灰度
    img = img.convert('L')
    # 放大2倍提高小字识别率
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    # 二值化：阈值180
    img = img.point(lambda x: 0 if x < 180 else 255, '1')
    return img


def ocr_image(img: Image.Image) -> str:
    """对图片执行OCR，返回识别文本（先预处理再识别）"""
    processed = preprocess_image(img)
    return pytesseract.image_to_string(processed)


def _parse_date_str(date_str: str, year: int = None) -> str:
    """将 '22Apr' 格式转为 '2026-04-22' ISO格式"""
    if year is None:
        year = datetime.now().year
    m = re.match(r'(\d{1,2})\s*([A-Za-z]{3})', date_str.strip())
    if not m:
        return ''
    day = int(m.group(1))
    month_str = m.group(2).capitalize()
    month = MONTH_MAP.get(month_str)
    if not month:
        return ''
    return f'{year}-{month}-{day:02d}'


def _clean_amount(amount_str: str) -> str:
    """清理金额字符串: '27,895' → '27895', '273.62' → '273.62'"""
    if not amount_str:
        return '0'
    return amount_str.replace(',', '').strip()


def parse_usbangla(text: str) -> dict:
    """解析 US Bangla Airlines 机票截图的OCR文本

    返回结构化数据，字段直接对应订单表单。
    """
    result = {
        'platform': 'US Bangla',
        'segments': [],
        'passengers': [],
        'pnr': '',
        'remarks': '',
    }

    # === PNR (顶部6位字母数字) ===
    pnr_match = re.search(r'\b([A-Z0-9]{6})\b', text)
    if pnr_match:
        result['pnr'] = pnr_match.group(1)

    # === 航线 + 航班号 + 日期 + 机型 ===
    # 格式: SIN - DAC  BS310  22Apr  Boeing 737-800 ( S2-AJF)
    flight_match = re.search(
        r'([A-Z]{3})\s*[-–]\s*([A-Z]{3})\s+([A-Z]{2}\s*\d{2,4})\s+(\d{1,2}\s*[A-Za-z]{3})\s+(.*?)(?:\n|$)',
        text
    )

    dep_airport = ''
    arr_airport = ''
    flight_number = ''
    dep_date_iso = ''
    aircraft = ''

    if flight_match:
        dep_airport = flight_match.group(1)
        arr_airport = flight_match.group(2)
        raw_fn = flight_match.group(3).replace(' ', '')
        flight_number = raw_fn
        dep_date_iso = _parse_date_str(flight_match.group(4))
        # 提取机型
        aircraft_str = flight_match.group(5).strip()
        aircraft_m = re.search(r'(Boeing\s+[\d-]+|Airbus\s+[A-Z\d-]+)', aircraft_str, re.IGNORECASE)
        if aircraft_m:
            aircraft = aircraft_m.group(1)

    # === 时间 + 航站楼 ===
    # 格式: 15:25 - 17:35  Terminal 3  04h10
    time_match = re.search(
        r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s+Terminal\s*(\d+)',
        text
    )

    dep_time = ''
    arr_time = ''
    terminal = ''

    if time_match:
        dep_time = time_match.group(1)
        arr_time = time_match.group(2)
        terminal = f'T{time_match.group(3)}'

    # 到达日期（默认同天，如果到达时间小于出发时间则+1天）
    arr_date_iso = dep_date_iso
    if dep_time and arr_time and dep_date_iso:
        dep_minutes = int(dep_time.split(':')[0]) * 60 + int(dep_time.split(':')[1])
        arr_minutes = int(arr_time.split(':')[0]) * 60 + int(arr_time.split(':')[1])
        if arr_minutes < dep_minutes:
            # 跨天
            from datetime import timedelta
            dep_dt = datetime.strptime(dep_date_iso, '%Y-%m-%d')
            arr_date_iso = (dep_dt + timedelta(days=1)).strftime('%Y-%m-%d')

    # === 舱位代码 ===
    # 在航段行附近找单字母舱位代码，或 ESGO-AD 这类
    cabin_code = ''
    cabin_match = re.search(r'\b([A-Z])\s+\d{2}[A-Za-z]{3}\s+[A-Z]{6}', text)
    if cabin_match:
        cabin_code = cabin_match.group(1)
    if not cabin_code:
        # 从 ESGO 等信息中提取
        esgo_match = re.search(r'ESGO', text)
        if esgo_match:
            cabin_code = 'Y'  # ESGO通常是经济舱

    # 构建航段
    if dep_airport and arr_airport:
        segment = {
            'flight_number': flight_number,
            'cabin_code': cabin_code or 'Y',
            'departure_airport': dep_airport,
            'arrival_airport': arr_airport,
            'departure_date': dep_date_iso,
            'departure_time': dep_time,
            'arrival_date': arr_date_iso,
            'arrival_time': arr_time,
            'airline_name': 'US-Bangla Airlines',
            'cabin_class': 'Economy',
            'departure_terminal': terminal,
            'arrival_terminal': '',
            'ticket_number': '',
            'pnr': result['pnr'],
            'baggage': '',
        }
        result['segments'].append(segment)

    # === 乘客信息 ===
    # 格式: AD Mr. UDDIN JASHIM 或 AD Mrs. BEGUM FATIMA
    pax_matches = re.finditer(
        r'(?:AD|CH|IN)\s+(?:Mr|Mrs|Ms|Miss|Mstr)\.\s*([A-Z\s]+?)(?:\n|$)',
        text
    )
    for pm in pax_matches:
        name = pm.group(0).strip()
        # 判断乘客类型
        pax_type = 'adult'
        if name.startswith('CH'):
            pax_type = 'child'
        elif name.startswith('IN'):
            pax_type = 'infant'

        # 清理名字：去掉 AD/CH/IN 前缀
        clean_name = re.sub(r'^(?:AD|CH|IN)\s+', '', name).strip()

        result['passengers'].append({
            'name': clean_name,
            'type': pax_type,
            'selling_price': 0,
            'cost_price': 0,
            'passport_number': '',
        })

    # === 票号 ===
    # 格式: 39131169  7792411781506 2/1
    ticket_match = re.search(r'(\d{8})\s+(\d{13})', text)
    if ticket_match and result['segments']:
        result['segments'][0]['ticket_number'] = ticket_match.group(2)

    # === 价格信息 ===
    # 策略：从 Ticket sale 行提取售价SGD，从 Commission 行提取佣金，成本=售价-佣金

    total_selling = 0
    commission = 0

    # 1) 售价: 从 Ticket sale/payment 行 "~ 289.02 SGD"
    sale_match = re.search(
        r'Ticket\s*(?:sale|payment).*?~\s*([\d,]+\.\d{2})\s*SGD',
        text, re.DOTALL | re.IGNORECASE
    )
    if sale_match:
        total_selling = float(_clean_amount(sale_match.group(1)))

    # 2) 如果没找到，从 Total price 或 Amount all taxes 行提取
    if total_selling == 0:
        tp_match = re.search(r'(?:Total\s+price|Amount\s+all\s+taxes)[:\s]*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if tp_match:
            total_selling = float(_clean_amount(tp_match.group(1)))

    # 3) 兜底：找所有 xxx.xx SGD 取最大的合理值
    if total_selling == 0:
        all_sgd = re.findall(r'([\d,]+\.\d{2})\s*SGD', text)
        sgd_values = [float(_clean_amount(v)) for v in all_sgd if float(_clean_amount(v)) > 0]
        if sgd_values:
            total_selling = max(sgd_values)

    # 4) 佣金: Commission 行的 SGD 金额（取绝对值）
    comm_match = re.search(
        r'[Cc]omm[io]ssion.*?(-?\s*[\d,]+\.\d{2})\s*SGD',
        text, re.DOTALL
    )
    if comm_match:
        commission = abs(float(_clean_amount(comm_match.group(1).replace(' ', ''))))

    # 成本 = 售价 - 佣金
    cost_sgd = round(total_selling - commission, 2) if total_selling > 0 else 0

    # 也尝试直接从 Total (BDT) ~SGD 行提取成本做交叉验证
    cost_direct = re.search(r'Total\s*\(BDT\).*?~\s*([\d,]+\.\d{2})', text, re.DOTALL)
    if cost_direct:
        cost_from_bdt = float(_clean_amount(cost_direct.group(1)))
        # 优先用直接值（更准确）
        if cost_from_bdt > 0:
            cost_sgd = cost_from_bdt

    # 分配价格给乘客
    pax_count = len(result['passengers']) or 1
    per_pax_selling = round(total_selling / pax_count, 2)
    per_pax_cost = round(cost_sgd / pax_count, 2)

    for pax in result['passengers']:
        pax['selling_price'] = per_pax_selling
        pax['cost_price'] = per_pax_cost

    # === 备注信息 ===
    remarks_parts = []
    if aircraft:
        remarks_parts.append(f'机型: {aircraft}')
    if result['pnr']:
        remarks_parts.append(f'PNR: {result["pnr"]}')
    result['remarks'] = ' | '.join(remarks_parts)

    return result


def parse_indigo(text: str) -> dict:
    """解析 IndiGo Airlines 机票截图的OCR文本

    IndiGo截图格式特征:
    - 顶部: IndiGo / IndiGo access
    - 乘客: Mr./Mrs./Ms. LASTNAME FIRSTNAME
    - 航段: SIN → TRZ, 航班号 6E XXXX
    - 日期: Fri, 17 Apr
    - 时间: 05:55 / 07:30
    - 机型: A320 等
    - 价格: SGD xxx.x 各项费用明细, Total fare SGD xxx.x
    """
    result = {
        'platform': 'IndiGo',
        'segments': [],
        'passengers': [],
        'pnr': '',
        'remarks': '',
    }

    # === PNR (6位字母数字，排除常见误匹配如机型A320) ===
    pnr_match = re.search(r'\b([A-Z0-9]{6})\b', text)
    if pnr_match:
        candidate = pnr_match.group(1)
        # 排除纯数字和常见机型
        if not candidate.isdigit() and candidate not in ('ACCESS', 'INDIGO'):
            result['pnr'] = candidate

    # === 乘客信息 ===
    # 格式: Mr. VENGATESHWARAN RAMU 或 Mrs. LASTNAME FIRSTNAME
    pax_matches = re.finditer(
        r'(?:Mr|Mrs|Ms|Miss|Mstr)\.?\s+([A-Z][A-Z\s]+?)(?:\s*\n|\s*$)',
        text, re.MULTILINE
    )
    seen_names = set()
    for pm in pax_matches:
        name_raw = pm.group(0).strip()
        # 排除包含航线/机场关键词的误匹配
        if any(kw in name_raw for kw in ['SINGAPORE', 'AIRPORT', 'INTERNATIONAL', 'TERMINAL']):
            continue
        # 去重：同一个名字只添加一次
        name_key = re.sub(r'\s+', ' ', name_raw).upper()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        result['passengers'].append({
            'name': name_raw,
            'type': 'adult',
            'selling_price': 0,
            'cost_price': 0,
            'passport_number': '',
        })

    # === 航班号 + 机型 ===
    # 格式: 6E 1024 . A320  或  6E 1024 A320
    # 注意: Tesseract常把 6E 识别成 6£ 或 6€，需要兼容
    flight_match = re.search(r'(6[E£€e])\s*(\d{3,4})\s*[.\s]*\b(A\d{3}|B\d{3}|Boeing[\s\d-]+|Airbus[\s\w-]+)?\b', text)
    flight_number = ''
    aircraft = ''
    if flight_match:
        flight_number = f'6E{flight_match.group(2)}'
        if flight_match.group(3):
            aircraft = flight_match.group(3).strip()

    # === 出发/到达机场 ===
    # 寻找三字码机场对: SIN ... TRZ，优先从航段信息区域提取
    dep_airport = ''
    arr_airport = ''

    # 方式1: 找 "SIN" 和 "TRZ" 这样大写三字码在航段区域
    # IndiGo格式中会出现加粗的机场代码行
    airport_pairs = re.findall(r'\b([A-Z]{3})\b', text)
    # 过滤掉常见非机场词
    non_airport = {'THE', 'AND', 'FOR', 'NOT', 'NON', 'PER', 'SGD', 'USD', 'INR', 'BDT',
                   'MRS', 'MIS', 'TAX', 'FEE', 'AIR', 'GET', 'ADD', 'NET', 'ALL',
                   'HRS', 'MIN', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT',
                   'NOV', 'DEC', 'JAN', 'FEB', 'MAR', 'FRI', 'SAT', 'SUN', 'MON',
                   'TUE', 'WED', 'THU', 'MR.', 'STOP'}
    airports = [a for a in airport_pairs if a not in non_airport]

    # 从 "SIN TRZ" 这样的行或 "SIN" 后面跟 "TRZ" 提取
    route_match = re.search(r'\b([A-Z]{3})\b\s+\b([A-Z]{3})\b', text)
    if route_match:
        dep_airport = route_match.group(1)
        arr_airport = route_match.group(2)
        # 验证不是非机场词
        if dep_airport in non_airport or arr_airport in non_airport:
            dep_airport = ''
            arr_airport = ''

    # 方式2: 从带城市名的行提取  "SIN\nSINGAPORE (T2)" ... "TRZ\nTIRUCHIRAPPALLI"
    if not dep_airport:
        airport_city = re.findall(r'\b([A-Z]{3})\b\s*\n\s*[A-Z]{2,}', text)
        airport_city = [a for a in airport_city if a not in non_airport]
        if len(airport_city) >= 2:
            dep_airport = airport_city[0]
            arr_airport = airport_city[1]

    # === 日期 ===
    # 格式: "Fri, 17 Apr" 或 "17 Apr" 或 "17Apr"
    dep_date_iso = ''
    date_match = re.search(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[,.]?\s*(\d{1,2})\s*([A-Za-z]{3})', text)
    if date_match:
        dep_date_iso = _parse_date_str(date_match.group(1) + date_match.group(2))
    else:
        date_match2 = re.search(r'(\d{1,2})\s*([A-Za-z]{3})\s*(?:\d{4})?', text)
        if date_match2:
            dep_date_iso = _parse_date_str(date_match2.group(1) + date_match2.group(2))

    # === 出发/到达时间 ===
    # IndiGo格式: 时间单独一行 "05:55" ... "07:30"
    # 需要排除 "Check-in closes 04:40" 等非航班时间
    dep_time = ''
    arr_time = ''
    # 先去掉干扰行再提取时间
    clean_text_for_time = re.sub(r'[Cc]heck[- ]?in\s+closes\s+\d{1,2}:\d{2}', '', text)
    clean_text_for_time = re.sub(r'Travel\s+Time\s+\d+\s+Hour\s+\d+\s+min', '', clean_text_for_time)
    times = re.findall(r'\b(\d{1,2}:\d{2})\b', clean_text_for_time)
    if len(times) >= 2:
        dep_time = times[0]
        arr_time = times[1]

    # === 航站楼 ===
    # 格式: "SIN-Changi Airport(T2)" 或 "(T2)" 或 "Terminal 2"
    dep_terminal = ''
    arr_terminal = ''
    terminal_matches = re.findall(r'\(T(\d)\)|Terminal\s*(\d)', text)
    if terminal_matches:
        dep_terminal = f'T{terminal_matches[0][0] or terminal_matches[0][1]}'
        if len(terminal_matches) > 1:
            arr_terminal = f'T{terminal_matches[1][0] or terminal_matches[1][1]}'

    # === 行李 ===
    baggage = ''
    bag_match = re.search(r'(\d+)\s*[Kk]g\s*Cabin.*?(\d+)\s*[Kk]g\s*Check', text, re.DOTALL)
    if bag_match:
        baggage = f'{bag_match.group(1)}Kg Cabin + {bag_match.group(2)}Kg Check-in'
    else:
        bag_match2 = re.search(r'(\d+)\s*[Kk]g\s*(?:Cabin|Check)', text)
        if bag_match2:
            baggage = bag_match2.group(0).strip()

    # 到达日期（默认同天，跨天则+1）
    arr_date_iso = dep_date_iso
    if dep_time and arr_time and dep_date_iso:
        dep_minutes = int(dep_time.split(':')[0]) * 60 + int(dep_time.split(':')[1])
        arr_minutes = int(arr_time.split(':')[0]) * 60 + int(arr_time.split(':')[1])
        if arr_minutes < dep_minutes:
            from datetime import timedelta
            dep_dt = datetime.strptime(dep_date_iso, '%Y-%m-%d')
            arr_date_iso = (dep_dt + timedelta(days=1)).strftime('%Y-%m-%d')

    # 构建航段
    if dep_airport and arr_airport:
        segment = {
            'flight_number': flight_number,
            'cabin_code': 'Y',
            'departure_airport': dep_airport,
            'arrival_airport': arr_airport,
            'departure_date': dep_date_iso,
            'departure_time': dep_time,
            'arrival_date': arr_date_iso,
            'arrival_time': arr_time,
            'airline_name': 'IndiGo',
            'cabin_class': 'Economy',
            'departure_terminal': dep_terminal,
            'arrival_terminal': arr_terminal,
            'ticket_number': '',
            'pnr': result['pnr'],
            'baggage': baggage,
        }
        result['segments'].append(segment)

    # === 价格信息 ===
    # IndiGo格式: Total fare SGD 364.3 或各项费用 SGD xxx
    total_selling = 0

    # 1) Total fare 行
    total_match = re.search(r'Total\s+fare\s*(?:SGD|USD|INR)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if total_match:
        total_selling = float(_clean_amount(total_match.group(1)))

    # 2) 兜底: 找 "SGD xxx.x" 格式金额取最大值
    if total_selling == 0:
        all_amounts = re.findall(r'SGD\s*([\d,]+\.?\d*)', text)
        amounts = [float(_clean_amount(v)) for v in all_amounts if float(_clean_amount(v)) > 0]
        if amounts:
            total_selling = max(amounts)

    # IndiGo一般没有佣金，成本=售价
    cost_sgd = total_selling

    # 分配价格给乘客
    pax_count = len(result['passengers']) or 1
    per_pax_selling = round(total_selling / pax_count, 2)
    per_pax_cost = round(cost_sgd / pax_count, 2)

    for pax in result['passengers']:
        pax['selling_price'] = per_pax_selling
        pax['cost_price'] = per_pax_cost

    # === 备注信息 ===
    remarks_parts = []
    if aircraft:
        remarks_parts.append(f'机型: {aircraft}')
    if result['pnr']:
        remarks_parts.append(f'PNR: {result["pnr"]}')
    if baggage:
        remarks_parts.append(f'行李: {baggage}')
    result['remarks'] = ' | '.join(remarks_parts)

    return result


# === 解析器注册表 ===
# 每个平台一个解析函数，通过关键词自动检测
PARSERS = [
    {
        'name': 'US Bangla',
        'key': 'usbangla',
        'keywords': ['US-Bangla', 'US Bangla', 'USBANGLA', 'BS3', 'BS 3', 'Bangla', 'BDT'],
        'parser': parse_usbangla,
    },
    {
        'name': 'IndiGo',
        'key': 'indigo',
        'keywords': ['IndiGo', 'INDIGO', 'indigo', '6E ', '6E1', '6E2', '6E3', '6E4', '6E5', '6E6', '6E7', '6E8', '6E9'],
        'parser': parse_indigo,
    },
    # 后续添加其它平台:
    # { 'name': 'Scoot', 'key': 'scoot', 'keywords': ['Scoot', 'TR '], 'parser': parse_scoot },
    # { 'name': 'AirAsia', 'key': 'airasia', 'keywords': ['AirAsia', 'AK '], 'parser': parse_airasia },
]

# 按key索引，用于手动指定平台
PARSER_BY_KEY = {entry['key']: entry for entry in PARSERS}


def detect_and_parse(text: str, platform_key: str = None) -> dict:
    """检测平台并解析OCR文本

    Args:
        text: OCR识别出的文本
        platform_key: 手动指定的平台key（如 'usbangla'），为None时自动检测

    Returns:
        dict: 解析结果
    """
    # 手动指定平台时直接调用对应解析器
    if platform_key and platform_key in PARSER_BY_KEY:
        entry = PARSER_BY_KEY[platform_key]
        return entry['parser'](text)

    # 自动检测：遍历关键词匹配
    text_upper = text.upper()
    for entry in PARSERS:
        for kw in entry['keywords']:
            if kw.upper() in text_upper:
                return entry['parser'](text)

    # 未匹配到已知平台
    return {
        'platform': None,
        'segments': [],
        'passengers': [],
        'pnr': '',
        'remarks': '',
        'raw_text': text,
    }


def extract_from_image(data_url: str, platform: str = None) -> dict:
    """从base64图片中提取航班信息（主入口）

    Args:
        data_url: base64编码的图片数据（含 data:image/... 前缀）
        platform: 手动指定平台key（如 'usbangla'），为None时自动检测

    Returns:
        dict: { success, data/error, raw_text }
    """
    try:
        img = image_from_base64(data_url)
        text = ocr_image(img)

        if not text.strip():
            return {'success': False, 'error': '图片OCR识别失败，未提取到文字内容'}

        result = detect_and_parse(text, platform_key=platform)

        if result.get('platform') is None:
            # 自动识别失败，返回OCR文本和支持的平台列表，前端可显示手动选择
            supported = [{'key': e['key'], 'name': e['name']} for e in PARSERS]
            return {
                'success': False,
                'error': '未能自动识别平台，请手动选择后重试',
                'raw_text': text,
                'supported_platforms': supported,
                'need_manual_select': True,
            }

        has_data = bool(result.get('segments') or result.get('passengers'))
        if not has_data:
            return {
                'success': False,
                'error': f'检测到 {result["platform"]} 格式，但未提取到有效航班数据，请检查图片清晰度',
                'raw_text': text,
            }

        return {
            'success': True,
            'data': result,
            'raw_text': text,
        }

    except Exception as e:
        return {'success': False, 'error': f'图片处理失败: {str(e)}'}
