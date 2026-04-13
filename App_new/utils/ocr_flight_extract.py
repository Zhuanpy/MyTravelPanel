"""
OCR航班图片解析模块

通过 Tesseract OCR 从机票截图中提取航班信息，
解析后返回结构化数据用于自动填充订单表单。

目前支持的航司/平台:
- US Bangla Airlines (Amadeus出票界面)

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


# === 解析器注册表 ===
# 每个平台一个解析函数，通过关键词自动检测
PARSERS = [
    {
        'name': 'US Bangla',
        'key': 'usbangla',  # 前端手动选择时使用的标识
        'keywords': ['US-Bangla', 'US Bangla', 'USBANGLA', 'BS3', 'BS 3', 'Bangla', 'BDT'],
        'parser': parse_usbangla,
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
