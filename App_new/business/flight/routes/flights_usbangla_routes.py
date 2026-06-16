# -*- coding: utf-8 -*-
"""机票PDF工具集：US-Bangla生成、Ctrip清理、IndiGo去价格"""

from flask import Blueprint, render_template, request, send_file, jsonify
from flask_login import login_required
from App_new.utils.decorators import staff_only
from io import BytesIO
import os
import re
import tempfile
import shutil

flights_usbangla = Blueprint('flights_usbangla', __name__, url_prefix='/flights_usbangla')

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'static', 'images', 'airlines', 'us_bangla_logo.png'
)

# 东方航空 logo
MU_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'static', 'images', 'airlines', 'china_eastern_logo.png'
)


# ========== PDF 文本预处理 ==========

def _collapse_spaced_text(text):
    """将 PDF 中字符间带空格的文本还原"""
    lines = text.split('\n')
    result = []
    for line in lines:
        if re.match(r'^[A-Za-z\d] [A-Za-z\d] ', line.strip()):
            collapsed = re.sub(r' {3,}', '\x00', line)
            collapsed = collapsed.replace(' ', '')
            collapsed = collapsed.replace('\x00', ' ')
            result.append(collapsed)
        else:
            result.append(line)
    return '\n'.join(result)


# ========== PDF 解析 ==========

def parse_usbangla_pdf(file_stream):
    """解析 US-Bangla 原始电子机票 PDF，提取航段和乘客信息"""
    from PyPDF2 import PdfReader

    reader = PdfReader(file_stream)
    raw_text = ''
    for page in reader.pages:
        t = page.extract_text()
        if t:
            raw_text += t + '\n'

    text = _collapse_spaced_text(raw_text)

    result = {
        'booking_ref': _extract_booking_ref(text),
        'segments': _extract_segments(text),
        'passengers': _extract_passengers(text),
    }
    return result


def _extract_booking_ref(text):
    """提取预订编号"""
    m = re.search(r'([A-Z0-9]{5,8})\s*B\s*o\s*o\s*k\s*i\s*n\s*g\s*r\s*e\s*f\s*e\s*r\s*e\s*n\s*c\s*e', text) or \
        re.search(r'([A-Z0-9]{5,8})\s*Booking\s*reference', text) or \
        re.search(r'Booking\s*reference\s*#?\s*([A-Z0-9]{5,8})', text, re.IGNORECASE)
    return m.group(1).strip() if m else ''


def _extract_segments(text):
    """提取所有航段信息（支持多航段往返）"""
    segments = []
    joined = text.replace('\n', ' ')

    # 查找所有 BS 航班号+值机时间 的匹配（间距还原后粘连: "BS31012:25"）
    flight_matches = list(re.finditer(r'(BS\d{3})(\d{1,2}:\d{2})', joined))
    if not flight_matches:
        flight_matches = list(re.finditer(r'(BS\d{3,4})(\d{1,2}:\d{2})', joined))

    # 城市对（每两个一组: from, to）
    cities = re.findall(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s*\(([A-Z]{3})\)', text)

    # 日期时间对（每两个一组: dep, arr）
    date_times = re.findall(
        r'(\d{1,2}[\-\u00AD](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\-\u00AD]\d{2})\s*(\d{1,2}:\d{2})',
        text
    )

    # Terminal+Cabin（格式: "17:3531EconomyOK"）
    terminal_matches = re.findall(
        r'\d{1,2}:\d{2}\s*(\d)\s*(\d)\s*(Economy|Business|First)',
        joined, re.IGNORECASE
    )

    # Fleet
    fleet_matches = re.findall(
        r'(Boeing\s*\d{3}[\-\u00AD]\d{3}|ATR\s*\d{2}[\-\u00AD]\d{3}|Dash8[\-\u00AD]Q\d{3})',
        text, re.IGNORECASE
    )

    # Stop
    stop_matches = re.findall(r'(Non\s*stop|1\s*stop|2\s*stops?)', text, re.IGNORECASE)

    # Baggage（匹配 "40 Kg" 格式，大写K区分于Terms中的小写"kg"/"kgs"）
    baggage_matches = re.findall(r'(\d+)\s*Kg', text)

    # 根据航班数构建航段
    num_segments = max(len(flight_matches), 1)

    for i in range(num_segments):
        seg = {
            'flight': '', 'checkin': '',
            'from_city': '', 'to_city': '',
            'dep_date': '', 'dep_time': '', 'arr_date': '', 'arr_time': '',
            'dep_terminal': '', 'arr_terminal': '',
            'cabin': 'Economy', 'status': 'OK',
            'fleet': '', 'stop': 'Non stop', 'baggage': '',
        }

        # 航班号 + 值机
        if i < len(flight_matches):
            seg['flight'] = flight_matches[i].group(1)
            seg['checkin'] = flight_matches[i].group(2)

        # 城市（每航段两个城市: from, to）
        ci = i * 2
        if ci + 1 < len(cities):
            seg['from_city'] = f"{cities[ci][0]} ({cities[ci][1]})"
            seg['to_city'] = f"{cities[ci + 1][0]} ({cities[ci + 1][1]})"

        # 日期时间（每航段两组: dep, arr）
        di = i * 2
        if di + 1 < len(date_times):
            seg['dep_date'] = date_times[di][0].replace('\u00AD', '-')
            seg['dep_time'] = date_times[di][1]
            seg['arr_date'] = date_times[di + 1][0].replace('\u00AD', '-')
            seg['arr_time'] = date_times[di + 1][1]

        # Terminal + Cabin
        if i < len(terminal_matches):
            seg['dep_terminal'] = terminal_matches[i][0]
            seg['arr_terminal'] = terminal_matches[i][1]
            seg['cabin'] = terminal_matches[i][2].capitalize()

        # Fleet
        if i < len(fleet_matches):
            seg['fleet'] = fleet_matches[i].replace('\u00AD', '-')

        # Stop
        if i < len(stop_matches):
            seg['stop'] = stop_matches[i].replace('\u00AD', '-')
            # 规范化
            if 'non' in seg['stop'].lower():
                seg['stop'] = 'Non stop'

        # Baggage（按航段索引匹配，每个航段各自的行李额）
        if i < len(baggage_matches):
            seg['baggage'] = f"{baggage_matches[i]} Kg"

        segments.append(seg)

    # 如果没有匹配到任何航班，返回一个空航段模板
    if not segments:
        segments.append({
            'flight': '', 'checkin': '',
            'from_city': '', 'to_city': '',
            'dep_date': '', 'dep_time': '', 'arr_date': '', 'arr_time': '',
            'dep_terminal': '', 'arr_terminal': '',
            'cabin': 'Economy', 'status': 'OK',
            'fleet': '', 'stop': 'Non stop', 'baggage': '',
        })

    return segments


def _extract_passengers(text):
    """提取乘客列表"""
    passengers = []
    pattern = r'(Mr\.|Mrs\.|Ms\.|Mstr\.)\s*([A-Z][A-Z\s]+?)\s+(\d{13})\s*(Adult\(s\)|Child|Infant)\s*([A-Z][A-Z0-9]+)'
    matches = re.findall(pattern, text)

    seen_tickets = set()
    for m in matches:
        title, name, ticket, pax_type, passport = m
        name = re.sub(r'\s+', ' ', name.strip())
        if ticket in seen_tickets:
            continue
        seen_tickets.add(ticket)
        passengers.append({
            'title': title, 'name': name, 'ticket': ticket,
            'pax_type': pax_type, 'passport': passport,
        })
    return passengers


# ========== PDF 生成 ==========

def _extract_pdf_header_image(file_bytes):
    """从原始US-Bangla PDF中提取头部区域（logo+蓝色横幅+二维码）保存为临时图片

    返回临时文件ID，后续生成PDF时使用。
    """
    import fitz
    import uuid

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc[0]

    # 截取头部区域：找到内容实际左右边界（蓝色横幅/图片），精确裁剪
    pw = page.rect.width
    x_min, x_max = pw, 0
    # 从绘制元素（蓝色横幅线）找边界
    for d in page.get_drawings():
        r = d['rect']
        if r.y0 < 115 and r.width > 100:
            x_min = min(x_min, r.x0)
            x_max = max(x_max, r.x1)
    # 从图片找边界
    for info in page.get_image_info():
        bbox = info['bbox']
        if bbox[1] < 115:
            x_min = min(x_min, bbox[0])
            x_max = max(x_max, bbox[2])
    # 兜底
    if x_min >= x_max:
        x_min, x_max = 0, pw
    # 内缩1pt去掉原始PDF的边框线
    clip = fitz.Rect(x_min + 1, 1, x_max - 1, 114)
    pix = page.get_pixmap(clip=clip, dpi=200)

    header_id = uuid.uuid4().hex[:12]
    header_dir = os.path.join(tempfile.gettempdir(), 'usbangla_headers')
    os.makedirs(header_dir, exist_ok=True)
    header_path = os.path.join(header_dir, f'{header_id}.png')
    pix.save(header_path)

    doc.close()
    return header_id


def _get_header_image_path(header_id):
    """根据header_id获取临时头部图片路径"""
    if not header_id:
        return None
    header_path = os.path.join(tempfile.gettempdir(), 'usbangla_headers', f'{header_id}.png')
    return header_path if os.path.exists(header_path) else None


def _create_ticket_pdf_class():
    from fpdf import FPDF

    class TicketPDF(FPDF):
        def __init__(self, booking_ref, logo_path, header_image_path=None):
            super().__init__()
            self.booking_ref = booking_ref
            self.logo_path = logo_path
            self.header_image_path = header_image_path

        def header(self):
            if self.header_image_path and os.path.exists(self.header_image_path):
                # 使用原始PDF的头部图片（包含logo+蓝色横幅+二维码+booking ref）
                self.image(self.header_image_path, x=10, y=3, w=190)
                self.set_y(42)
                self.ln(3)
            else:
                # 降级：使用静态logo
                if os.path.exists(self.logo_path):
                    self.image(self.logo_path, x=10, y=8, w=60)
                self.set_font("Helvetica", "B", 18)
                self.set_text_color(0, 51, 102)
                self.set_y(10)
                self.cell(0, 10, "e-ticket", align="R", new_x="LMARGIN", new_y="NEXT")
                self.set_font("Helvetica", "B", 12)
                self.set_text_color(80, 80, 80)
                self.cell(0, 7, f"Booking reference # {self.booking_ref}", align="R", new_x="LMARGIN", new_y="NEXT")
                self.set_y(max(self.get_y(), 24))
                self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
                self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10,
                      "Us-bangla Airlines : 77, Sohrawardi Avenue, Baridhara Diplomatic Zone, "
                      "Dhaka - 1212, Bangladesh | E-mail:info@usbair.com | Hotline: 13605 | www.usbair.com",
                      align="C")

    return TicketPDF


def draw_table_row(pdf, x, widths, texts, bold=False, fill=False, h=7):
    pdf.set_x(x)
    style = "B" if bold else ""
    if fill:
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
    else:
        pdf.set_text_color(30, 30, 30)
    for i, (w, t) in enumerate(zip(widths, texts)):
        pdf.set_font("Helvetica", style, 8)
        pdf.cell(w, h, str(t), border=1, fill=fill, align="C" if i > 0 else "L")
    pdf.ln(h)


def generate_single_ticket(pax, flight_data, logo_path, header_image_path=None):
    """生成单个乘客的机票 PDF（支持多航段），返回 bytes"""
    TicketPDF = _create_ticket_pdf_class()
    booking_ref = flight_data.get('booking_ref', '')
    segments = flight_data.get('segments', [])

    pdf = TicketPDF(booking_ref, logo_path, header_image_path=header_image_path)
    pdf.add_page()

    # === Passenger Information ===
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, "Passenger Information", new_x="LMARGIN", new_y="NEXT")

    headers = ["Passenger Name", "Ticket Number", "Pax. Type", "Passport Number"]
    widths = [60, 50, 35, 45]
    draw_table_row(pdf, 10, widths, headers, bold=True, fill=True)
    row = [f"{pax['title']} {pax['name']}", pax["ticket"], pax.get("pax_type", "Adult(s)"), pax["passport"]]
    draw_table_row(pdf, 10, widths, row)

    pdf.ln(6)

    # === Travel Itinerary ===
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, "Travel Itinerary", new_x="LMARGIN", new_y="NEXT")

    it_headers = ["Flight", "Check-in", "From", "To", "Departure", "Arrival", "Cabin", "Status"]
    it_widths = [18, 18, 34, 30, 28, 28, 20, 14]
    draw_table_row(pdf, 10, it_widths, it_headers, bold=True, fill=True)

    for seg in segments:
        it_row = [
            seg.get("flight", ""), seg.get("checkin", ""),
            seg.get("from_city", ""), seg.get("to_city", ""),
            f"{seg.get('dep_date', '')} {seg.get('dep_time', '')}".strip(),
            f"{seg.get('arr_date', '')} {seg.get('arr_time', '')}".strip(),
            seg.get("cabin", ""), seg.get("status", "OK")
        ]
        draw_table_row(pdf, 10, it_widths, it_row, h=10)

        # Fleet info（每航段一行）
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(80, 80, 80)
        fleet_line = f"Fleet: {seg.get('fleet', '')}" if seg.get('fleet') else ''
        if seg.get('stop'):
            fleet_line += f" | {seg['stop']}" if fleet_line else seg['stop']
        if seg.get('dep_terminal'):
            fleet_line += f" | Departure Terminal: {seg['dep_terminal']}"
        if seg.get('arr_terminal'):
            fleet_line += f" | Arrival Terminal: {seg['arr_terminal']}"
        if fleet_line:
            pdf.cell(0, 6, fleet_line, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # === Baggage Details ===
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, "Baggage Details", new_x="LMARGIN", new_y="NEXT")

    bg_headers = ["Trip Segment", "Pax. Name", "Baggage Allowance"]
    bg_widths = [60, 70, 60]
    draw_table_row(pdf, 10, bg_widths, bg_headers, bold=True, fill=True)

    for seg in segments:
        from_code = seg["from_city"].split("(")[-1].replace(")", "").strip() if "(" in seg.get("from_city", "") else seg.get("from_city", "")
        to_code = seg["to_city"].split("(")[-1].replace(")", "").strip() if "(" in seg.get("to_city", "") else seg.get("to_city", "")
        bg_row = [f"{from_code} -> {to_code}", pax["name"], seg.get("baggage", "")]
        draw_table_row(pdf, 10, bg_widths, bg_row)

    pdf.ln(10)

    # === Travel Note ===
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, "Travel Note", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(50, 50, 50)
    notes = [
        "Check-in counter opens 1:30 hour (Domestic) and 3:00 hour (International) prior to flight departure and closes 30 minutes before Domestic and 60 minutes before International flight departure time.",
        "Passenger fails to report at check-in before closure time shall be considered as No-Show and refused to board on the same flight.",
        "Please report check-in counter with valid photo ID for Domestic and valid travel pass / passport with at least six months validity for international journey.",
        "Once the boarding pass is issued / printed, respected passengers' coupon is considered as used, no further voluntary refund / re-issuance claim is acceptable.",
        "Boarding gate closes 20 minutes before Domestic and 30 minutes before International flight departure time.",
        "Check-in baggage applicable as per fare rule and maximum within two pieces. Hand carry bag shall not exceed 15 lbs. or 7 Kg.",
        "After ticket issuance Passenger name or identity change / Transfer / Re-route / Endorsement etc. are not allowed.",
    ]
    for note in notes:
        pdf.cell(5, 5, "-")
        pdf.set_x(15)
        pdf.multi_cell(180, 4, note)
        pdf.ln(1)

    return pdf.output()


# ========== 路由 ==========

@flights_usbangla.route('/ticket_generator')
@login_required
@staff_only
def ticket_generator():
    return render_template('business/flight/usbangla_ticket_generator.html')


@flights_usbangla.route('/parse_pdf', methods=['POST'])
@login_required
@staff_only
def parse_pdf():
    file = request.files.get('pdf_file')
    if not file:
        return jsonify({'success': False, 'message': '请选择PDF文件'})
    try:
        # 读取文件内容（后续PyPDF2和PyMuPDF都要用）
        file_bytes = file.stream.read()

        result = parse_usbangla_pdf(BytesIO(file_bytes))

        # 如果PDF正文中未提取到预订编号，尝试从文件名中提取
        booking_ref = result['booking_ref']
        if not booking_ref and file.filename:
            fn_match = re.search(r'[_\-]([A-Z0-9]{5,8})[_\-]', file.filename) or \
                       re.search(r'[_\-]([A-Z0-9]{5,8})\.pdf', file.filename, re.IGNORECASE)
            if fn_match:
                booking_ref = fn_match.group(1)

        # 从原始PDF提取头部图片（logo + 蓝色横幅 + 二维码）
        header_id = _extract_pdf_header_image(file_bytes)

        return jsonify({
            'success': True,
            'booking_ref': booking_ref,
            'segments': result['segments'],
            'passengers': result['passengers'],
            'header_id': header_id,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'PDF解析失败：{str(e)}'})


@flights_usbangla.route('/generate_tickets', methods=['POST'])
@login_required
@staff_only
def generate_tickets():
    import zipfile

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400

    flight_data = {
        'booking_ref': data.get('booking_ref', ''),
        'segments': data.get('segments', []),
    }
    passengers = data.get('passengers', [])

    if not passengers:
        return jsonify({'success': False, 'message': '请至少添加一位乘客'}), 400

    booking_ref = flight_data['booking_ref'] or 'UNKNOWN'

    # 获取原始PDF的头部图片
    header_id = data.get('header_id', '')
    header_image_path = _get_header_image_path(header_id)

    try:
        if len(passengers) == 1:
            pax = passengers[0]
            pdf_bytes = generate_single_ticket(pax, flight_data, LOGO_PATH, header_image_path=header_image_path)
            output = BytesIO(pdf_bytes)
            safe_name = pax['name'].replace(' ', '_')
            filename = f"E-ticket_{booking_ref}_{safe_name}.pdf"
            return send_file(output, download_name=filename, as_attachment=True, mimetype='application/pdf')
        else:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for pax in passengers:
                    pdf_bytes = generate_single_ticket(pax, flight_data, LOGO_PATH, header_image_path=header_image_path)
                    safe_name = pax['name'].replace(' ', '_')
                    filename = f"E-ticket_{booking_ref}_{safe_name}.pdf"
                    zf.writestr(filename, pdf_bytes)
            zip_buffer.seek(0)
            zip_filename = f"E-tickets_{booking_ref}.zip"
            return send_file(zip_buffer, download_name=zip_filename, as_attachment=True, mimetype='application/zip')
    except Exception as e:
        return jsonify({'success': False, 'message': f'生成失败：{str(e)}'}), 500


# ====================================================================
#  Ctrip/Trip.com 行程单清理
# ====================================================================

_CTRIP_FONTNAME = "helv"
_CTRIP_FONTSIZE = 9.5
_CTRIP_COLOR = (0, 0, 0)


def _ctrip_find_and_remove_logos(page):
    """去除页面右上角的 Trip.com Group logo 和 IATA logo"""
    import fitz

    pw = page.rect.width
    blocks = page.get_text("dict")["blocks"]
    img_blocks = [b for b in blocks if b["type"] == 1 and b["bbox"][0] > pw * 0.4 and b["bbox"][1] < 120]
    if img_blocks:
        x0 = min(b["bbox"][0] for b in img_blocks) - 5
        y0 = min(b["bbox"][1] for b in img_blocks) - 5
        x1 = max(b["bbox"][2] for b in img_blocks) + 5
        y1 = max(b["bbox"][3] for b in img_blocks) + 5
        page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1, 1, 1))
        return True
    return False


def _ctrip_find_and_remove_boilerplate(page):
    """去除 'We advise you...' 提示语"""
    import fitz

    results = page.search_for("We advise you print out")
    if results:
        r = results[0]
        end_results = page.search_for("possible.")
        end_y = end_results[0].y1 if end_results else r.y1 + 16
        page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, page.rect.width - 50, end_y + 2), fill=(1, 1, 1))
        return end_y
    return None


def _ctrip_find_and_remove_booking_no(page):
    """去除 Booking No. 行"""
    import fitz
    results = page.search_for("Booking No.")
    if results:
        r = results[0]
        page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, page.rect.width - 50, r.y1 + 2), fill=(1, 1, 1))
        return r.y1
    return None


def _ctrip_fix_name_line(page):
    """修复姓名换行：将 'XX (First name) YY' + 'ZZ (Last name)' 合并为一行
    支持多个乘客/多个行程段，每段独立处理，返回列表"""
    import fitz

    blocks = page.get_text("dict")["blocks"]
    all_name_spans = []
    half_w = page.rect.width / 2
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                bbox = span["bbox"]
                if bbox[0] > half_w:
                    continue
                if any(kw in txt for kw in ["(First", "(Last", "name)", "(First name)", "(Last name)"]):
                    all_name_spans.append(span)
    if not all_name_spans:
        return []

    # 按 y 坐标排序，按 "(First" 关键字分割每位乘客
    all_name_spans.sort(key=lambda s: s["bbox"][1])
    groups = []
    current_group = []
    for s in all_name_spans:
        txt = s["text"].strip()
        if "(First" in txt and current_group:
            groups.append(current_group)
            current_group = [s]
        else:
            current_group.append(s)
    if current_group:
        groups.append(current_group)

    results = []
    for name_spans in groups:
        raw_name = " ".join(s["text"].strip() for s in name_spans)
        clean_name = re.sub(r'\(\s*First\s*name\s*\)', '', raw_name)
        clean_name = re.sub(r'\(\s*Last\s*name\s*\)', '', clean_name)
        clean_name = re.sub(r'\(\s*First\b', '', clean_name)
        clean_name = re.sub(r'\bname\s*\)', '', clean_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()

        x0 = min(s["bbox"][0] for s in name_spans) - 1
        y0 = min(s["bbox"][1] for s in name_spans) - 1
        x1 = max(s["bbox"][2] for s in name_spans) + 1
        y1 = max(s["bbox"][3] for s in name_spans) + 1
        page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1, 1, 1))
        results.append({"name": clean_name, "x": x0 + 1, "y": name_spans[0]["bbox"][1] + _CTRIP_FONTSIZE + 1})

    return results


def _ctrip_fix_wrapped_flight_info(page):
    """修复航班信息换行：将跨两行的机场名称合并为一行"""
    blocks = page.get_text("dict")["blocks"]
    fixes = []
    all_spans = []
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                all_spans.append(span)
    for i, span in enumerate(all_spans):
        txt = span["text"].strip()
        if "International" in txt and txt.endswith("International"):
            for j in range(i + 1, min(i + 3, len(all_spans))):
                next_txt = all_spans[j]["text"].strip()
                if next_txt.startswith("Airport"):
                    combined = txt.replace("International", "Intl") + " " + next_txt
                    fixes.append({
                        "main_span": span,
                        "wrap_span": all_spans[j],
                        "combined": combined,
                    })
                    break
    return fixes


def _ctrip_remove_page_numbers(page):
    """去除页面底部的页码"""
    import fitz

    ph = page.rect.height
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                if txt.isdigit() and span["bbox"][1] > ph - 70:
                    page.add_redact_annot(
                        fitz.Rect(span["bbox"][0] - 2, span["bbox"][1] - 2,
                                  span["bbox"][2] + 2, span["bbox"][3] + 2),
                        fill=(1, 1, 1))


def _ctrip_fix_trip_com_text(page):
    """将 'Trip.com' 替换为 'The airline'"""
    import fitz
    results = page.search_for("Trip.com bears no responsibility if passengers are unable to")
    if results:
        r = results[0]
        page.add_redact_annot(fitz.Rect(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1), fill=(1, 1, 1))
        return {"x": r.x0, "y": r.y1 - 2}
    results = page.search_for("Trip.com")
    for r in results:
        page.add_redact_annot(fitz.Rect(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1), fill=(1, 1, 1))
    return None


def _ctrip_remove_baggage_information(page):
    """去除 'Baggage Information' 标题及之后的所有内容"""
    import fitz
    pw = page.rect.width
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                if txt == "Baggage Information" and span["size"] > 12:
                    bi_y = span["bbox"][1] - 15
                    page.add_redact_annot(fitz.Rect(0, bi_y, pw, page.rect.height), fill=(1, 1, 1))
                    return bi_y
    return None


def process_ctrip_pdf(file_stream):
    """处理 Ctrip/Trip.com 行程单PDF，返回清理后的 bytes

    优化：支持多乘客姓名、多航段表头、通用空白区域压缩
    """
    import fitz

    # 写入临时文件（fitz 需要文件路径）
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        os.write(tmp_fd, file_stream.read())
        os.close(tmp_fd)

        doc = fitz.open(tmp_path)
        total_pages = doc.page_count
        page = doc[0]
        pw = page.rect.width
        ph = page.rect.height

        # ===== 第 1 页处理 =====
        page1_gaps = []  # 收集所有需要消除的空白区域 (y0, y1)

        _ctrip_find_and_remove_logos(page)
        boilerplate_end = _ctrip_find_and_remove_boilerplate(page)
        booking_end = _ctrip_find_and_remove_booking_no(page)

        # 记录提示语/订单号的空白区域
        if boilerplate_end or booking_end:
            bp_res = page.search_for("We advise you print out")
            bk_res = page.search_for("Booking No.")
            all_y0 = [r.y0 for r in bp_res] + [r.y0 for r in bk_res]
            if all_y0:
                gap_y0 = min(all_y0) - 2
                gap_y1 = max(filter(None, [boilerplate_end, booking_end])) + 2
                page1_gaps.append((gap_y0, gap_y1))

        # 简化 "Airline Booking Reference" 表头为 "Reference"（支持多航段）
        all_header_spans = []
        half_w = page.rect.width / 2
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    bbox = span["bbox"]
                    if bbox[0] > half_w:
                        if txt in ["Airline Booking", "Airline", "Booking", "Reference"]:
                            all_header_spans.append(span)

        # 按 y 坐标聚类分组（y 间距 > 30 视为不同航段）
        header_groups = []
        if all_header_spans:
            all_header_spans.sort(key=lambda s: s["bbox"][1])
            current_group = [all_header_spans[0]]
            for s in all_header_spans[1:]:
                if s["bbox"][1] - current_group[-1]["bbox"][1] > 30:
                    header_groups.append(current_group)
                    current_group = [s]
                else:
                    current_group.append(s)
            header_groups.append(current_group)

        for hg in header_groups:
            x0 = min(s["bbox"][0] for s in hg) - 2
            y0 = min(s["bbox"][1] for s in hg) - 2
            x1 = max(s["bbox"][2] for s in hg) + 2
            y1 = max(s["bbox"][3] for s in hg) + 2
            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1, 1, 1))

        # 记录每个表头组中多余行的空白区域
        for hg in header_groups:
            sorted_spans = sorted(hg, key=lambda s: s["bbox"][1])
            first_y = sorted_spans[0]["bbox"][1]
            later = [s for s in sorted_spans if s["bbox"][1] > first_y + 5]
            if later:
                gy0 = min(s["bbox"][1] for s in later) - 2
                gy1 = max(s["bbox"][3] for s in later) + 3
                page1_gaps.append((gy0, gy1))

        name_infos = _ctrip_fix_name_line(page)

        flight_fixes = _ctrip_fix_wrapped_flight_info(page)
        for fix in flight_fixes:
            main = fix["main_span"]
            wrap = fix["wrap_span"]
            redact_rect = fitz.Rect(
                main["bbox"][0] - 1, main["bbox"][1] - 1,
                max(main["bbox"][2], wrap["bbox"][2]) + 1, wrap["bbox"][3] + 1)
            page.add_redact_annot(redact_rect, fill=(1, 1, 1))
            # 记录换行区域的空白（第二行）
            page1_gaps.append((wrap["bbox"][1] - 1, wrap["bbox"][3] + 3))

        _ctrip_remove_page_numbers(page)
        page.apply_redactions()

        # 插入修正后的文字
        for hg in header_groups:
            hx = min(s["bbox"][0] for s in hg)
            hy = min(s["bbox"][1] for s in hg)
            page.insert_text(fitz.Point(hx, hy + _CTRIP_FONTSIZE),
                             "Reference", fontname=_CTRIP_FONTNAME, fontsize=_CTRIP_FONTSIZE, color=_CTRIP_COLOR)

        for ni in name_infos:
            page.insert_text(fitz.Point(ni["x"], ni["y"]),
                             ni["name"], fontname=_CTRIP_FONTNAME, fontsize=_CTRIP_FONTSIZE, color=_CTRIP_COLOR)

        for fix in flight_fixes:
            main = fix["main_span"]
            page.insert_text(fitz.Point(main["bbox"][0], main["bbox"][1] + _CTRIP_FONTSIZE),
                             fix["combined"], fontname=_CTRIP_FONTNAME, fontsize=_CTRIP_FONTSIZE, color=_CTRIP_COLOR)

        # ===== 第 2 页及之后处理 =====
        pages_to_delete = []
        baggage_info_found = False
        for page_idx in range(1, total_pages):
            pg = doc[page_idx]
            if baggage_info_found:
                pages_to_delete.append(page_idx)
                continue
            trip_insert = _ctrip_fix_trip_com_text(pg)
            bi_y = _ctrip_remove_baggage_information(pg)
            if bi_y:
                baggage_info_found = True
                for search_txt in ["Please check the baggage information at the bottom", "for more details."]:
                    refs = pg.search_for(search_txt)
                    for r in refs:
                        pg.add_redact_annot(fitz.Rect(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1), fill=(1, 1, 1))
            _ctrip_remove_page_numbers(pg)
            pg.apply_redactions()
            if trip_insert:
                pg.insert_text(fitz.Point(trip_insert["x"], trip_insert["y"]),
                               "The airline bears no responsibility if passengers are unable to",
                               fontname=_CTRIP_FONTNAME, fontsize=9.2, color=_CTRIP_COLOR)
            remaining_text = pg.get_text().strip()
            if len(remaining_text) < 50:
                pages_to_delete.append(page_idx)

        for idx in sorted(pages_to_delete, reverse=True):
            doc.delete_page(idx)

        # ===== 通用多段裁剪，消除第 1 页所有空白区域 =====
        # 合并重叠的空白区域
        page1_gaps.sort(key=lambda g: g[0])
        merged_gaps = []
        for g in page1_gaps:
            if merged_gaps and g[0] <= merged_gaps[-1][1] + 2:
                merged_gaps[-1] = (merged_gaps[-1][0], max(merged_gaps[-1][1], g[1]))
            else:
                merged_gaps.append(g)

        # 保存中间结果
        tmp2_path = tmp_path + ".mid"
        doc.save(tmp2_path)
        doc.close()

        if merged_gaps:
            doc = fitz.open(tmp2_path)
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=pw, height=ph)

            # 构建保留区段（跳过所有空白区域）
            segments = []
            cur_y = 0
            for gy0, gy1 in merged_gaps:
                if gy0 > cur_y:
                    segments.append((cur_y, gy0))
                cur_y = gy1
            if cur_y < ph:
                segments.append((cur_y, ph))

            dest_y = 0.0
            for src_y0, src_y1 in segments:
                seg_h = src_y1 - src_y0
                new_page.show_pdf_page(
                    fitz.Rect(0, dest_y, pw, dest_y + seg_h),
                    doc, 0,
                    clip=fitz.Rect(0, src_y0, pw, src_y1))
                dest_y += seg_h

            # 用白色填充底部空余区域
            if dest_y < ph:
                new_page.draw_rect(fitz.Rect(0, dest_y, pw, ph), color=(1, 1, 1), fill=(1, 1, 1))

            # 复制其余页面
            for i in range(1, doc.page_count):
                new_doc.insert_pdf(doc, from_page=i, to_page=i)

            doc.close()
            final_doc = new_doc
        else:
            final_doc = fitz.open(tmp2_path)

        # 输出到 BytesIO
        output = BytesIO()
        final_doc.save(output, deflate=True)
        final_doc.close()
        output.seek(0)

        # 清理临时文件
        for p in [tmp_path, tmp2_path]:
            if os.path.exists(p):
                os.remove(p)

        return output
    except Exception:
        # 清理临时文件
        for p in [tmp_path, tmp_path + ".mid"]:
            if os.path.exists(p):
                os.remove(p)
        raise


# ====================================================================
#  IndiGo 机票去价格
# ====================================================================

# 价格相关关键词
_INDIGO_PRICE_KEYWORDS = [
    "Flight summary", "Fare summary", "Fare Breakup", "Fare Break-up",
    "Fare Details", "Fare Information", "Payment Details", "Payment Summary",
    "Payment Information", "Price Details", "Price Breakup", "Price Summary",
    "AirFare charge", "AirFare", "Air Fare", "Base Fare", "Total Fare",
    "Total Amount", "Total Price", "Grand Total", "Amount Paid", "Amount Due",
    "Tax Invoice", "Invoice Details",
    "SGD", "INR", "USD", "BDT", "MYR",
]

# 需要保留的内容关键词
_INDIGO_KEEP_KEYWORDS = [
    "Baggage Information", "Baggage Allowance", "Baggage Details",
    "Check-in:", "Cabin:",
]


def _indigo_find_price_top(page):
    """在页面中查找价格区域的最高 y 坐标"""
    best_y = None
    matched_kw = None
    text = page.get_text().upper()
    for kw in _INDIGO_PRICE_KEYWORDS:
        if kw.upper() not in text:
            continue
        results = page.search_for(kw)
        if results:
            for r in results:
                if best_y is None or r.y0 < best_y:
                    best_y = r.y0
                    matched_kw = kw
    return best_y, matched_kw


def _indigo_find_keep_bottom(page):
    """找到需要保留内容的最低 y 坐标"""
    bottom = 0
    text = page.get_text()
    for kw in _INDIGO_KEEP_KEYWORDS:
        if kw not in text:
            continue
        results = page.search_for(kw)
        if results:
            for r in results:
                if r.y1 > bottom:
                    bottom = r.y1
    return bottom


def process_indigo_pdf(file_stream):
    """处理 IndiGo 机票PDF，去除价格信息，返回清理后的 bytes"""
    import fitz

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        os.write(tmp_fd, file_stream.read())
        os.close(tmp_fd)

        doc = fitz.open(tmp_path)
        total_pages = doc.page_count
        price_found = False
        pages_to_delete = []

        # 扫描第 2 页起
        for page_idx in range(1, total_pages):
            page = doc[page_idx]
            price_y, matched_kw = _indigo_find_price_top(page)
            if price_y is None:
                continue
            price_found = True
            keep_bottom = _indigo_find_keep_bottom(page)
            redact_y = price_y - 15
            if keep_bottom > 0:
                redact_y = max(redact_y, keep_bottom + 5)
            for drawing in page.get_drawings():
                rect = drawing["rect"]
                if keep_bottom < rect.y0 < price_y:
                    redact_y = min(redact_y, rect.y0 - 2)
            redact_rect = fitz.Rect(0, redact_y, page.rect.width, page.rect.height)
            page.add_redact_annot(redact_rect, fill=(1, 1, 1))
            page.apply_redactions()
            for later_idx in range(page_idx + 1, total_pages):
                if later_idx not in pages_to_delete:
                    pages_to_delete.append(later_idx)
            break

        if not price_found:
            # 第 1 页也搜索
            page = doc[0]
            price_y, matched_kw = _indigo_find_price_top(page)
            if price_y is not None:
                price_found = True
                keep_bottom = _indigo_find_keep_bottom(page)
                redact_y = price_y - 15
                if keep_bottom > 0:
                    redact_y = max(redact_y, keep_bottom + 5)
                for drawing in page.get_drawings():
                    rect = drawing["rect"]
                    if keep_bottom < rect.y0 < price_y:
                        redact_y = min(redact_y, rect.y0 - 2)
                redact_rect = fitz.Rect(0, redact_y, page.rect.width, page.rect.height)
                page.add_redact_annot(redact_rect, fill=(1, 1, 1))
                page.apply_redactions()
                pages_to_delete = list(range(1, total_pages))

        # 从后往前删除多余页面
        for idx in sorted(pages_to_delete, reverse=True):
            doc.delete_page(idx)

        # 输出到 BytesIO
        output = BytesIO()
        doc.save(output, deflate=True)
        doc.close()
        output.seek(0)

        os.remove(tmp_path)
        return output, price_found
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ====================================================================
#  Ctrip & IndiGo 路由
# ====================================================================

@flights_usbangla.route('/clean_ctrip', methods=['POST'])
@login_required
@staff_only
def clean_ctrip():
    """处理 Ctrip/Trip.com 行程单：去除logo、Booking No、Trip.com字样等"""
    file = request.files.get('pdf_file')
    if not file:
        return jsonify({'success': False, 'message': '请选择PDF文件'}), 400
    try:
        output = process_ctrip_pdf(file.stream)
        original_name = file.filename or 'ctrip_ticket.pdf'
        clean_name = original_name.rsplit('.', 1)[0] + '_clean.pdf'
        return send_file(output, download_name=clean_name, as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500


@flights_usbangla.route('/clean_indigo', methods=['POST'])
@login_required
@staff_only
def clean_indigo():
    """处理 IndiGo 机票：去除价格信息"""
    file = request.files.get('pdf_file')
    if not file:
        return jsonify({'success': False, 'message': '请选择PDF文件'}), 400
    try:
        output, price_found = process_indigo_pdf(file.stream)
        if not price_found:
            return jsonify({'success': False, 'message': '未找到价格相关内容，无需处理'}), 200
        original_name = file.filename or 'indigo_ticket.pdf'
        clean_name = original_name.rsplit('.', 1)[0] + '_clean.pdf'
        return send_file(output, download_name=clean_name, as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500


# ====================================================================
# 去哪儿 (Qunar) 行程单清理
# ====================================================================

def _qunar_find_and_remove_logos(page):
    """去除页面左上角的去哪儿 logo"""
    import fitz
    blocks = page.get_text("dict")["blocks"]
    img_blocks = [b for b in blocks if b["type"] == 1 and b["bbox"][1] < 120]
    if img_blocks:
        x0 = min(b["bbox"][0] for b in img_blocks) - 5
        y0 = min(b["bbox"][1] for b in img_blocks) - 5
        x1 = max(b["bbox"][2] for b in img_blocks) + 5
        y1 = max(b["bbox"][3] for b in img_blocks) + 5
        page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1, 1, 1))
        return True
    return False


def _qunar_find_and_remove_price_lines(page):
    """去除票价/税款/付款方式行（中英文关键词）"""
    import fitz
    pw = page.rect.width
    gaps = []

    # 票价行: "FARE:" / "机票款"
    for keyword in ["FARE:", "FARE：", "机票款"]:
        for r in page.search_for(keyword):
            page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw - 30, r.y1 + 2), fill=(1, 1, 1))
            gaps.append((r.y0 - 2, r.y1 + 2))

    # 税款行: "TAX:" / "稅款" / "税款"
    for keyword in ["TAX:", "TAX：", "稅款", "税款"]:
        for r in page.search_for(keyword):
            page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw - 30, r.y1 + 2), fill=(1, 1, 1))
            gaps.append((r.y0 - 2, r.y1 + 2))

    # 付款方式行: "FORM OF PAYMENT" / "付款方式"
    for keyword in ["FORM OF PAYMENT", "付款方式"]:
        for r in page.search_for(keyword):
            page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw - 30, r.y1 + 2), fill=(1, 1, 1))
            gaps.append((r.y0 - 2, r.y1 + 2))

    return gaps


def _qunar_find_and_remove_ie_pnr(page):
    """去除去哪儿订单号 IE PNR 行"""
    import fitz
    pw = page.rect.width
    gaps = []
    for r in page.search_for("IE PNR"):
        page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw - 30, r.y1 + 2), fill=(1, 1, 1))
        gaps.append((r.y0 - 2, r.y1 + 2))
    return gaps


def _qunar_find_and_remove_agency_info(page):
    """去除代理信息行（中英文关键词）"""
    import fitz
    pw = page.rect.width
    gaps = []
    for keyword in ["AGENCY ADDRESS", "IATA CODE", "代理人地址", "航协代码"]:
        for r in page.search_for(keyword):
            page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw - 30, r.y1 + 2), fill=(1, 1, 1))
            gaps.append((r.y0 - 2, r.y1 + 2))
    # 电话/传真行: 匹配 "电话" / "TEL" 开头的行（整行清除，因为传真在同一行）
    for keyword in ["电话", "TEL"]:
        for r in page.search_for(keyword):
            page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw - 30, r.y1 + 2), fill=(1, 1, 1))
            gaps.append((r.y0 - 2, r.y1 + 2))
    return gaps


def _qunar_remove_page_numbers(page):
    """去除页面底部的页码"""
    import fitz
    ph = page.rect.height
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                if txt.isdigit() and span["bbox"][1] > ph - 70:
                    page.add_redact_annot(
                        fitz.Rect(span["bbox"][0] - 2, span["bbox"][1] - 2,
                                  span["bbox"][2] + 2, span["bbox"][3] + 2),
                        fill=(1, 1, 1))


def process_qunar_pdf(file_stream, baggage=''):
    """处理去哪儿行程单PDF，返回清理后的 BytesIO"""
    import fitz

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        os.write(tmp_fd, file_stream.read())
        os.close(tmp_fd)

        doc = fitz.open(tmp_path)
        total_pages = doc.page_count
        all_page_gaps = {}

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_gaps = []

            _qunar_find_and_remove_logos(page)
            page_gaps.extend(_qunar_find_and_remove_ie_pnr(page))
            page_gaps.extend(_qunar_find_and_remove_agency_info(page))
            page_gaps.extend(_qunar_find_and_remove_price_lines(page))
            _qunar_remove_page_numbers(page)
            page.apply_redactions()

            if page_gaps:
                all_page_gaps[page_idx] = page_gaps

        # 保存中间结果
        tmp2_path = tmp_path + ".mid"
        doc.save(tmp2_path)
        doc.close()

        # 重建页面，消除空白区域
        if all_page_gaps:
            doc = fitz.open(tmp2_path)
            new_doc = fitz.open()

            for page_idx in range(doc.page_count):
                page = doc[page_idx]
                pw = page.rect.width
                ph = page.rect.height

                if page_idx not in all_page_gaps:
                    new_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
                    continue

                gaps = all_page_gaps[page_idx]
                gaps.sort(key=lambda g: g[0])
                merged_gaps = []
                for g in gaps:
                    if merged_gaps and g[0] <= merged_gaps[-1][1] + 2:
                        merged_gaps[-1] = (merged_gaps[-1][0], max(merged_gaps[-1][1], g[1]))
                    else:
                        merged_gaps.append(g)

                new_page = new_doc.new_page(width=pw, height=ph)
                segments = []
                cur_y = 0
                for gy0, gy1 in merged_gaps:
                    if gy0 > cur_y:
                        segments.append((cur_y, gy0))
                    cur_y = gy1
                if cur_y < ph:
                    segments.append((cur_y, ph))

                dest_y = 0.0
                for src_y0, src_y1 in segments:
                    seg_h = src_y1 - src_y0
                    new_page.show_pdf_page(
                        fitz.Rect(0, dest_y, pw, dest_y + seg_h),
                        doc, page_idx,
                        clip=fitz.Rect(0, src_y0, pw, src_y1))
                    dest_y += seg_h

                if dest_y < ph:
                    new_page.draw_rect(fitz.Rect(0, dest_y, pw, ph), color=(1, 1, 1), fill=(1, 1, 1))

            doc.close()
            final_doc = new_doc
        else:
            final_doc = fitz.open(tmp2_path)

        # 在最终页面上添加行李信息（压缩后，确保文字在最上层）
        if baggage:
            _qunar_add_baggage_info(final_doc, baggage)

        output = BytesIO()
        final_doc.save(output, deflate=True)
        final_doc.close()
        output.seek(0)

        for p in [tmp_path, tmp2_path]:
            if os.path.exists(p):
                os.remove(p)

        return output
    except Exception:
        for p in [tmp_path, tmp_path + ".mid"]:
            if os.path.exists(p):
                os.remove(p)
        raise


def _qunar_add_baggage_info(doc, baggage_text):
    """在每页航班表格下方追加行李额文本（清理后、压缩前调用）

    定位策略：找 "付款方式" / "FORM OF PAYMENT" 行的位置（已被redact清除），
    用该行的y坐标插入BAGGAGE文本（视觉上替代被删除的付款行）。
    若找不到付款行，则在 "注：" / "注:" 上方插入。
    """
    import fitz

    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        blocks = page.get_text("dict")["blocks"]

        # 策略1: 找 "注：" / "注:" 的位置，在其上方插入
        note_y = None
        for b in blocks:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    if txt.startswith("注：") or txt.startswith("注:"):
                        note_y = span["bbox"][1]

        # 策略2: 找最后一个OK/OPEN行
        last_flight_y = 0
        for b in blocks:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    if txt in ("OK", "OPEN"):
                        last_flight_y = max(last_flight_y, span["bbox"][3])

        if last_flight_y <= 0:
            continue

        # 确定插入y坐标（baseline）
        if note_y and note_y > last_flight_y:
            # "注："上方，留出间距
            insert_baseline = note_y - 16
        else:
            # 没有"注："时，用最后航班行下方推算
            insert_baseline = last_flight_y + 25

        label = f"BAGGAGE:  {baggage_text}"
        # 文字区域：baseline往上约12px为顶部，往下约2px为底部
        text_top = insert_baseline - 12
        text_bottom = insert_baseline + 2
        pw = page.rect.width
        # 先用白色矩形覆盖该区域的横线，避免线条穿过文字
        page.draw_rect(
            fitz.Rect(38, text_top, pw - 30, text_bottom),
            color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text(
            fitz.Point(39, insert_baseline),
            label,
            fontsize=9,
            fontname="helv",
            color=(0, 0, 0),
        )


# ==================== Expedia 行程单清理 ====================

_EXPEDIA_FONTNAME = "helv"
_EXPEDIA_FONTSIZE = 10.5
_EXPEDIA_COLOR = (0, 0, 0)
_EXPEDIA_A4_W = 595.28
_EXPEDIA_A4_H = 841.89


def _expedia_get_content_segments(page):
    """分析 Expedia 页面，返回去除区域、redact 矩形、重写项目"""
    import fitz
    blocks = page.get_text("dict")["blocks"]
    pw = page.rect.width
    ph = page.rect.height

    remove_regions = []
    redact_rects = []
    rewrite_items = []

    # 找关键段落所有出现的 y 位置（多人订单同一 label 会出现多次）
    LABEL_KEYS = ["Location", "Airline rules and restrictions",
                  "Traveller info", "Ticket number",
                  "Email address", "Phone number", "Preferences",
                  "Payment details", "Your One Key rewards",
                  "Expedia support"]
    section_positions = {k: [] for k in LABEL_KEYS}
    please_contact_ys = []  # "Please contact airline..." 行底部 Y，用作 Preferences 块结束界
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                bbox = span["bbox"]
                if txt in section_positions:
                    section_positions[txt].append(bbox[1])
                if "Please contact airline" in txt:
                    please_contact_ys.append(bbox[3])
    for k in section_positions:
        section_positions[k].sort()
    please_contact_ys.sort()

    def _first_after(ys, after_y):
        for y in ys:
            if y > after_y:
                return y
        return None

    def _first_label_y_after(after_y, exclude_keys=()):
        """所有 label 中 > after_y 的最小 Y（用于确定 PII 段下边界）"""
        best = None
        for k, ys in section_positions.items():
            if k in exclude_keys:
                continue
            y = _first_after(ys, after_y)
            if y is not None and (best is None or y < best):
                best = y
        return best

    # 兼容旧逻辑：单值 dict（取首次出现）
    section_starts = {k: ys[0] for k, ys in section_positions.items() if ys}

    # Expedia header 图片
    first_text_y = 999
    for b in blocks:
        if b["type"] == 0:
            for line in b["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        first_text_y = min(first_text_y, span["bbox"][1])
    for b in blocks:
        if b["type"] == 1 and b["bbox"][1] < 80:
            rect = fitz.Rect(b["bbox"])
            if rect.y1 > first_text_y - 2:
                rect.y1 = first_text_y - 2
            if rect.y1 > rect.y0:
                redact_rects.append(rect)
                remove_regions.append((rect.y0, rect.y1))

    # Expedia itinerary 行
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                if txt.startswith("Expedia itinerary:"):
                    bbox = span["bbox"]
                    redact_rects.append(fitz.Rect(bbox[0] - 2, bbox[1] - 2, pw - 50, bbox[3] + 2))
                    remove_regions.append((bbox[1] - 2, bbox[3] + 2))

    # 行李费用清理
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                bbox = span["bbox"]
                if "checked bag:" in txt and ("US$" in txt or "S$" in txt):
                    redact_rects.append(fitz.Rect(bbox))
                    remove_regions.append((bbox[1] - 1, bbox[3] + 1))
                if "No fee up to" in txt:
                    redact_rects.append(fitz.Rect(bbox))
                    clean_txt = txt.replace("No fee up to", "up to").replace(":  up to", ": up to")
                    rewrite_items.append({
                        "text": clean_txt, "x": bbox[0],
                        "y": bbox[1] + _EXPEDIA_FONTSIZE, "size": span["size"]
                    })
                if "Estimated baggage fees" in txt or "weight and size restrictions" in txt:
                    redact_rects.append(fitz.Rect(bbox))
                    remove_regions.append((bbox[1] - 1, bbox[3] + 1))

    # Economy 舱位代码
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                if txt.startswith("Economy (") and txt.endswith(")"):
                    bbox = span["bbox"]
                    redact_rects.append(fitz.Rect(bbox))
                    rewrite_items.append({
                        "text": "Economy", "x": bbox[0],
                        "y": bbox[1] + _EXPEDIA_FONTSIZE, "size": span["size"]
                    })

    # Location 段
    if "Location" in section_starts:
        loc_y = section_starts["Location"] - 4
        redact_rects.append(fitz.Rect(0, loc_y, pw, ph))
        remove_regions.append((loc_y, ph))

    # Airline rules and restrictions（多页时只在该页有该 label 才处理；下边界用首次出现的 Traveller info）
    for ar_y_raw in section_positions["Airline rules and restrictions"]:
        y = ar_y_raw - 10
        next_y = ph
        ti_y = _first_after(section_positions["Traveller info"], y)
        if ti_y is not None:
            next_y = ti_y - 10
        redact_rects.append(fitz.Rect(0, y, pw, next_y))
        remove_regions.append((y, next_y))

    # 一次性收集所有非空 span bbox，给「上方溢出检测」复用
    all_text_bboxes = []
    for _b in blocks:
        if _b["type"] != 0:
            continue
        for _ln in _b["lines"]:
            for _sp in _ln["spans"]:
                if _sp["text"].strip():
                    all_text_bboxes.append(_sp["bbox"])

    def _collect_block_spans(start_y, end_y):
        """收集 top y 在 [start_y, end_y) 范围内的所有非空 span bbox。"""
        return [bb for bb in all_text_bboxes if start_y <= bb[1] < end_y]

    def _safe_redact_top(span_bbox):
        """如果有上方 span 的 bbox 越界压到当前 span 的顶部（源 PDF 排版重叠），
        把 redact rect 的顶部下移到上方 span 的底下，避免吃掉上面那行文本。"""
        adjusted = span_bbox[1]
        for ob in all_text_bboxes:
            if ob[1] < span_bbox[1] and ob[3] > adjusted and not (ob[2] <= span_bbox[0] or ob[0] >= span_bbox[2]):
                adjusted = ob[3] + 0.1
        return adjusted

    def _surgical_redact(start_y_raw, end_y, side_pad=1.0):
        """逐 span 添加 redact 矩形（避免吃到上方溢出 bbox 的相邻文本，例如机票号尾巴压到下一段标题），并返回该块的 (top, bottom) 用于布局。"""
        spans = _collect_block_spans(start_y_raw, end_y)
        if not spans:
            return None
        for bb in spans:
            top = _safe_redact_top(bb)
            redact_rects.append(fitz.Rect(bb[0] - side_pad, top, bb[2] + side_pad, bb[3] + 0.5))
        return (min(s[1] for s in spans), max(s[3] for s in spans))

    # Email address 段：逐个处理每位旅客的邮箱（下边界 = 紧随其后的任意 label）
    for ea_y_raw in section_positions["Email address"]:
        end = _first_label_y_after(ea_y_raw + 1)
        end = (end - 1) if end is not None else ph
        rng = _surgical_redact(ea_y_raw, end)
        if rng:
            remove_regions.append(rng)

    # Phone number 段
    for pn_y_raw in section_positions["Phone number"]:
        end = _first_label_y_after(pn_y_raw + 1)
        end = (end - 1) if end is not None else ph
        rng = _surgical_redact(pn_y_raw, end)
        if rng:
            remove_regions.append(rng)

    # Preferences 段：以最近一行 "Please contact airline..." 作为块结束界（无该行则降级用下一个 label）
    for pr_y_raw in section_positions["Preferences"]:
        pc_end = _first_after(please_contact_ys, pr_y_raw)
        if pc_end is not None:
            end = pc_end + 1
        else:
            label_end = _first_label_y_after(pr_y_raw + 1)
            end = (label_end - 1) if label_end is not None else ph
        rng = _surgical_redact(pr_y_raw, end)
        if rng:
            remove_regions.append(rng)

    # Payment details 及之后
    if "Payment details" in section_starts:
        pd_y = section_starts["Payment details"] - 10
        redact_rects.append(fitz.Rect(0, pd_y, pw, ph))
        remove_regions.append((pd_y, ph))

    # One Key / Expedia support 兜底
    for key in ["Your One Key rewards", "Expedia support"]:
        if key in section_starts:
            ky = section_starts[key] - 4
            redact_rects.append(fitz.Rect(0, ky, pw, ph))
            remove_regions.append((ky, ph))

    return remove_regions, redact_rects, rewrite_items


def _expedia_merge_regions(regions):
    """合并重叠的区域"""
    if not regions:
        return []
    regions.sort()
    merged = [regions[0]]
    for s, e in regions[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def _expedia_get_keep_regions(remove_regions, ph):
    """从去除区域计算保留区域"""
    merged = _expedia_merge_regions(remove_regions)
    keep = []
    y = 0
    for rs, re in merged:
        if y < rs:
            keep.append((y, rs))
        y = re
    if y < ph:
        keep.append((y, ph))
    return keep


def process_expedia_pdf(file_stream):
    """处理 Expedia 行程单PDF，返回清理后的 BytesIO"""
    import fitz

    tmp_path = tempfile.mktemp(suffix=".pdf")
    try:
        # 保存上传文件到临时文件
        data = file_stream.read()
        with open(tmp_path, 'wb') as f:
            f.write(data)

        doc = fitz.open(tmp_path)
        total_pages = doc.page_count

        # 收集每页的保留区域
        page_keep_data = []

        for pi in range(total_pages):
            page = doc[pi]
            pw = page.rect.width
            ph = page.rect.height

            remove_regions, redact_rects, rewrite_items = _expedia_get_content_segments(page)

            # 应用 redactions
            for rect in redact_rects:
                page.add_redact_annot(rect.irect, fill=(1, 1, 1))
            page.apply_redactions()

            # 重写文字
            for item in rewrite_items:
                page.insert_text(
                    fitz.Point(item["x"], item["y"]),
                    item["text"],
                    fontname=_EXPEDIA_FONTNAME, fontsize=item["size"], color=_EXPEDIA_COLOR
                )

            keep_regions = _expedia_get_keep_regions(remove_regions, ph)
            keep_regions = [(s, e) for s, e in keep_regions if e - s > 5]
            page_keep_data.append((pi, keep_regions, pw, ph))

        # 保存 redact 后的临时文件
        tmp2_path = tmp_path + ".tmp"
        doc.save(tmp2_path)
        doc.close()

        # 重建为 A4 页面
        doc = fitz.open(tmp2_path)
        margin_lr = 50
        min_margin_tb = 60

        all_segments = []
        for pi, keep_regions, src_pw, src_ph in page_keep_data:
            for ys, ye in keep_regions:
                all_segments.append((pi, ys, ye, src_pw))

        total_content_h = sum(ye - ys for _, ys, ye, _ in all_segments)
        usable_h = _EXPEDIA_A4_H - 2 * min_margin_tb

        final_doc = fitz.open()

        if total_content_h <= usable_h:
            # 单页居中
            margin_top = max(min_margin_tb, (_EXPEDIA_A4_H - total_content_h) * 0.38)
            new_page = final_doc.new_page(width=_EXPEDIA_A4_W, height=_EXPEDIA_A4_H)
            dest_y = margin_top
            for pi, ys, ye, src_pw in all_segments:
                seg_h = ye - ys
                scale = (_EXPEDIA_A4_W - 2 * margin_lr) / (src_pw - 2 * margin_lr)
                if scale > 1:
                    scale = 1
                clip = fitz.Rect(0, ys, src_pw, ye)
                x_offset = (_EXPEDIA_A4_W - src_pw * scale) / 2
                dest = fitz.Rect(x_offset, dest_y, x_offset + src_pw * scale, dest_y + seg_h * scale)
                new_page.show_pdf_page(dest, doc, pi, clip=clip)
                dest_y += seg_h * scale
        else:
            # 多页分割
            margin_top = min_margin_tb
            dest_y = margin_top
            page_bottom = _EXPEDIA_A4_H - min_margin_tb
            new_page = final_doc.new_page(width=_EXPEDIA_A4_W, height=_EXPEDIA_A4_H)
            for pi, ys, ye, src_pw in all_segments:
                scale = (_EXPEDIA_A4_W - 2 * margin_lr) / (src_pw - 2 * margin_lr)
                if scale > 1:
                    scale = 1
                x_offset = (_EXPEDIA_A4_W - src_pw * scale) / 2
                remaining_seg_y = ys
                while remaining_seg_y < ye:
                    avail = page_bottom - dest_y
                    seg_remaining_h = ye - remaining_seg_y
                    place_h = min(seg_remaining_h, avail / scale)
                    if place_h < 5:
                        new_page = final_doc.new_page(width=_EXPEDIA_A4_W, height=_EXPEDIA_A4_H)
                        dest_y = margin_top
                        continue
                    clip = fitz.Rect(0, remaining_seg_y, src_pw, remaining_seg_y + place_h)
                    dest = fitz.Rect(x_offset, dest_y, x_offset + src_pw * scale, dest_y + place_h * scale)
                    new_page.show_pdf_page(dest, doc, pi, clip=clip)
                    dest_y += place_h * scale
                    remaining_seg_y += place_h
                    if remaining_seg_y < ye and dest_y >= page_bottom - 5:
                        new_page = final_doc.new_page(width=_EXPEDIA_A4_W, height=_EXPEDIA_A4_H)
                        dest_y = margin_top

        output = BytesIO()
        final_doc.save(output, deflate=True)
        final_doc.close()
        doc.close()
        output.seek(0)

        for p in [tmp_path, tmp2_path]:
            if os.path.exists(p):
                os.remove(p)

        return output
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        tmp2 = tmp_path + ".tmp"
        if os.path.exists(tmp2):
            os.remove(tmp2)
        raise


@flights_usbangla.route('/clean_expedia', methods=['POST'])
@login_required
@staff_only
def clean_expedia():
    """处理 Expedia 行程单：去除logo、价格、个人信息等"""
    file = request.files.get('pdf_file')
    if not file:
        return jsonify({'success': False, 'message': '请选择PDF文件'}), 400
    try:
        output = process_expedia_pdf(file.stream)
        original_name = file.filename or 'expedia_ticket.pdf'
        clean_name = original_name.rsplit('.', 1)[0] + '_clean.pdf'
        return send_file(output, download_name=clean_name, as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500


@flights_usbangla.route('/clean_qunar', methods=['POST'])
@login_required
@staff_only
def clean_qunar():
    """处理去哪儿行程单：去除logo、价格、订单号、代理信息等"""
    file = request.files.get('pdf_file')
    if not file:
        return jsonify({'success': False, 'message': '请选择PDF文件'}), 400
    try:
        baggage = request.form.get('baggage', '').strip()
        output = process_qunar_pdf(file.stream, baggage=baggage)
        original_name = file.filename or 'qunar_ticket.pdf'
        clean_name = original_name.rsplit('.', 1)[0] + '_clean.pdf'
        return send_file(output, download_name=clean_name, as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500


# ====================================================================
#  东方航空 (China Eastern, MU) 行程单生成
# ====================================================================


def parse_mu_pdf(file_stream):
    """解析东方航空 (MU) 邮件行程单 PDF，提取订单号、航班、乘客"""
    import fitz

    file_bytes = file_stream.read() if hasattr(file_stream, 'read') else file_stream
    doc = fitz.open(stream=file_bytes, filetype='pdf')
    text = ''
    for page in doc:
        t = page.get_text()
        if t:
            text += t + '\n'
    doc.close()

    flights = _mu_extract_flights(text)
    return {
        'order_no': _mu_extract_order_no(text),
        'flights': flights,
        # 向后兼容：保留单航段字段（取第一段）
        'flight': flights[0] if flights else _mu_empty_flight(),
        'passengers': _mu_extract_passengers(text),
    }


def _mu_extract_order_no(text):
    """从 'order No. is800426051127455782!' 提取订单号"""
    m = re.search(r'order\s*No\.?\s*is\s*(\d{10,})', text, re.IGNORECASE)
    return m.group(1) if m else ''


def _mu_extract_passengers(text):
    """乘客块在 'Passenger travel details' 与 'Order Detail' 之间，每位 5 行
    顺序：Ticket No / Passenger type / Passenger name / ID No / URL
    """
    m = re.search(r'Passenger travel details(.*?)Order Detail', text, re.DOTALL)
    if not m:
        return []
    block = m.group(1)
    lines = [ln.strip() for ln in block.split('\n') if ln.strip()]

    passengers = []
    i = 0
    while i < len(lines):
        # 票号锚点：781-xxxxxxxxxx
        if re.match(r'^\d{3}-\d{8,12}$', lines[i]):
            ticket = lines[i]
            pax_type = lines[i + 1] if i + 1 < len(lines) else ''
            name = lines[i + 2] if i + 2 < len(lines) else ''
            id_no = lines[i + 3] if i + 3 < len(lines) else ''
            if pax_type in ('Adult', 'Child', 'Infant') and '/' in name:
                passengers.append({
                    'name': name.upper(),
                    'pax_type': pax_type,
                    'id_no': id_no.upper(),
                    'ticket_no': ticket,
                })
            i += 5
        else:
            i += 1
    return passengers


def _mu_empty_flight():
    return {
        'flight_no': '', 'from_code': '', 'from_airport': '',
        'to_code': '', 'to_airport': '',
        'dep_date': '', 'dep_time': '', 'arr_date': '', 'arr_time': '',
        'cabin': '',
    }


def _mu_extract_flights(text):
    """提取所有航段（支持多段行程）

    订单明细区域内每个航段以航班号(MUxxxx)开头，按航班号将文本切块后逐段解析。
    """
    # 限定到订单明细区域：Order Detail ~ Total Amount，避免误匹配正文里的其它内容
    section = text
    m_start = re.search(r'Order Detail', section, re.IGNORECASE)
    if m_start:
        section = section[m_start.end():]
    m_end = re.search(r'Total\s*Amount', section, re.IGNORECASE)
    if m_end:
        section = section[:m_end.start()]

    # 找到所有航班号位置，相邻航班号之间即为一个航段块
    matches = list(re.finditer(r'\b(MU\d{2,4})\b', section))
    flights = []
    for idx, mt in enumerate(matches):
        start = mt.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section)
        flights.append(_mu_parse_flight_block(section[start:end], mt.group(1)))
    return flights


def _mu_parse_flight_block(block, flight_no):
    """解析单个航段块：起降城市、起降时间、舱位"""
    flight = _mu_empty_flight()
    flight['flight_no'] = flight_no

    # 出发/到达日期+时间（在邮件 PDF 中两者分行）
    dt = re.findall(r'(\d{4}-\d{1,2}-\d{1,2})\s*\n?\s*(\d{1,2}:\d{2})', block)
    if len(dt) >= 2:
        flight['dep_date'], flight['dep_time'] = dt[0]
        flight['arr_date'], flight['arr_time'] = dt[1]

    # 机场代码：紧跟两个 3-letter 大写代码 + (...)
    codes = re.findall(r'\b([A-Z]{3})\b\s*\n?\s*\(', block)
    if len(codes) >= 2:
        flight['from_code'] = codes[0]
        flight['to_code'] = codes[1]

    # 机场名（括号内，可能跨行）
    parens = re.findall(r'\(([^)]+)\)', block, re.DOTALL)
    if len(parens) >= 2:
        flight['from_airport'] = re.sub(r'\s+', ' ', parens[0]).strip()
        flight['to_airport'] = re.sub(r'\s+', ' ', parens[1]).strip()

    # 舱位："Economy\nClass S" 或 "Economy Class S"
    m = re.search(r'(Economy|Business|First|Premium\s*Economy)\s*\n?\s*Class\s+([A-Z])',
                  block, re.IGNORECASE)
    if m:
        cabin_name = re.sub(r'\s+', ' ', m.group(1)).strip().title()
        flight['cabin'] = f"{cabin_name} ({m.group(2)})"

    return flight


_MU_FONTS_REGISTERED = False


def _register_mu_fonts():
    """注册微软雅黑字体；失败则回退到 Helvetica"""
    global _MU_FONTS_REGISTERED
    if _MU_FONTS_REGISTERED:
        return True
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        msyh = r"C:\Windows\Fonts\msyh.ttc"
        msyhbd = r"C:\Windows\Fonts\msyhbd.ttc"
        if os.path.exists(msyh) and os.path.exists(msyhbd):
            pdfmetrics.registerFont(TTFont("MSYH", msyh))
            pdfmetrics.registerFont(TTFont("MSYHBD", msyhbd))
            _MU_FONTS_REGISTERED = True
            return True
    except Exception:
        pass
    return False


def generate_mu_itinerary(data, logo_path):
    """生成东方航空行程单 PDF（参考 itinerary_MU.py），返回 bytes

    data 结构：
      order_no,
      flights: [{flight_no, from_code, from_airport, from_terminal,
                 to_code, to_airport, to_terminal, dep_date, dep_time,
                 arr_date, arr_time, cabin}, ...],  # 支持多航段
      passengers: [{name, pax_type, id_no, ticket_no}, ...],
      notices: [str, ...]
    兼容旧格式：缺少 flights 时回退到顶层单航段字段。
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    )
    from PIL import Image as PILImage

    has_msyh = _register_mu_fonts()
    font_regular = "MSYH" if has_msyh else "Helvetica"
    font_bold = "MSYHBD" if has_msyh else "Helvetica-Bold"

    output = BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"{data.get('flight_no', 'MU')} Itinerary",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Title"],
        fontName=font_bold, fontSize=22, leading=28,
        textColor=colors.HexColor("#B8002E"),
        alignment=0, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontName=font_regular, fontSize=10, leading=14,
        textColor=colors.HexColor("#666666"), spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "h2", parent=styles["Heading2"],
        fontName=font_bold, fontSize=13, leading=18,
        textColor=colors.HexColor("#222222"),
        spaceBefore=12, spaceAfter=6,
    )
    note_style = ParagraphStyle(
        "note", parent=styles["Normal"],
        fontName=font_regular, fontSize=10, leading=16,
        textColor=colors.HexColor("#333333"),
    )

    story = []

    # 头部：logo + 标题
    has_logo = logo_path and os.path.exists(logo_path)
    if has_logo:
        pil = PILImage.open(logo_path)
        logo_h = 14 * mm
        logo_w = logo_h * pil.width / pil.height
        logo_img = Image(logo_path, width=logo_w, height=logo_h)
    else:
        logo_w = 0
        logo_img = Paragraph("", note_style)

    order_no = data.get('order_no', '')
    sub_text = "China Eastern Airlines"
    if order_no:
        sub_text += f" &nbsp;|&nbsp; Order No. {order_no}"

    header_text = [
        [Paragraph("Flight Itinerary", title_style)],
        [Paragraph(sub_text, sub_style)],
    ]
    header_text_tbl = Table(header_text, colWidths=[120 * mm])
    header_text_tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    if has_logo:
        header = Table(
            [[logo_img, header_text_tbl]],
            colWidths=[logo_w + 6 * mm, 170 * mm - logo_w - 6 * mm],
        )
    else:
        header = Table([[header_text_tbl]], colWidths=[170 * mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header)
    story.append(Spacer(1, 4 * mm))

    # === Flight Information ===
    story.append(Paragraph("Flight Information", h2_style))

    def _compose_endpoint(code, airport, terminal):
        parts = [p for p in [code, airport] if p]
        text = "  ·  ".join(parts)
        if terminal:
            text += f"  ·  Terminal {terminal}"
        return text

    def _compose_datetime(d, t):
        return f"{d}  {t}".strip()

    def _build_flight_table(seg):
        """根据单个航段数据构建航班信息表格"""
        flight_rows = [
            ["Flight No.", seg.get('flight_no', '')],
            ["From", _compose_endpoint(seg.get('from_code', ''), seg.get('from_airport', ''), seg.get('from_terminal', ''))],
            ["To", _compose_endpoint(seg.get('to_code', ''), seg.get('to_airport', ''), seg.get('to_terminal', ''))],
            ["Departure", _compose_datetime(seg.get('dep_date', ''), seg.get('dep_time', ''))],
            ["Arrival", _compose_datetime(seg.get('arr_date', ''), seg.get('arr_time', ''))],
            ["Class", seg.get('cabin', '')],
        ]
        tbl = Table(flight_rows, colWidths=[32 * mm, 138 * mm])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_regular),
            ("FONTNAME", (0, 0), (0, -1), font_bold),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F5F7")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ]))
        return tbl

    # 多航段：优先使用 flights 列表；为兼容旧数据，缺省时回退到顶层单航段字段
    flights = data.get('flights') or []
    if not flights:
        flights = [data]

    seg_label_style = ParagraphStyle(
        "seglabel", parent=styles["Normal"],
        fontName=font_bold, fontSize=11, leading=15,
        textColor=colors.HexColor("#B8002E"),
        spaceBefore=8, spaceAfter=4,
    )
    multi = len(flights) > 1
    for i, seg in enumerate(flights, 1):
        if multi:
            story.append(Paragraph(f"Flight {i}", seg_label_style))
        story.append(_build_flight_table(seg))

    # === Passenger Information ===
    passengers = data.get('passengers', []) or []
    story.append(Paragraph(f"Passenger Information ({len(passengers)} passenger{'s' if len(passengers) != 1 else ''})", h2_style))

    pax_header = ["#", "Name", "Type", "ID No.", "Ticket No."]
    pax_rows = [pax_header]
    for i, p in enumerate(passengers, 1):
        pax_rows.append([
            str(i),
            p.get('name', ''),
            p.get('pax_type', 'Adult'),
            p.get('id_no', ''),
            p.get('ticket_no', ''),
        ])
    pax_tbl = Table(pax_rows, colWidths=[10 * mm, 42 * mm, 18 * mm, 42 * mm, 58 * mm])
    pax_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_regular),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTSIZE", (0, 0), (-1, -1), 10.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B8002E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#FAFAFA")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
    ]))
    story.append(pax_tbl)

    # === Notice ===
    notices = [n for n in (data.get('notices') or []) if n and n.strip()]
    if notices:
        story.append(Paragraph("Notice", h2_style))
        for t in notices:
            story.append(Paragraph(f"• {t}", note_style))

    doc.build(story)
    return output.getvalue()


@flights_usbangla.route('/parse_mu_pdf', methods=['POST'])
@login_required
@staff_only
def parse_mu_pdf_route():
    """上传东方航空邮件行程单 PDF，解析出订单号、航班、乘客"""
    file = request.files.get('pdf_file')
    if not file:
        return jsonify({'success': False, 'message': '请选择PDF文件'}), 400
    try:
        result = parse_mu_pdf(file.stream)
        return jsonify({
            'success': True,
            'order_no': result['order_no'],
            'flights': result['flights'],
            'flight': result['flight'],  # 向后兼容
            'passengers': result['passengers'],
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'PDF解析失败：{str(e)}'}), 500


@flights_usbangla.route('/generate_mu_itinerary', methods=['POST'])
@login_required
@staff_only
def generate_mu_itinerary_route():
    """根据表单数据生成东方航空行程单 PDF"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    passengers = data.get('passengers', []) or []
    if not passengers:
        return jsonify({'success': False, 'message': '请至少添加一位乘客'}), 400
    # 多航段：flights 列表至少有一段含航班号；兼容旧的顶层 flight_no
    flights = data.get('flights') or []
    first_flight_no = (flights[0].get('flight_no') if flights else '') or data.get('flight_no')
    if not first_flight_no:
        return jsonify({'success': False, 'message': '请填写航班号'}), 400

    try:
        pdf_bytes = generate_mu_itinerary(data, MU_LOGO_PATH)
        flight_no = (first_flight_no or 'MU').upper().replace(' ', '')
        order_no = (data.get('order_no') or '').strip()
        filename = f"Itinerary_{flight_no}"
        if order_no:
            filename += f"_{order_no}"
        filename += ".pdf"
        return send_file(BytesIO(pdf_bytes), download_name=filename,
                         as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'message': f'生成失败：{str(e)}'}), 500
