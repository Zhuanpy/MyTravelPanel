# -*- coding: utf-8 -*-
"""护照识别路由：上传图片 → MRZ OCR → 编辑确认 → 写入常用旅客表

注意: 不再单独建表。识别结果直接落入 frequent_travelers (FrequentTraveler)，
与现有"常用旅客"管理打通，方便订票/项目时复用。
"""

import os
import re
import tempfile
import uuid
from pathlib import Path
from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, or_
from werkzeug.utils import secure_filename

from App_new.utils.decorators import staff_only
from App_new.exts import db, csrf
from App_new.business.projects.models.frequent_traveler import FrequentTraveler
from App_new.business.projects.models.traveler_file import TravelerFile
from App_new.business.projects.models.project import CustomerCompany
from ..services.passport_ocr import extract_from_path

flights_passport = Blueprint('flights_passport', __name__, url_prefix='/flights_passport')

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'tif'}
MAX_BYTES = 10 * 1024 * 1024

# OCR 输出 vs FrequentTraveler 字段映射
_MONTH_MAP = {
    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
}
_SEX_MAP = {'M': 'male', 'F': 'female'}


def _infer_title(gender, dob):
    """按性别(+出生日期判成人/儿童)推断称谓 MR/MS/MISS/MASTER

    航旅惯例：12 岁以下为儿童 → 男 MASTER / 女 MISS；成人 → 男 MR / 女 MS。
    无法判断性别时返回 None。
    """
    if gender not in ('male', 'female'):
        return None
    is_child = False
    if dob:
        try:
            today = datetime.utcnow().date()
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day))
            is_child = age < 12
        except (AttributeError, TypeError):
            is_child = False
    if gender == 'female':
        return 'MISS' if is_child else 'MS'
    return 'MASTER' if is_child else 'MR'


def _allowed(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def _parse_date(s: str):
    """'19 NOV 1998' / 'YYYY-MM-DD' → date 对象，失败返回 None"""
    if not s:
        return None
    s = s.strip()
    m = re.match(r'^(\d{1,2})\s+([A-Z]{3})\s+(\d{4})$', s, re.IGNORECASE)
    if m:
        d, mon, y = int(m.group(1)), m.group(2).upper(), int(m.group(3))
        if mon in _MONTH_MAP:
            try:
                return date(y, _MONTH_MAP[mon], d)
            except ValueError:
                return None
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _format_date(d):
    """date → 'DD MON YYYY' 显示用"""
    if not d:
        return ''
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    return f'{d.day:02d} {months[d.month - 1]} {d.year}'


def _traveler_to_passport_dict(t: FrequentTraveler) -> dict:
    """把 FrequentTraveler 渲染成"近期保存"列表里需要的字段"""
    name_en = (t.name_en or '').strip()
    if '/' in name_en:
        surname, given_name = name_en.split('/', 1)
        surname, given_name = surname.strip(), given_name.strip()
    elif ' ' in name_en:
        parts = name_en.split(' ', 1)
        surname, given_name = parts[0].strip(), parts[1].strip()
    else:
        surname, given_name = name_en, ''
    sex_short = ''
    if t.gender == 'male':
        sex_short = 'M'
    elif t.gender == 'female':
        sex_short = 'F'
    return {
        'id': t.id,
        'traveler_code': t.traveler_code,
        'is_frequent': True,
        'surname': surname,
        'given_name': given_name,
        'name': t.name or '',
        'name_en': name_en,
        'sex': sex_short,
        'date_of_birth': _format_date(t.date_of_birth),
        'nationality': t.nationality or '',
        'country_code': t.passport_issuing_country or '',
        'passport_number': t.passport_number or '',
        'expiration_date': _format_date(t.passport_expiry_date),
        'group_name': t.group_name or '',
        'updated_at': t.updated_at.strftime('%Y-%m-%d %H:%M') if t.updated_at else '',
    }


@flights_passport.route('/extract')
@login_required
@staff_only
def extract_page():
    """护照识别页面"""
    _per_page = 20
    _pag = (FrequentTraveler.query
            .filter(FrequentTraveler.passport_number.isnot(None),
                    FrequentTraveler.passport_number != '')
            .order_by(desc(FrequentTraveler.updated_at))
            .paginate(page=1, per_page=_per_page, error_out=False))
    recent = _pag.items

    # 集团下拉：CustomerCompany.group_name + FrequentTraveler.group_name 的去重并集
    company_groups = {g[0] for g in db.session.query(CustomerCompany.group_name)
                      .filter(CustomerCompany.group_name.isnot(None),
                              CustomerCompany.group_name != '').distinct().all()}
    traveler_groups = {g[0] for g in db.session.query(FrequentTraveler.group_name)
                       .filter(FrequentTraveler.group_name.isnot(None),
                               FrequentTraveler.group_name != '').distinct().all()}
    groups = sorted(company_groups | traveler_groups)

    return render_template('business/flight/passport_extract.html',
                           recent_list=[_traveler_to_passport_dict(t) for t in recent],
                           recent_total=_pag.total,
                           recent_pages=_pag.pages,
                           recent_per_page=_per_page,
                           groups=groups)


@flights_passport.route('/ocr', methods=['POST'])
@login_required
@staff_only
def ocr():
    """图片 → MRZ → JSON，不入库"""
    file = request.files.get('image')
    if not file or not file.filename:
        return jsonify({'success': False, 'error': '请上传护照图片'}), 400
    if not _allowed(file.filename):
        return jsonify({'success': False, 'error': '图片格式不支持，请用 PNG/JPG/JPEG/WEBP'}), 400

    suffix = '.' + file.filename.rsplit('.', 1)[1].lower()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        file.save(tmp.name)
        tmp.close()
        size = os.path.getsize(tmp.name)
        if size > MAX_BYTES:
            return jsonify({'success': False, 'error': f'图片过大 ({size//1024} KB)，请压缩到 10 MB 以内'}), 400
        result = extract_from_path(tmp.name)
        return jsonify(result), (200 if result.get('success') else 422)
    except Exception as e:
        current_app.logger.exception('护照 OCR 失败')
        return jsonify({'success': False, 'error': f'服务异常: {e}'}), 500
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


class DuplicateNeedsResolution(Exception):
    """同名但无护照号的疑似重复旅客，需用户确认合并/新建"""
    def __init__(self, candidates):
        self.candidates = candidates
        super().__init__('duplicate needs resolution')


def _apply_passport_fields(rec, *, name_en, gender, title, dob, nationality,
                           issuing_country, expiry, cn_name, group_name,
                           passport_number=None):
    """把护照字段写入旅客记录（passport_match 更新 与 合并 共用）"""
    rec.name_en = name_en
    if gender:
        rec.gender = gender
    # 称谓为空才补，避免覆盖人工已设的称谓
    if title and not (rec.title or '').strip():
        rec.title = title
    if dob:
        rec.date_of_birth = dob
    if nationality:
        rec.nationality = nationality
    if issuing_country:
        rec.passport_issuing_country = issuing_country
    if expiry:
        rec.passport_expiry_date = expiry
    if cn_name:
        rec.name = cn_name
    if group_name:
        rec.group_name = group_name
    if passport_number:
        rec.passport_number = passport_number
    rec.updated_at = datetime.utcnow()


def _find_name_dup_candidates(name_en, cn_name):
    """无护照号、姓名疑似相同的常用旅客（可能是同一人但未存护照）"""
    from sqlalchemy import func
    no_passport = db.or_(FrequentTraveler.passport_number.is_(None),
                          FrequentTraveler.passport_number == '')
    name_conds = [
        func.upper(func.trim(FrequentTraveler.name_en)) == name_en,
        func.upper(func.trim(FrequentTraveler.name)) == name_en,
    ]
    if cn_name:
        name_conds.append(FrequentTraveler.name == cn_name)
    return (FrequentTraveler.query
            .filter(no_passport, db.or_(*name_conds))
            .limit(5).all())


def _upsert_traveler_from_passport(data):
    """根据前端传来的护照字段 find-or-create FrequentTraveler

    去重策略：
      1. 护照号已存在 → 更新该条 (action='updated')
      2. data.merge_into_id → 合并护照信息到指定旅客 (action='merged')
      3. 未 force_create 且发现同名无护照的疑似重复 → 抛
         DuplicateNeedsResolution，交前端让用户选合并/新建
      4. 否则新建 (action='created')

    失败时抛 ValueError（调用方负责转成 400 响应）
    """
    surname = (data.get('surname') or '').strip().upper()
    given_name = (data.get('given_name') or '').strip().upper()
    passport_number = (data.get('passport_number') or '').strip().upper()
    nationality = (data.get('nationality') or '').strip().upper()

    if not (surname and given_name and passport_number):
        raise ValueError('姓 / 名 / 护照号 不能为空')

    name_en = f'{surname} {given_name}'
    sex_raw = (data.get('sex') or '').strip().upper()[:1]
    gender = _SEX_MAP.get(sex_raw)
    dob = _parse_date(data.get('date_of_birth') or '')
    # 称谓：优先前端显式传入，否则按性别(+生日)推断
    title = (data.get('title') or '').strip().upper() or _infer_title(gender, dob)
    expiry = _parse_date(data.get('expiration_date') or '')
    issuing_country = (data.get('country_code') or '').strip().upper()
    cn_name = (data.get('name') or '').strip()
    group_name = (data.get('group_name') or '').strip() or None

    fields = dict(name_en=name_en, gender=gender, title=title, dob=dob,
                  nationality=nationality, issuing_country=issuing_country,
                  expiry=expiry, cn_name=cn_name, group_name=group_name)

    # 1) 护照号已存在 → 更新该条
    existing = FrequentTraveler.query.filter_by(passport_number=passport_number).first()
    if existing:
        _apply_passport_fields(existing, **fields)
        return existing, 'updated'

    # 2) 用户已确认合并到某条
    merge_id = data.get('merge_into_id')
    if merge_id:
        rec = FrequentTraveler.query.get(int(merge_id))
        if not rec:
            raise ValueError('要合并的旅客不存在')
        _apply_passport_fields(rec, passport_number=passport_number, **fields)
        return rec, 'merged'

    # 3) 未强制新建 → 检测同名无护照疑似重复，交用户决定
    if not data.get('force_create'):
        candidates = _find_name_dup_candidates(name_en, cn_name)
        if candidates:
            raise DuplicateNeedsResolution([{
                'id': t.id,
                'traveler_code': t.traveler_code,
                'title': t.title,
                'name': t.name,
                'name_en': t.name_en,
                'phone': t.phone,
                'company_name': t.company.company_name if t.company else None,
            } for t in candidates])

    # 4) 新建
    record = FrequentTraveler(
        name=cn_name or name_en,
        name_en=name_en,
        title=title,
        gender=gender,
        date_of_birth=dob,
        nationality=nationality or None,
        passport_number=passport_number,
        passport_issuing_country=issuing_country or None,
        passport_expiry_date=expiry,
        group_name=group_name,
    )
    db.session.add(record)
    return record, 'created'


def _get_traveler_files_dir(traveler_id):
    """返回旅客的文件存储目录（与 frequent_traveler 路由保持一致）"""
    base = Path(os.getcwd()) / '资源' / 'Travelers' / str(traveler_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


@flights_passport.route('/save', methods=['POST'])
@login_required
@staff_only
def save():
    """写入或更新 FrequentTraveler。去重 key: passport_number。"""
    data = request.get_json() or {}
    try:
        record, action = _upsert_traveler_from_passport(data)
        db.session.commit()
        return jsonify({
            'success': True,
            'action': action,
            'data': _traveler_to_passport_dict(record),
        })
    except DuplicateNeedsResolution as d:
        db.session.rollback()
        return jsonify({
            'success': False,
            'need_resolution': True,
            'candidates': d.candidates,
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('护照保存到 FrequentTraveler 失败')
        return jsonify({'success': False, 'error': f'保存失败: {e}'}), 500


@flights_passport.route('/save_image', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def save_image():
    """保存护照图片到 TravelerFile

    前端 multipart/form-data：
    - image: 图片文件（必填）
    - surname / given_name / passport_number 等：与 /save 同格式，用来 find-or-create 旅客
    """
    file = request.files.get('image')
    if not file or not file.filename:
        return jsonify({'success': False, 'error': '请上传护照图片'}), 400
    if not _allowed(file.filename):
        return jsonify({'success': False, 'error': '图片格式不支持，请用 PNG/JPG/JPEG/WEBP'}), 400

    # 用表单里的护照字段 find-or-create 旅客
    try:
        record, action = _upsert_traveler_from_passport(request.form)
        db.session.flush()  # 新建时拿到 traveler.id
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('保存图片前置旅客 upsert 失败')
        return jsonify({'success': False, 'error': f'保存失败: {e}'}), 500

    # 保存文件 + 写 TravelerFile
    try:
        original = secure_filename(file.filename) or file.filename
        ext = os.path.splitext(original)[1].lower() or '.jpg'
        stored = f'{uuid.uuid4().hex}{ext}'
        file_dir = _get_traveler_files_dir(record.id)
        full_path = file_dir / stored
        file.save(str(full_path))
        size = os.path.getsize(str(full_path))
        if size > MAX_BYTES:
            os.unlink(str(full_path))
            return jsonify({'success': False, 'error': f'图片过大 ({size//1024} KB)，请压缩到 10 MB 以内'}), 400

        tf = TravelerFile(
            traveler_id=record.id,
            file_category='passport',
            filename=file.filename,
            stored_filename=stored,
            file_path=str(full_path),
            file_size=size,
            file_type=file.content_type,
            description='护照识别页面上传',
        )
        db.session.add(tf)
        db.session.commit()
        return jsonify({
            'success': True,
            'action': action,  # 'created'/'updated' 表示 FrequentTraveler 状态
            'traveler_id': record.id,
            'file': tf.to_dict(),
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('护照图片保存失败')
        return jsonify({'success': False, 'error': f'保存失败: {e}'}), 500


@flights_passport.route('/recent')
@login_required
@staff_only
def recent():
    """近期保存列表（仅含护照号的旅客），支持搜索 + 分页"""
    per_page = min(int(request.args.get('limit', 20)), 100)
    page = max(int(request.args.get('page', 1)), 1)
    keyword = (request.args.get('q') or '').strip()

    query = FrequentTraveler.query.filter(
        FrequentTraveler.passport_number.isnot(None),
        FrequentTraveler.passport_number != ''
    )
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(or_(
            FrequentTraveler.name.ilike(like),
            FrequentTraveler.name_en.ilike(like),
            FrequentTraveler.passport_number.ilike(like),
        ))
    pag = query.order_by(desc(FrequentTraveler.updated_at)).paginate(
        page=page, per_page=per_page, error_out=False)
    return jsonify({
        'success': True,
        'data': [_traveler_to_passport_dict(t) for t in pag.items],
        'total': pag.total,
        'page': pag.page,
        'pages': pag.pages,
        'per_page': per_page,
    })


@flights_passport.route('/<int:tid>', methods=['DELETE'])
@login_required
@staff_only
def delete(tid):
    """删除一条常用旅客记录（连带 traveler_files 级联删除）"""
    rec = FrequentTraveler.query.get_or_404(tid)
    try:
        db.session.delete(rec)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
