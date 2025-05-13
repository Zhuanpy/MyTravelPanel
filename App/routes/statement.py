from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash
from ..code.Statement import OriginalStatement
from ..code.Invoice import CountHid
from flask import current_app as app
import os

# 创建蓝图
statement_blue = Blueprint('statement_routes', __name__)


@statement_blue.route('/uob_bank')
def uob_bank():
    # 只渲染UOB银行账单页面，不执行任何操作
    return render_template('statement/UobBank.html')


@statement_blue.route('/open_uob_statement_folder', methods=['GET', 'POST'])
def open_uob_statement_folder():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    
    # POST请求执行原有功能
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    folder_path = os.path.join(UOB_path)
    os.startfile(folder_path)
    flash('成功打开UOB账单文件夹')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/uob_bank_processing', methods=['GET', 'POST'])
def uob_bank_processing():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    
    # POST请求执行原有功能
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    st = OriginalStatement(UOB_path)
    st.statement_process()
    flash('账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/uob_original_processing', methods=['GET', 'POST'])
def uob_original_processing():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    
    # POST请求执行原有功能
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    statement = OriginalStatement(UOB_path)
    statement.organized_statement_data()
    flash('原始账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/latest_company_statement', methods=['GET', 'POST'])
def latest_company_statement():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    
    # POST请求执行原有功能
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    statement = OriginalStatement(UOB_path)
    statement.latest_company_statement()
    flash('公司账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/latest_self_statement', methods=['GET', 'POST'])
def latest_self_statement():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    
    # POST请求执行原有功能
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    statement = OriginalStatement(UOB_path)
    statement.latest_self_statement()
    flash('个人账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/statement_to_company', methods=['GET', 'POST'])
def statement_to_company():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    
    # POST请求执行原有功能
    UOB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "ZHANG ZHUAN UOB MASTER")
    statement = OriginalStatement(UOB_path)
    statement.statement_to_company()
    flash('最终公司账单生成完成')
    return redirect(url_for('statement_routes.uob_bank'))


# OCBC银行相关路由
@statement_blue.route('/ocbc_bank')
def ocbc_bank():
    # 渲染OCBC银行账单页面
    return render_template('statement/OcbcBank.html')


@statement_blue.route('/open_ocbc_statement_folder', methods=['GET', 'POST'])
def open_ocbc_statement_folder():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    
    # POST请求执行功能
    # TODO: 更新为实际的OCBC账单文件夹路径
    OCBC_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "OCBC")
    folder_path = os.path.join(OCBC_path)
    os.startfile(folder_path)
    flash('成功打开OCBC账单文件夹')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_bank_processing', methods=['GET', 'POST'])
def ocbc_bank_processing():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    
    # TODO: 实现OCBC账单处理逻辑
    # POST请求执行功能
    OCBC_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "OCBC")
    # TODO: 根据实际情况实现具体的账单处理逻辑
    flash('OCBC账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_original_processing', methods=['GET', 'POST'])
def ocbc_original_processing():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    
    # TODO: 实现OCBC原始账单整理逻辑
    OCBC_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "OCBC")
    # TODO: 根据实际情况实现具体的原始账单整理逻辑
    flash('OCBC原始账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_latest_company_statement', methods=['GET', 'POST'])
def ocbc_latest_company_statement():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    
    # TODO: 实现OCBC公司账单整理逻辑
    OCBC_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "OCBC")
    # TODO: 根据实际情况实现具体的公司账单整理逻辑
    flash('OCBC公司账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_latest_self_statement', methods=['GET', 'POST'])
def ocbc_latest_self_statement():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    
    # TODO: 实现OCBC个人账单整理逻辑
    OCBC_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "OCBC")
    # TODO: 根据实际情况实现具体的个人账单整理逻辑
    flash('OCBC个人账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_to_company', methods=['GET', 'POST'])
def ocbc_to_company():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    
    # TODO: 实现OCBC生成公司账单逻辑
    OCBC_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "OCBC")
    # TODO: 根据实际情况实现具体的生成公司账单逻辑
    flash('OCBC公司账单生成功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


# 招商银行相关路由
@statement_blue.route('/cmb_bank')
def cmb_bank():
    # 渲染招商银行账单页面
    return render_template('statement/CmbBank.html')


@statement_blue.route('/open_cmb_statement_folder', methods=['GET', 'POST'])
def open_cmb_statement_folder():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    
    # POST请求执行功能
    # TODO: 更新为实际的招商银行账单文件夹路径
    CMB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "CMB")
    folder_path = os.path.join(CMB_path)
    os.startfile(folder_path)
    flash('成功打开招商银行账单文件夹')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_bank_processing', methods=['GET', 'POST'])
def cmb_bank_processing():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    
    # TODO: 实现招商银行账单处理逻辑
    CMB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "CMB")
    # TODO: 根据实际情况实现具体的账单处理逻辑
    flash('招商银行账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_original_processing', methods=['GET', 'POST'])
def cmb_original_processing():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    
    # TODO: 实现招商银行原始账单整理逻辑
    CMB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "CMB")
    # TODO: 根据实际情况实现具体的原始账单整理逻辑
    flash('招商银行原始账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_latest_company_statement', methods=['GET', 'POST'])
def cmb_latest_company_statement():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    
    # TODO: 实现招商银行公司账单整理逻辑
    CMB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "CMB")
    # TODO: 根据实际情况实现具体的公司账单整理逻辑
    flash('招商银行公司账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_latest_self_statement', methods=['GET', 'POST'])
def cmb_latest_self_statement():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    
    # TODO: 实现招商银行个人账单整理逻辑
    CMB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "CMB")
    # TODO: 根据实际情况实现具体的个人账单整理逻辑
    flash('招商银行个人账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_to_company', methods=['GET', 'POST'])
def cmb_to_company():
    # 如果是GET请求，重定向到安全页面
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    
    # TODO: 实现招商银行生成公司账单逻辑
    CMB_path = os.path.join(app.root_path, app.static_folder, "资源", "账单", "CMB")
    # TODO: 根据实际情况实现具体的生成公司账单逻辑
    flash('招商银行公司账单生成功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/athina_page')
def athina_page():
    return render_template('statement/athina.html')


@statement_blue.route('/athina_processing', methods=['GET', 'POST'])
def process_all_invoices():
    # 验证AJAX请求以提高安全性
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest' and request.method == 'GET':
        # 如果不是AJAX请求但是GET方法，重定向到athina_page
        return redirect(url_for('statement_routes.athina_page'))
        
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

@statement_blue.route('/statement/company_bill', methods=['GET', 'POST'])
def company_bill():
    # 仅处理POST请求执行文件操作
    if request.method == 'POST':
        file_path = os.path.join(app.root_path, app.static_folder, "资源", "账单")
        folder_path = os.path.join(file_path)
        # 打开文件夹
        os.startfile(folder_path)
        flash('成功打开公司账单文件夹')
    
    # 所有请求都重定向到首页
    return redirect(url_for("index.index"))
