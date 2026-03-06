# -*- coding: utf-8 -*-
"""US-Bangla Airlines 机票PDF工具：上传原始合票PDF → 解析 → 生成单人PDF（支持多航段往返）"""

from flask import Blueprint, render_template, request, send_file, jsonify
from flask_login import login_required
from App_new.utils.decorators import staff_only
from io import BytesIO
import os
import re

flights_usbangla = Blueprint('flights_usbangla', __name__, url_prefix='/flights_usbangla')

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'static', 'images', 'airlines', 'us_bangla_logo.png'
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

def _create_ticket_pdf_class():
    from fpdf import FPDF

    class TicketPDF(FPDF):
        def __init__(self, booking_ref, logo_path):
            super().__init__()
            self.booking_ref = booking_ref
            self.logo_path = logo_path

        def header(self):
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


def generate_single_ticket(pax, flight_data, logo_path):
    """生成单个乘客的机票 PDF（支持多航段），返回 bytes"""
    TicketPDF = _create_ticket_pdf_class()
    booking_ref = flight_data.get('booking_ref', '')
    segments = flight_data.get('segments', [])

    pdf = TicketPDF(booking_ref, logo_path)
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
    it_widths = [18, 18, 35, 30, 28, 28, 20, 15]
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
    bg_widths = [50, 60, 50]
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
        result = parse_usbangla_pdf(file.stream)
        return jsonify({
            'success': True,
            'booking_ref': result['booking_ref'],
            'segments': result['segments'],
            'passengers': result['passengers'],
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

    if len(passengers) == 1:
        pax = passengers[0]
        pdf_bytes = generate_single_ticket(pax, flight_data, LOGO_PATH)
        output = BytesIO(pdf_bytes)
        safe_name = pax['name'].replace(' ', '_')
        filename = f"E-ticket_{booking_ref}_{safe_name}.pdf"
        return send_file(output, download_name=filename, as_attachment=True, mimetype='application/pdf')
    else:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for pax in passengers:
                pdf_bytes = generate_single_ticket(pax, flight_data, LOGO_PATH)
                safe_name = pax['name'].replace(' ', '_')
                filename = f"E-ticket_{booking_ref}_{safe_name}.pdf"
                zf.writestr(filename, pdf_bytes)
        zip_buffer.seek(0)
        zip_filename = f"E-tickets_{booking_ref}.zip"
        return send_file(zip_buffer, download_name=zip_filename, as_attachment=True, mimetype='application/zip')
