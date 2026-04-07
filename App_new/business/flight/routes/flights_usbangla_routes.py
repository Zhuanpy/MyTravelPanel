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
    """去除票价 FARE、税款 TAX、付款方式 FORM OF PAYMENT 行"""
    import fitz
    pw = page.rect.width
    gaps = []

    for keyword in ["FARE:", "FARE："]:
        for r in page.search_for(keyword):
            page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw * 0.5, r.y1 + 2), fill=(1, 1, 1))
            gaps.append((r.y0 - 2, r.y1 + 2))

    for keyword in ["TAX:", "TAX："]:
        for r in page.search_for(keyword):
            page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw - 30, r.y1 + 2), fill=(1, 1, 1))
            gaps.append((r.y0 - 2, r.y1 + 2))

    for r in page.search_for("FORM OF PAYMENT"):
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
    """去除 AGENCY ADDRESS、IATA CODE、TEL 行"""
    import fitz
    pw = page.rect.width
    gaps = []
    for keyword in ["AGENCY ADDRESS", "IATA CODE"]:
        for r in page.search_for(keyword):
            page.add_redact_annot(fitz.Rect(r.x0 - 2, r.y0 - 2, pw - 30, r.y1 + 2), fill=(1, 1, 1))
            gaps.append((r.y0 - 2, r.y1 + 2))
    for r in page.search_for("TEL"):
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


def process_qunar_pdf(file_stream):
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


@flights_usbangla.route('/clean_qunar', methods=['POST'])
@login_required
@staff_only
def clean_qunar():
    """处理去哪儿行程单：去除logo、价格、订单号、代理信息等"""
    file = request.files.get('pdf_file')
    if not file:
        return jsonify({'success': False, 'message': '请选择PDF文件'}), 400
    try:
        output = process_qunar_pdf(file.stream)
        original_name = file.filename or 'qunar_ticket.pdf'
        clean_name = original_name.rsplit('.', 1)[0] + '_clean.pdf'
        return send_file(output, download_name=clean_name, as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500
