# -*- coding: utf-8 -*-
"""
图片OCR航班信息提取（轻量版）

依赖：
- pytesseract、Pillow（如未安装或未配置Tesseract，将优雅降级并返回提示）

输出字段：
- schedule_city: "SIN PVG"
- schedule_timing: "HHMM HHMM"
- departure_terminal / departure_gate
- arrival_terminal / arrival_gate
- aircraft, status
"""

from typing import Dict, Optional
import re


def _to_hhmm(t: str) -> str:
    try:
        h, m = t.split(":")
        h = h.zfill(2)
        return f"{h}{m}"
    except Exception:
        return "Unknown"


def _first_or_unknown(items):
    return items[0] if items else "Unknown"


def extract_flight_info_from_text(text: str) -> Dict[str, str]:
    """从纯文本中用正则解析航班核心信息。"""
    result = {
        "schedule_city": "Unknown",
        "schedule_timing": "Unknown Unknown",
        "departure_terminal": "Unknown",
        "departure_gate": "Unknown",
        "arrival_terminal": "Unknown",
        "arrival_gate": "Unknown",
        "aircraft": "Unknown",
        "status": "Unknown",
    }

    # 时间：取前两处 HH:MM，分别作为起飞/到达
    times = re.findall(r"\b(\d{1,2}:\d{2})\b", text)
    if times:
        dep_t = _to_hhmm(times[0])
        arr_t = _to_hhmm(times[-1]) if len(times) > 1 else "Unknown"
        result["schedule_timing"] = f"{dep_t} {arr_t}"

    # IATA：取前两个不同的3位大写字母
    iatas = re.findall(r"\b([A-Z]{3})\b", text)
    uniq = []
    for code in iatas:
        if code not in uniq:
            uniq.append(code)
        if len(uniq) >= 2:
            break
    if len(uniq) >= 2:
        result["schedule_city"] = f"{uniq[0]} {uniq[1]}"

    # 航站楼：T\d 或 Terminal X
    terminals = re.findall(r"Terminal\s*([A-Z0-9]+)|\bT(\d+)\b|航站楼\s*([A-Z0-9]+)", text, flags=re.IGNORECASE)
    flat_terms = []
    for a, b, c in terminals:
        v = a or b or c
        if v:
            flat_terms.append(v)
    if flat_terms:
        result["departure_terminal"] = flat_terms[0]
    if len(flat_terms) > 1:
        result["arrival_terminal"] = flat_terms[1]

    # 登机口：Gate X 或 字母数字
    gates = re.findall(r"Gate\s*([A-Z0-9]+)|\b([A-Z])\d+\b|登机口\s*([A-Z0-9]+)", text, flags=re.IGNORECASE)
    flat_gates = []
    for a, b, c in gates:
        v = a or b or c
        if v:
            flat_gates.append(v)
    if flat_gates:
        result["departure_gate"] = flat_gates[0]
    if len(flat_gates) > 1:
        result["arrival_gate"] = flat_gates[1]

    # 机型：Boeing XXX / Airbus XXX / 77W 等
    ac = re.search(r"(Boeing\s*\d{3}|Airbus\s*A?\d{3}|\b\d{2}[A-Z]\b|\b7\d{2}\b)", text, flags=re.IGNORECASE)
    if ac:
        result["aircraft"] = ac.group(1)

    # 状态关键词
    st = re.search(r"(On\s*Time|Delayed|Expected|Landed|Cancelled)", text, flags=re.IGNORECASE)
    if st:
        result["status"] = st.group(1).title()

    return result


def extract_flight_info_from_image(file_storage) -> Dict[str, str]:
    """从图片流中做 OCR 并解析航班信息。返回字段见上。"""
    try:
        # 延迟导入，避免环境无依赖时报错
        from PIL import Image
        import pytesseract

        # 测试Tesseract是否可用
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            return {"success": False, "message": "OCR引擎未安装，请安装Tesseract OCR", "data": None}

        image = Image.open(file_storage.stream).convert("RGB")
        ocr_text = pytesseract.image_to_string(image, lang="eng+chi_sim")
        if not ocr_text:
            return {"success": False, "message": "OCR未识别到文本", "data": None}

        data = extract_flight_info_from_text(ocr_text)
        return {"success": True, "message": "OK", "data": data}
    except Exception as e:
        # 未安装 tesseract 或依赖缺失
        return {"success": False, "message": f"OCR不可用: {e}", "data": None}


