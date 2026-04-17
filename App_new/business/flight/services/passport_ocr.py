# -*- coding: utf-8 -*-
"""护照 MRZ OCR 服务

封装 passporteye + Tesseract 识别逻辑。基于用户提供的 extract_passport.py 改造，
去掉 Windows 硬编码路径、改为环境变量驱动；只对外暴露 extract_from_path() 一个函数。

依赖（服务器需安装）:
    apt install tesseract-ocr libgl1
    pip install passporteye pytesseract Pillow
"""

import os
import re
import sys
import shutil
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)


def _detect_tesseract() -> str:
    """按以下优先级查找 tesseract 可执行文件:
    1. TESSERACT_PATH / TESSERACT_CMD 环境变量
    2. 系统 PATH (shutil.which)
    3. Windows 常见安装位置
    4. Linux/Mac 常见安装位置
    返回找到的路径，找不到返回空串。
    """
    env_path = os.environ.get('TESSERACT_PATH') or os.environ.get('TESSERACT_CMD')
    if env_path and Path(env_path).exists():
        return env_path

    auto = shutil.which('tesseract') or shutil.which('tesseract.exe')
    if auto:
        return auto

    candidates = []
    if sys.platform == 'win32':
        candidates += [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            os.path.expandvars(r'%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe'),
        ]
    else:
        candidates += [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',
        ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return ''


_TESS_PATH = _detect_tesseract()
if _TESS_PATH:
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = _TESS_PATH
    except ImportError:
        pass


_MONTHS = {
    "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR",
    "05": "MAY", "06": "JUN", "07": "JUL", "08": "AUG",
    "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC",
}


def _format_date(raw: str) -> str:
    """YYMMDD → '19 NOV 1998'。识别失败时原样返回。"""
    if not raw or not re.match(r"^\d{6}$", raw):
        return raw or ""
    yy, mm, dd = int(raw[0:2]), raw[2:4], raw[4:6]
    # 出生年份分界：>40 视作 19xx，否则 20xx
    year = 1900 + yy if yy > 40 else 2000 + yy
    return f"{dd} {_MONTHS.get(mm, mm)} {year}"


def _extract_names_from_mrz(raw_text: str) -> tuple:
    """从 MRZ 第一行提取姓/名，修正 OCR 把 < 误读成 K 的常见噪声。

    策略:
    - 名字区固定从第 6 字符开始（位置 5+）
    - 在 [<K] 字符的连续序列里找"分隔符"和"填充段"
    - 第一个 [<K]{2,} 视为姓-名分隔符 <<
    - 之后第一个 [<K]{2,} 视为名字结束，后面都是填充
    - 残留单个 K：仅当两侧都是 < 时才视为 < （否则保留为真字母）
    """
    lines = raw_text.strip().split("\n")
    if not lines:
        return "", ""

    line1 = lines[0].strip()
    if len(line1) < 6:
        return "", ""

    name_area = line1[5:]

    def _resolve_k(s: str) -> str:
        """把仅在 < 包围下的 K 还原为 <，迭代到稳定为止"""
        chars = list(s)
        for _ in range(3):
            changed = False
            n = len(chars)
            for i in range(n):
                if chars[i] != 'K':
                    continue
                left = chars[i - 1] if i > 0 else '<'
                right = chars[i + 1] if i < n - 1 else '<'
                if left == '<' and right == '<':
                    chars[i] = '<'
                    changed = True
            if not changed:
                break
        return ''.join(chars)

    # 第 1 步：找姓-名分隔符（最左侧的 [<K]{2,}）
    sep_re = re.compile(r'[<K]{2,}')
    sep = sep_re.search(name_area)
    if not sep:
        # 没有分隔符，整段视为姓
        return name_area.replace('<', ' ').replace('K', ' ').strip(), ''

    surname_raw = name_area[:sep.start()]
    rest = name_area[sep.end():]

    # 第 2 步：在 rest 里找名字结束（再来一个 [<K]{2,} → 后面都是填充）
    end = sep_re.search(rest)
    if end:
        given_raw = rest[:end.start()]
    else:
        given_raw = rest.rstrip('<K')

    # 第 3 步：清理姓 / 名内残留的 K（仅 << 之间的 K 还原为 <）
    surname_clean = _resolve_k(surname_raw)
    given_clean = _resolve_k(given_raw)

    surname = surname_clean.replace('<', ' ').strip()
    given_name = given_clean.replace('<', ' ').strip()
    return surname, given_name


def extract_from_path(image_path: str) -> dict:
    """从图片文件提取护照信息。

    返回:
        成功: {'success': True, 'data': {字段...}}
        失败: {'success': False, 'error': '错误说明'}
    """
    try:
        from passporteye import read_mrz
    except ImportError:
        return {
            'success': False,
            'error': '服务器未安装 passporteye，请联系管理员安装：pip install passporteye pytesseract'
        }

    if not Path(image_path).exists():
        return {'success': False, 'error': f'图片文件不存在: {image_path}'}

    try:
        mrz = read_mrz(image_path)
    except Exception as e:
        return {'success': False, 'error': f'OCR 处理失败: {e}'}

    if mrz is None:
        return {
            'success': False,
            'error': '未检测到护照 MRZ 区域，请确认图片清晰、包含护照底部两行机读码'
        }

    d = mrz.to_dict()
    raw_text = d.get('raw_text', '')

    surname, given_name = _extract_names_from_mrz(raw_text)
    if not surname:
        surname = d.get('surname', '')
    if not given_name:
        given_name = (d.get('names', '') or '').strip()

    return {
        'success': True,
        'data': {
            'document_type': (d.get('type') or '').replace('<', '').strip(),
            'country_code': d.get('country', ''),
            'passport_number': d.get('number', ''),
            'surname': surname,
            'given_name': given_name,
            'nationality': d.get('nationality', ''),
            'date_of_birth': _format_date(d.get('date_of_birth', '')),
            'sex': d.get('sex', ''),
            'expiration_date': _format_date(d.get('expiration_date', '')),
            'personal_number': (d.get('personal_number') or '').replace('<', '').strip(),
            'mrz_raw': raw_text,
            'valid_score': d.get('valid_score', 0),
        }
    }
