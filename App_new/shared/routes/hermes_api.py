# -*- coding: utf-8 -*-
"""Hermes 自描述接口

给 AI agent（Hermes）提供「读得到」的接口清单，避免把 API 说明塞进它有限、
会被淘汰的记忆库。Hermes 开机 fetch 一次即可拿到最新的可调接口。

- GET /api/hermes/catalog : 结构化 JSON 接口目录（agent 好解析）
- GET /api/hermes/manual  : 返回 docs/Hermes_API手册.md 全文（给人看/兜底）

两者都走 token 鉴权（X-API-Key → request_loader），GET 无 CSRF 顾虑。
"""

from pathlib import Path
from flask import Blueprint, jsonify, Response, current_app
from flask_login import login_required

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
                 'input': '-', 'desc': '复制项目，返回 new_project_id/new_hid/new_ref_ids'},
                {'method': 'POST', 'path': '/projects/<pid>/members/batch',
                 'input': 'JSON {members:[{member_name,member_name_en}]}',
                 'desc': '批量加成员（首个自动 Leader）'},
                {'method': 'POST', 'path': '/projects/ref/flight/quick-create/<pid>',
                 'input': 'JSON {supplier_id,leader_name,passengers,segments,auto_eo,auto_invoice}',
                 'desc': '一键建 机票REF + EO + 发票'},
                {'method': 'POST', 'path': '/projects/ref/flight/segment/<sid>/update',
                 'input': 'JSON', 'desc': '改单个航段字段（航站楼/时刻/票号）'},
                {'method': 'POST', 'path': '/projects/ref/flight/passenger/<pid>/update',
                 'input': 'JSON', 'desc': '改单个乘客字段'},
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
                {'method': 'POST', 'path': '/visa/project/generate_form/<id>',
                 'input': '-', 'desc': '生成韩国签证表格（申请人数据仍来自项目文件夹 FormSample.xls）'},
                {'method': 'POST', 'path': '/visa/project/sync_project_documents/<id>',
                 'input': '-', 'desc': '从模板同步资料清单'},
            ],
        },
    ],
    # 尚未 JSON 化、Hermes 暂时调不了的动作，避免它误以为存在
    'not_available_yet': [
        '非机票 REF 下单（hotel/visa/tour/insurance/transport 无 quick-create）',
        '签证建项目 + 申请人填表数据 JSON 写入口',
        '非机票 REF 改单、单笔收款/退款/预付创建、项目从零创建',
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
