# -*- coding: utf-8 -*-
"""旧 athina_* 路由的兼容重定向

历史上这批路由带 athina 前缀（当年从 Athina 系统导入数据时留下的），
现已改成中性命名。存过书签、写进邮件或外部脚本里的旧链接不能直接 404，
所以在这里统一做 301 重定向。

GET 页面用 301（浏览器会记住），POST 接口用 307（保留请求方法和请求体）。
以后确认没人再访问旧地址了，整个文件可以直接删掉。
"""

from flask import Blueprint, redirect, request, url_for

legacy_blue = Blueprint('legacy_athina', __name__)

# 旧路径 -> 新 endpoint
GET_REDIRECTS = {
    # 注：旧的 /statement/athina_page 不在这里——它定义在一个从未注册过的
    # 死文件里，线上从来就是 404，没有兼容的必要
    '/statement/athina_stats': 'statement_routes.statement_stats',
    '/statement/athina_header_data': 'statement_routes.statement_data',
    '/statement/athina_processing': 'statement_routes.process_all_invoices',
    '/statement/open_athina_statement_folder': 'statement_routes.open_statement_folder',
    '/statement/athina_performance_settlement': 'statement_routes.performance_settlement',
    '/statement/athina_performance_settlement_export': 'statement_routes.performance_settlement_export',
    '/statement/athina_export_unsettled': 'statement_routes.export_unsettled_orders',
    '/statement/athina_to_project/csv_import': 'statement_routes.import_to_project_csv_import',
}

# POST 接口：307 保留方法和 body
POST_REDIRECTS = {
    '/statement/athina_processing_month': 'statement_routes.process_month_invoice',
    '/statement/athina_batch_settle_performance': 'statement_routes.batch_settle_performance',
    '/statement/athina_batch_settle_all_filtered': 'statement_routes.batch_settle_all_filtered',
    '/statement/athina_calculate_profit_distribution': 'statement_routes.calculate_profit_distribution',
    '/statement/athina_calculate_all_unsettled_profit_distribution': 'statement_routes.calculate_all_unsettled_profit_distribution',
    '/statement/athina_to_project/import_reservation_csv': 'statement_routes.import_reservation_csv',
    '/statement/athina_to_project/import_eo_csv': 'statement_routes.import_eo_csv',
    '/statement/athina_to_project/import_invoice_csv': 'statement_routes.import_invoice_csv',
    '/statement/athina_to_project/import_receipt_csv': 'statement_routes.import_receipt_csv',
}

# 机票工具：整个前缀换了名字
FLIGHT_PREFIX_OLD = '/flights_athina'
FLIGHT_PREFIX_NEW = '/flights_itinerary'
FLIGHT_PATH_ALIASES = {
    '/athina': '/booking_code',
    '/athina_simple': '/booking_code_simple',
}


def _with_query(path):
    """带上原始 query string，筛选条件、tab 参数都不能丢"""
    return path + ('?' + request.query_string.decode() if request.query_string else '')


def _make_get_view(endpoint):
    def view(**kwargs):
        return redirect(_with_query(url_for(endpoint, **kwargs)), code=301)
    return view


def _make_post_view(endpoint):
    def view(**kwargs):
        return redirect(_with_query(url_for(endpoint, **kwargs)), code=307)
    return view


for i, (old_path, endpoint) in enumerate(GET_REDIRECTS.items()):
    legacy_blue.add_url_rule(old_path, endpoint='get_%d' % i,
                             view_func=_make_get_view(endpoint), methods=['GET'])

for i, (old_path, endpoint) in enumerate(POST_REDIRECTS.items()):
    legacy_blue.add_url_rule(old_path, endpoint='post_%d' % i,
                             view_func=_make_post_view(endpoint),
                             methods=['GET', 'POST'])


@legacy_blue.route('/statement/athina_to_project/generate_eos/<int:project_id>',
                   methods=['GET', 'POST'])
def legacy_generate_eos(project_id):
    return redirect(url_for('statement_routes.import_to_project_generate_eos',
                            project_id=project_id), code=307)


@legacy_blue.route(FLIGHT_PREFIX_OLD, defaults={'sub_path': ''},
                   methods=['GET', 'POST'])
@legacy_blue.route(FLIGHT_PREFIX_OLD + '/<path:sub_path>', methods=['GET', 'POST'])
def legacy_flights(sub_path):
    """/flights_athina/* -> /flights_itinerary/*

    两个页面路径本身也改了名（/athina、/athina_simple），单独映射；
    其余子路径原样透传。
    """
    path = '/' + sub_path if sub_path else ''
    path = FLIGHT_PATH_ALIASES.get(path, path)
    code = 301 if request.method == 'GET' else 307
    return redirect(_with_query(FLIGHT_PREFIX_NEW + path), code=code)


@legacy_blue.route('/m/athina-code', methods=['GET', 'POST'])
def legacy_mobile_booking_code():
    return redirect(_with_query(url_for('mobile.booking_code')),
                    code=301 if request.method == 'GET' else 307)
