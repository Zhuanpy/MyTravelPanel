from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash
from App.code.Statement import OriginalStatement
from App.code.Invoice import CountHid
from flask import current_app as app
import os
from App.config import Config
from pathlib import Path

# 创建蓝图
statement_blue = Blueprint('statement_routes', __name__)


@statement_blue.route('/uob_bank')
def uob_bank():
    # 只渲染UOB银行账单页面，不执行任何操作
    return render_template('statement/UobBank.html')


@statement_blue.route('/open_uob_statement_folder', methods=['GET', 'POST'])
def open_uob_statement_folder():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    os.startfile(str(folder_path))
    flash('成功打开UOB账单文件夹')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/uob_bank_processing', methods=['GET', 'POST'])
def uob_bank_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    st = OriginalStatement(str(folder_path))
    st.statement_process()
    flash('账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/uob_original_processing', methods=['GET', 'POST'])
def uob_original_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.organized_statement_data()
    flash('原始账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/latest_company_statement', methods=['GET', 'POST'])
def latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.latest_company_statement()
    flash('公司账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/latest_self_statement', methods=['GET', 'POST'])
def latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.latest_self_statement()
    flash('个人账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/statement_to_company', methods=['GET', 'POST'])
def statement_to_company():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.statement_to_company()
    flash('最终公司账单生成完成')
    return redirect(url_for('statement_routes.uob_bank'))


# OCBC银行相关路由
@statement_blue.route('/ocbc_bank')
def ocbc_bank():
    return render_template('statement/OcbcBank.html')


@statement_blue.route('/open_ocbc_statement_folder', methods=['GET', 'POST'])
def open_ocbc_statement_folder():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    os.startfile(str(folder_path))
    flash('成功打开OCBC账单文件夹')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_bank_processing', methods=['GET', 'POST'])
def ocbc_bank_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_original_processing', methods=['GET', 'POST'])
def ocbc_original_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC原始账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_latest_company_statement', methods=['GET', 'POST'])
def ocbc_latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC公司账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_latest_self_statement', methods=['GET', 'POST'])
def ocbc_latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC个人账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_to_company', methods=['GET', 'POST'])
def ocbc_to_company():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC公司账单生成功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


# 招商银行相关路由
@statement_blue.route('/cmb_bank')
def cmb_bank():
    return render_template('statement/CmbBank.html')


@statement_blue.route('/open_cmb_statement_folder', methods=['GET', 'POST'])
def open_cmb_statement_folder():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    os.startfile(str(folder_path))
    flash('成功打开招商银行账单文件夹')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_bank_processing', methods=['GET', 'POST'])
def cmb_bank_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_original_processing', methods=['GET', 'POST'])
def cmb_original_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行原始账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_latest_company_statement', methods=['GET', 'POST'])
def cmb_latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行公司账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_latest_self_statement', methods=['GET', 'POST'])
def cmb_latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行个人账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_to_company', methods=['GET', 'POST'])
def cmb_to_company():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行公司账单生成功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/athina_page')
def athina_page():
    return render_template('statement/athina.html')


@statement_blue.route('/athina_processing', methods=['GET', 'POST'])
def process_all_invoices():
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest' and request.method == 'GET':
        return redirect(url_for('statement_routes.athina_page'))
    folder_path = Config.BILLING_DATA_PATH / "BOOKING"
    count = CountHid(str(folder_path))
    profits, pre_sum = count.find_no_inv_booking()
    r = f'全部未结算总额：SGD {int(profits)};'
    return jsonify({'result': r})


@statement_blue.route('/athina_processing_month', methods=['POST'])
def process_month_invoice():
    folder_path = Config.BILLING_DATA_PATH / "BOOKING"
    data = request.get_json()
    month = data.get('month')
    count = CountHid(str(folder_path))
    profits, pre_sum = count.find_no_inv_booking(pre_month=month)
    results = f'截至{month[:4]}年{month[-2:]}月的未结算总额: SGD {int(pre_sum)}'
    return jsonify({'result': results})


@statement_blue.route('/open_athina_statement_folder', methods=['GET', 'POST'])
def open_athina_statement_folder():
    folder_path = Config.BILLING_DATA_PATH / "BOOKING"
    os.startfile(str(folder_path))
    return redirect(url_for("statement_routes.athina_page"))

@statement_blue.route('/statement/company_bill', methods=['GET', 'POST'])
def company_bill():
    if request.method == 'POST':
        folder_path = Config.BILLING_DATA_PATH
        os.startfile(str(folder_path))
        flash('成功打开公司账单文件夹')
    return redirect(url_for("index.index"))
