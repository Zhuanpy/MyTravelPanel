from flask import Blueprint, render_template, jsonify, request, url_for, redirect
from ..code.Statement import OriginalStatement
from ..code.Invoice import CountHid
from flask import current_app as app
import os

# 创建蓝图
statement_blue = Blueprint('statement_routes', __name__)



@statement_blue.route('/open_uob_statement_folder')
def open_uob_statement_folder():
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    folder_path = os.path.join(UOB_path)
    os.startfile(folder_path)
    return render_template('statement/UobBank.html')


@statement_blue.route('/uob_bank_processing')
def uob_bank_processing():
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    st = OriginalStatement(UOB_path)
    st.statement_process()
    return render_template('statement/UobBank.html')


@statement_blue.route('/uob_original_processing')
def uob_original_processing():
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    statement = OriginalStatement(UOB_path)
    statement.organized_statement_data()
    return render_template('statement/UobBank.html')


@statement_blue.route('/latest_company_statement')
def latest_company_statement():
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    statement = OriginalStatement(UOB_path)
    statement.latest_company_statement()
    return render_template('statement/UobBank.html')


@statement_blue.route('/latest_self_statement')
def latest_self_statement():
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    statement = OriginalStatement(UOB_path)
    statement.latest_self_statement()
    return render_template('statement/UobBank.html')


@statement_blue.route('/statement_to_company')
def statement_to_company():
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    statement = OriginalStatement(UOB_path)
    statement.statement_to_company()
    return render_template('statement/UobBank.html')


@statement_blue.route('/athina_page')
def athina_page():
    return render_template('finance/athina/athina.html')


@statement_blue.route('/athina_processing', methods=['GET'])
def process_all_invoices():
    booking_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "BOOKING")
    count = CountHid(booking_path)
    profits, pre_sum = count.find_no_inv_booking()
    r = f'全部未结算总额：SGD {int(profits)};'
    return jsonify({'result': r})


# 处理指定月份订单的路由
@statement_blue.route('/athina_processing_month', methods=['POST'])
def process_month_invoice():
    booking_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "BOOKING")
    data = request.get_json()
    month = data.get('month')

    count = CountHid(booking_path)
    profits, pre_sum = count.find_no_inv_booking(pre_month=month)
    results = f'截至{month[:4]}年{month[-2:]}月的未结算总额: SGD {int(pre_sum)}'

    return jsonify({'result': results})


@statement_blue.route('/open_athina_statement_folder', methods=['GET', 'POST'])
def open_athina_statement_folder():
    # 获取文件夹路径
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "BOOKING")
    folder_path = os.path.join(UOB_path)

    # 打开文件夹
    os.startfile(folder_path)

    # 跳转到 athina_page
    return redirect(url_for("statement_routes.athina_page"))

@statement_blue.route('/statement/company_bill', methods=['GET'])
def company_bill():
    file_path = os.path.join(app.root_path, app.static_folder, "资源", "账单")

    folder_path = os.path.join(file_path)

    # 打开文件夹
    os.startfile(folder_path)
    # 跳转到 athina_page
    return redirect(url_for("index.index"))
