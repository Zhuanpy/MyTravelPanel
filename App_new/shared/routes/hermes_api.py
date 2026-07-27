# -*- coding: utf-8 -*-
"""Hermes 自描述接口

给 AI agent（Hermes）提供「读得到」的接口清单，避免把 API 说明塞进它有限、
会被淘汰的记忆库。Hermes 开机 fetch 一次即可拿到最新的可调接口。

- GET /api/hermes/catalog : 结构化 JSON 接口目录（agent 好解析）
- GET /api/hermes/manual  : 返回 docs/Hermes_API手册.md 全文（给人看/兜底）

两者都走 token 鉴权（X-API-Key → request_loader），GET 无 CSRF 顾虑。
"""

from pathlib import Path
from flask import Blueprint, jsonify, Response, current_app, request
from flask_login import login_required, current_user

from App_new.exts import db
from App_new.utils.decorators import staff_only

hermes_api = Blueprint('hermes_api', __name__, url_prefix='/api/hermes')

# 手册 markdown 文件（项目根/docs 下），运行时读取以保证始终最新
_MANUAL_RELATIVE = ('docs', 'Hermes_API手册.md')

# 结构化接口目录：只收录「当前已 JSON 化、agent 可直接调」的接口。
# 完整细节（请求体/返回字段/示例）见 /api/hermes/manual。
_CATALOG = {
    'base_url': 'https://joyesc.com',
    'auth': {
        'header': 'X-API-Key: <staff token>',
        'note': 'token 走 Flask-Login request_loader 免登录，带 token 的写请求自动跳过 CSRF；token 用户需 staff 角色。',
        'create_token': 'python scripts/20260622_manage_api_token.py create <邮箱> <标签>',
    },
    'manual': '/api/hermes/manual',
    'groups': [
        {
            'name': '自检 / 查公司（下单前先用）',
            'endpoints': [
                {'method': 'GET', 'path': '/api/hermes/whoami',
                 'input': '-',
                 'desc': '★token 自检。任何请求返回 401/403 时先打这里：200=token 有效，'
                         '问题在那个请求本身，原样报错误不要降级；401=token 失效，停止并报告；'
                         '403=角色不对。**任何情况下都不要改用账号密码登录浏览器**'},
                {'method': 'GET', 'path': '/api/hermes/companies/search',
                 'input': 'query q, limit?, role?(customer|supplier|any)',
                 'desc': '按公司名/简称/代码搜客户，返回 company_id + 联系人列表。'
                         '替代开浏览器搜公司'},
                {'method': 'GET', 'path': '/api/hermes/order/<hid|pid>/summary',
                 'input': '-',
                 'desc': '★下单后验收：一次返回项目全部关键事实（REF/供应商/售价/成本/'
                         'EO号/发票号/乘客/航段/ref_count），逐项与原始订单要素比对'},
            ],
        },
        {
            'name': '机票行程工具 (Athina)',
            'endpoints': [
                {'method': 'POST', 'path': '/flights_athina/parse_flights',
                 'input': 'JSON {text}',
                 'desc': '各平台行程文本→结构化航段（Trip/携程/Google Flights/酷航/手动）'},
                {'method': 'POST', 'path': '/flights_athina/api/convert_itinerary',
                 'input': 'JSON {text, language(chinese|english), luggage?, price?}',
                 'desc': '行程文本→格式化中/英文行程单'},
                {'method': 'POST', 'path': '/flights_athina/generate_booking_code',
                 'input': 'JSON [{flightNumber, flightDate}]',
                 'desc': '生成 GDS 订位指令串（航班需已在本地时刻表；非真实预订）'},
            ],
        },
        {
            'name': '实时航班 & 解析',
            'endpoints': [
                {'method': 'GET', 'path': '/flight_schedule/get-flight-info',
                 'input': 'query flight_number,dep_iata,arr_iata,flight_date',
                 'desc': '实时抓航班（Aerodatabox→FR24→DB 三级回退，含航站楼/登机口）'},
                {'method': 'GET', 'path': '/flight_schedule/search_airports',
                 'input': 'query iata,city', 'desc': '机场模糊搜索'},
                {'method': 'POST', 'path': '/flights_booking/parse_flight_text',
                 'input': 'JSON {text}', 'desc': '粘贴行程文字→航段/乘客'},
            ],
        },
        {
            'name': '护照 / 常用旅客',
            'endpoints': [
                {'method': 'POST', 'path': '/flights_passport/ocr',
                 'input': 'multipart image', 'desc': '护照图片→MRZ→JSON（不入库）'},
                {'method': 'POST', 'path': '/flights_passport/save',
                 'input': 'JSON 护照字段', 'desc': '识别结果落库常用旅客（去重键=护照号）'},
                {'method': 'GET', 'path': '/flights_passport/recent',
                 'input': 'query q,page,limit', 'desc': '近期护照旅客列表'},
            ],
        },
        {
            'name': '机票下单（闭环）',
            'endpoints': [
                {'method': 'POST', 'path': '/projects/detail/<source_id>/copy',
                 'input': 'JSON {with_refs?:bool}',
                 'desc': '复制项目。★下单请传 {"with_refs": false}：只复制项目头+成员，'
                         '不复制模板 REF/航段/乘客，省掉「先建后删」和脏数据窗口。'
                         '返回 new_project_id/new_hid/new_ref_ids'},
                {'method': 'POST', 'path': '/projects/<pid>/members/batch',
                 'input': 'JSON {members:[{member_name,member_name_en}]}',
                 'desc': '批量加成员（首个自动 Leader）'},
                {'method': 'POST', 'path': '/projects/ref/flight/quick-create/<pid>',
                 'input': 'JSON {supplier_id,leader_name,passengers,segments,auto_eo,'
                          'auto_invoice,idempotency_key?}',
                 'desc': '一键建 机票REF + EO + 发票。★务必传 idempotency_key（同一订单固定不变，'
                         '如 hermes-<消息ID>）：重试/超时重发会原样返回首次结果并带 '
                         'idempotent_replay=true，不会重复建单'},
                {'method': 'GET', 'path': '/projects/ref/flight/<rid>/segments',
                 'input': '-', 'desc': '航段列表（改单前先拿 segment_id）'},
                {'method': 'GET', 'path': '/projects/ref/flight/<rid>/passengers',
                 'input': '-', 'desc': '乘客列表（含 segments 格子：PNR/票号/座位/行李）'},
                {'method': 'POST', 'path': '/projects/ref/flight/<rid>/ticketing',
                 'input': 'JSON {replace,passengers:[{name|passenger_id,pnr,ticket_number,'
                          'baggage,passport_number,segments:[{segment_id,seat,pnr,...}]}]}',
                 'desc': '★补行程单首选：一个请求灌完整个 REF 的「乘客×航段」票务矩阵，'
                         '出错整批回滚。多乘客/多航段用它，别按乘客循环'},
                {'method': 'POST', 'path': '/projects/ref/flight/segment/<sid>/update',
                 'input': 'JSON {departure_terminal,arrival_terminal,airline_name,cabin_class}',
                 'desc': '改单个航段字段。仅限这 4 个字段；'
                         'PNR/票号/座位/行李是乘客×航段级，写这里不显示，用 ticketing'},
                {'method': 'POST', 'path': '/projects/ref/flight/passenger/<pid>/update',
                 'input': 'JSON {ticket_number,pnr,baggage,passport_number,segments:[...]}',
                 'desc': '改单个乘客（乘客级默认值 + 各航段格子）。只动一两个格子时用'},
            ],
        },
        {
            'name': '发票 / EO / 付款',
            'endpoints': [
                {'method': 'POST', 'path': '/projects/invoice/quick_create/<pid>',
                 'input': 'JSON', 'desc': '按项目快速开发票'},
                {'method': 'POST', 'path': '/projects/invoice/void',
                 'input': 'JSON {invoice_number}', 'desc': '按发票号作废'},
                {'method': 'POST', 'path': '/projects/eo/quick_create/<rid>',
                 'input': 'JSON/-', 'desc': '快速创建 EO'},
                {'method': 'POST', 'path': '/projects/eo/<eid>/pay',
                 'input': 'JSON', 'desc': '单 EO 付款'},
                {'method': 'POST', 'path': '/projects/eo/batch-pay/submit',
                 'input': 'JSON', 'desc': '批量付款'},
            ],
        },
        {
            'name': '项目 / 成员 / 提醒',
            'endpoints': [
                {'method': 'GET', 'path': '/projects/list/api/search-by-person',
                 'input': 'query q,limit?',
                 'desc': '按姓名反查项目：命中联系人/负责人/REF乘客/项目成员，返回结构化列表（含 hid/ref_number/company_name/role/selling_price）'},
                {'method': 'GET', 'path': '/projects/<pid>/members', 'input': '-', 'desc': '成员列表'},
                {'method': 'GET', 'path': '/projects/detail/<pid>/refs', 'input': '-', 'desc': '项目 REF 列表'},
                {'method': 'GET', 'path': '/projects/reminder/<hid>/list', 'input': '-', 'desc': '项目提醒列表'},
                {'method': 'POST', 'path': '/projects/list/api/settle/<pid>', 'input': '-', 'desc': '结算单个项目'},
            ],
        },
        {
            'name': '签证',
            'endpoints': [
                {'method': 'POST', 'path': '/visa/project/api/files/<pid>/upload',
                 'input': 'multipart files+description', 'desc': '上传签证材料'},
                {'method': 'GET', 'path': '/visa/project/<id>/form-data',
                 'input': '-', 'desc': '读取韩国签证填表字段结构+已填值'},
                {'method': 'POST', 'path': '/visa/project/<id>/form-data',
                 'input': 'JSON {values:{seq:detail}}', 'desc': '写入申请人填表值（存库，供 generate_form 生成）'},
                {'method': 'POST', 'path': '/visa/project/generate_form/<id>',
                 'input': '-', 'desc': '生成韩国签证表格（填表值改从数据库读取）'},
                {'method': 'POST', 'path': '/visa/project/sync_project_documents/<id>',
                 'input': '-', 'desc': '从模板同步资料清单'},
            ],
        },
        {
            'name': '打印 / PDF（HTML 页 + Chrome printToPDF）',
            'note': '这些是打印用 HTML 页，不是 JSON 接口。用你的 Chrome 带 X-API-Key 导航过去，'
                    '再调 CDP Page.printToPDF 即得 PDF 字节（打印 CSS 已隔离，只输出单据本身）。',
            'endpoints': [
                {'method': 'GET', 'path': '/projects/invoice/<invoice_id>',
                 'input': '-', 'desc': '发票页；printToPDF → 发票 PDF（@media print 只输出发票区）'},
                {'method': 'GET', 'path': '/flights_booking/print_itinerary/<ref_id>',
                 'input': '-', 'desc': '行程单打印页（独立 A4 HTML）；printToPDF → 行程单 PDF'},
            ],
        },
    ],
    # 鉴权失败的语义（2026-07-27 起不再 302 到登录页）
    'auth_errors': {
        '401': 'token 缺失/无效/已停用 → 停止并报告，等人换 token',
        '403': 'token 有效但角色不是 staff → 停止并报告，换 token 也没用',
        'other': '与鉴权无关（路径/参数/数据权限）→ 原样报出状态码和响应体',
        'probe': 'GET /api/hermes/whoami',
        'note': 'ApiToken 没有过期时间（只有 is_active 开关），所以「token 过期」这个判断'
                '永远是错的。任何情况下都不要降级到账号密码登录浏览器。',
    },
    # 尚未 JSON 化、Hermes 暂时调不了的动作，避免它误以为存在
    'not_available_yet': [
        '非机票 REF 下单（hotel/visa/tour/insurance/transport 无 quick-create）',
        '签证建项目 + 申请人填表数据 JSON 写入口',
        '非机票 REF 改单、单笔收款/退款/预付创建',
        '项目从零创建（但可用 copy + with_refs:false 得到一个不含模板REF的干净项目）',
    ],
}


def _manual_path() -> Path:
    """docs/Hermes_API手册.md 的绝对路径（项目根 = App_new 的上级目录）"""
    return Path(current_app.root_path).parent.joinpath(*_MANUAL_RELATIVE)


@hermes_api.route('/catalog', methods=['GET'])
@login_required
@staff_only
def catalog():
    """结构化 JSON 接口目录，供 Hermes 程序化读取。"""
    return jsonify({'success': True, 'source': 'docs/Hermes_API手册.md', **_CATALOG})


@hermes_api.route('/whoami', methods=['GET'])
@login_required
@staff_only
def whoami():
    """token 自检探针（最便宜的一次调用）。

    Hermes 遇到任何疑似鉴权失败时**先打这里**再决定下一步：
      - 200 → token 有效。故障出在刚才那个请求本身（路径/参数/数据权限），
              把状态码与响应体原文报出来，**不要**降级到浏览器账号密码登录。
      - 401 → token 确实无效/被停用，停止并报告，等人换 token。
      - 403 → token 有效但角色不是 staff，换 token 也没用。
    """
    return jsonify({
        'success': True,
        'user_id': current_user.id,
        'email': getattr(current_user, 'email', None),
        'username': getattr(current_user, 'username', None),
        'role': current_user.role.name if getattr(current_user, 'role', None) else None,
        'note': 'token 有效。若业务接口仍失败，原因不是鉴权，请勿改用账号密码登录。',
    })


@hermes_api.route('/companies/search', methods=['GET'])
@login_required
@staff_only
def search_companies():
    """按公司名 / 简称 / 公司代码模糊搜索客户公司，返回公司 + 联系人。

    下单前用它一次拿到 company_id 与联系人，替代「开浏览器搜公司」。
    query: q（必填）, limit（默认 20，上限 50）, role（customer|supplier|any，默认 customer）
    """
    from App_new.business.projects.models.project import CustomerCompany

    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'success': False, 'error': 'q 不能为空'}), 400

    try:
        limit = min(int(request.args.get('limit', 20)), 50)
    except (TypeError, ValueError):
        limit = 20

    like = f'%{q}%'
    query = CustomerCompany.query.filter(
        CustomerCompany.status == 'active',
        db.or_(
            CustomerCompany.company_name.like(like),
            CustomerCompany.alias.like(like),
            CustomerCompany.company_code.like(like),
        ),
    )

    # 默认只搜客户；供应商用 role=supplier（下单选供应商时用）
    role = (request.args.get('role') or 'customer').lower()
    if role == 'customer':
        query = query.filter(CustomerCompany.is_customer.is_(True))
    elif role == 'supplier':
        query = query.filter(CustomerCompany.is_supplier.is_(True))

    # 常用的排前面（click_count 是既有的使用热度字段）
    rows = query.order_by(CustomerCompany.click_count.desc(),
                          CustomerCompany.company_name).limit(limit).all()

    return jsonify({
        'success': True,
        'count': len(rows),
        'data': [{
            'id': c.id,
            'company_name': c.company_name,
            'alias': c.alias,
            'company_code': c.company_code,
            'currency': c.currency,
            'is_customer': c.is_customer,
            'is_supplier': c.is_supplier,
            # 公司表上的主联系人（旧字段，可能为空）
            'contact_person': c.contact_person,
            'contact_phone': c.contact_phone,
            'contact_email': c.contact_email,
            # 联系人表（推荐用这个）
            'contacts': [ct.to_dict() for ct in c.contacts],
        } for c in rows],
    })


@hermes_api.route('/order/<key>/summary', methods=['GET'])
@login_required
@staff_only
def order_summary(key):
    """下单验收专用：一次返回项目的全部关键事实，供 agent 逐项比对。

    key 可以是 HID（如 H2601234）或项目主表 id。
    返回 refs（含 ref_number/供应商/售价/成本/EO号/发票号/乘客/航段），
    agent 应拿它与「解析阶段得到的原始订单要素」逐项断言，并校验 ref_count。
    """
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.invoice import ProjectInvoice
    from App_new.business.flight.models.flight import (
        ProjectFlightSegment, ProjectFlightPassenger,
    )
    from App_new.utils.permissions import can_access_project

    # 先按 HID 查，查不到再按主键 id 查
    header = ProjectHeader.query.filter_by(hid=key).first()
    if not header and str(key).isdigit():
        header = ProjectHeader.query.get(int(key))
    if not header:
        return jsonify({'success': False, 'error': f'项目不存在: {key}'}), 404
    if not can_access_project(header, current_user):
        return jsonify({'success': False, 'error': '无权访问此项目'}), 403

    # 该项目下的发票：ref_ids 是 JSON 文本，逐张解析出它覆盖的 REF
    import json
    invoices = ProjectInvoice.query.filter_by(header_id=header.id).all()
    ref_to_invoice = {}
    for inv in invoices:
        try:
            for rid in (json.loads(inv.ref_ids) if inv.ref_ids else []):
                ref_to_invoice[int(rid)] = inv
        except (ValueError, TypeError):
            continue

    def _money(v):
        return float(v) if v is not None else None

    refs = []
    for ref in header.refs:
        eo = ref.eos  # uselist=False，单个或 None
        inv = ref_to_invoice.get(ref.id)
        segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id) \
            .order_by(ProjectFlightSegment.departure_time).all()
        passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).all()

        refs.append({
            'ref_id': ref.id,
            'ref_number': ref.ref_number,
            'description': ref.description,
            'ref_type': ref.ref_type.name if ref.ref_type else None,
            'supplier_id': ref.supplier_id,
            'supplier_name': ref.supplier.company_name if ref.supplier else None,
            'selling_price': _money(ref.selling_price),
            'cost_price': _money(ref.cost_price),
            'currency': ref.currency,
            'status': ref.status,
            'payment_status': ref.payment_status,
            'eo_number': eo.eo_number if eo else None,
            'eo_status': eo.status if eo else None,
            'invoice_number': inv.invoice_number if inv else None,
            'invoice_amount': _money(inv.amount) if inv else None,
            'invoice_status': inv.status if inv else None,
            'passengers': [{
                'id': p.id,
                'name': p.name,
                'passenger_type': p.passenger_type,
                'selling_price': _money(p.selling_price),
                'cost_price': _money(p.cost_price),
                'baggage': p.baggage,
                'ticket_number': p.ticket_number,
                'pnr': p.pnr,
                'passport_number': p.passport_number,
            } for p in passengers],
            'segments': [{
                'id': s.id,
                'flight_number': s.flight_number,
                'airline_name': s.airline_name,
                'departure_airport': s.departure_airport,
                'arrival_airport': s.arrival_airport,
                'departure_time': s.departure_time.isoformat() if s.departure_time else None,
                'arrival_time': s.arrival_time.isoformat() if s.arrival_time else None,
                'cabin_class': s.cabin_class,
            } for s in segments],
        })

    return jsonify({
        'success': True,
        'project_id': header.id,
        'hid': header.hid,
        'company_id': header.company_id,
        'company_name': header.company.company_name if header.company else None,
        'contact': header.contact,
        'leader_name': header.leader_name,
        'currency': header.currency,
        'status': header.status,
        # ★ 验收必查：多出来的 REF 通常是复制来的模板 REF 没删，或重复建单
        'ref_count': len(refs),
        'refs': refs,
    })


@hermes_api.route('/manual', methods=['GET'])
@login_required
@staff_only
def manual():
    """返回 Hermes API 手册 markdown 全文（运行时读取，始终最新）。"""
    path = _manual_path()
    if not path.exists():
        return jsonify({'success': False, 'error': f'手册文件不存在: {path.name}'}), 404
    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        return jsonify({'success': False, 'error': f'读取手册失败: {e}'}), 500
    return Response(content, mimetype='text/markdown; charset=utf-8')
