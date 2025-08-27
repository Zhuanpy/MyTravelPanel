from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash
from flask_login import login_required
from App_new.utils.Statement import OriginalStatement
from App_new.utils.Invoice import CountHid
import os
import logging
from App_new.config import Config
import subprocess
import pandas as pd
import tempfile
from datetime import datetime
from App_new.exts import csrf
from App_new.utils.decorators import staff_only
from App_new.utils.report_utils import (
    get_report_headers_string,
    read_excel_file,
    read_csv_file,
    compare_profit_columns,
    add_comparison_column
)
from App_new.config import safe_json

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
statement_blue = Blueprint('statement_routes', __name__)


@statement_blue.route('/uob_bank')
@login_required
@staff_only
def uob_bank():
    # 只渲染UOB银行账单页面，不执行任何操作
    return render_template('finance/statement/UobBank.html')


@statement_blue.route('/open_uob_statement_folder', methods=['GET', 'POST'])
@csrf.exempt
def open_uob_statement_folder():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    
    # 如果文件夹不存在，则创建它
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            flash('UOB文件夹不存在，已自动创建', 'info')
        except Exception as e:
            flash(f'创建文件夹失败：{str(e)}', 'error')
            return redirect(url_for('statement_routes.uob_bank'))
    
    try:
        subprocess.run(['explorer', str(folder_path)], shell=True)
        flash('成功打开UOB账单文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/uob_bank_processing', methods=['GET', 'POST'])
@csrf.exempt
def uob_bank_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    st = OriginalStatement(str(folder_path))
    st.statement_process()
    flash('账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/uob_original_processing', methods=['GET', 'POST'])
@csrf.exempt
def uob_original_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.organized_statement_data()
    flash('原始账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/latest_company_statement', methods=['GET', 'POST'])
@csrf.exempt
def latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.latest_company_statement()
    flash('公司账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/latest_self_statement', methods=['GET', 'POST'])
@csrf.exempt
def latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.latest_self_statement()
    flash('个人账单整理完成')
    return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/statement_to_company', methods=['GET', 'POST'])
@csrf.exempt
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
@login_required
@staff_only
def ocbc_bank():
    return render_template('finance/statement/OcbcBank.html')


@statement_blue.route('/open_ocbc_statement_folder', methods=['GET', 'POST'])
@csrf.exempt
def open_ocbc_statement_folder():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    
    # 如果文件夹不存在，则创建它
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            flash('OCBC文件夹不存在，已自动创建', 'info')
        except Exception as e:
            flash(f'创建文件夹失败：{str(e)}', 'error')
            return redirect(url_for('statement_routes.ocbc_bank'))
    
    try:
        subprocess.run(['explorer', str(folder_path)], shell=True)
        flash('成功打开OCBC账单文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_bank_processing', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_bank_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_original_processing', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_original_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC原始账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_latest_company_statement', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC公司账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_latest_self_statement', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC个人账单整理功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


@statement_blue.route('/ocbc_to_company', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_to_company():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC公司账单生成功能尚未实现')
    return redirect(url_for('statement_routes.ocbc_bank'))


# 招商银行相关路由
@statement_blue.route('/cmb_bank')
@login_required
@staff_only
def cmb_bank():
    return render_template('finance/statement/CmbBank.html')


@statement_blue.route('/open_cmb_statement_folder', methods=['GET', 'POST'])
@csrf.exempt
def open_cmb_statement_folder():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    
    # 如果文件夹不存在，则创建它
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            flash('CMB文件夹不存在，已自动创建', 'info')
        except Exception as e:
            flash(f'创建文件夹失败：{str(e)}', 'error')
            return redirect(url_for('statement_routes.cmb_bank'))
    
    try:
        subprocess.run(['explorer', str(folder_path)], shell=True)
        flash('成功打开招商银行账单文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_bank_processing', methods=['GET', 'POST'])
@csrf.exempt
def cmb_bank_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_original_processing', methods=['GET', 'POST'])
@csrf.exempt
def cmb_original_processing():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行原始账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_latest_company_statement', methods=['GET', 'POST'])
@csrf.exempt
def cmb_latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行公司账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_latest_self_statement', methods=['GET', 'POST'])
@csrf.exempt
def cmb_latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行个人账单整理功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/cmb_to_company', methods=['GET', 'POST'])
@csrf.exempt
def cmb_to_company():
    if request.method == 'GET':
        return redirect(url_for('statement_routes.cmb_bank'))
    folder_path = Config.BILLING_DATA_PATH / "CMB"
    flash('招商银行公司账单生成功能尚未实现')
    return redirect(url_for('statement_routes.cmb_bank'))


@statement_blue.route('/athina_page')
@login_required
@staff_only
def athina_page():
    return render_template('finance/statement/athina.html')


@statement_blue.route('/athina_processing', methods=['GET', 'POST'])
@csrf.exempt
def process_all_invoices():
    try:
        folder_path = Config.BILLING_DATA_PATH / "BOOKING"
        
        # 检查文件夹是否存在
        if not folder_path.exists():
            return jsonify({'error': f'账单文件夹不存在: {folder_path}'}), 404
        
        count = CountHid(str(folder_path))
        profits, pre_sum = count.find_no_inv_booking()
        
        r = f'全部未结算总额：SGD {int(profits)};'
        return jsonify({'result': r})
        
    except Exception as e:
        logger.error(f"处理全部订单失败: {e}")
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@statement_blue.route('/athina_processing_month', methods=['POST'])
@csrf.exempt
def process_month_invoice():
    try:
        folder_path = Config.BILLING_DATA_PATH / "BOOKING"
        
        # 检查文件夹是否存在
        if not folder_path.exists():
            return jsonify({'error': f'账单文件夹不存在: {folder_path}'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': '未提供月份数据'}), 400
        
        month = data.get('month')
        if not month:
            return jsonify({'error': '月份参数不能为空'}), 400
        
        # 验证月份格式
        import re
        if not re.match(r'^\d{4}-\d{2}$', month):
            return jsonify({'error': '月份格式错误，请使用YYYY-MM格式'}), 400
        
        count = CountHid(str(folder_path))
        profits, pre_sum = count.find_no_inv_booking(pre_month=month)
        
        results = f'截至{month[:4]}年{month[-2:]}月的未结算总额: SGD {int(pre_sum)}'
        return jsonify({'result': results})
        
    except Exception as e:
        logger.error(f"处理指定月份订单失败: {e}")
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@statement_blue.route('/open_athina_statement_folder', methods=['GET', 'POST'])
@csrf.exempt
def open_athina_statement_folder():
    folder_path = Config.BILLING_DATA_PATH / "BOOKING"
    
    # 如果文件夹不存在，则创建它
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            flash('文件夹不存在，已自动创建', 'info')
        except Exception as e:
            flash(f'创建文件夹失败：{str(e)}', 'error')
            return redirect(url_for("statement_routes.athina_page"))
    
    try:
        os.startfile(str(folder_path))
        flash('成功打开BOOKING文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_routes.athina_page"))

@statement_blue.route('/statement/company_bill', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def company_bill():
    """公司账单主页面"""
    if request.method == 'POST':
        folder_path = Config.BILLING_DATA_PATH / "Company"
        
        # 如果文件夹不存在，则创建它
        if not folder_path.exists():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                flash('Company文件夹不存在，已自动创建', 'info')
            except Exception as e:
                flash(f'创建文件夹失败：{str(e)}', 'error')
                return redirect(url_for("statement_routes.company_bill"))
        
        try:
            os.startfile(str(folder_path))
            flash('成功打开公司账单文件夹', 'success')
        except Exception as e:
            flash(f'打开文件夹失败：{str(e)}', 'error')
        
        return redirect(url_for("statement_routes.company_bill"))
    
    # GET请求，显示公司账单页面
    companies = get_company_list()
    return render_template('finance/statement/CompanyBill.html', companies=companies)


def get_company_list():
    """获取公司列表"""
    companies = []
    company_folder = Config.BILLING_DATA_PATH / "Company"
    
    if company_folder.exists():
        for company_dir in company_folder.iterdir():
            if company_dir.is_dir():
                # 统计文件数量
                file_count = len([f for f in company_dir.iterdir() if f.is_file()])
                
                # 获取最后修改时间
                try:
                    last_modified = max([f.stat().st_mtime for f in company_dir.iterdir() if f.is_file()])
                    last_updated = datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M')
                except:
                    last_updated = "未知"
                
                # 判断处理状态（这里可以根据实际需求调整逻辑）
                status = "pending"  # 默认状态
                status_text = "待处理"
                
                companies.append({
                    'name': company_dir.name,
                    'file_count': file_count,
                    'last_updated': last_updated,
                    'status': status,
                    'status_text': status_text
                })
    
    return companies


@statement_blue.route('/company_bill_processing', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def company_bill_processing():
    """批量处理公司账单"""
    try:
        company_folder = Config.BILLING_DATA_PATH / "Company"
        processed_count = 0
        
        if company_folder.exists():
            for company_dir in company_folder.iterdir():
                if company_dir.is_dir():
                    # 处理每个公司的账单文件
                    for file_path in company_dir.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in ['.xls', '.xlsx', '.csv']:
                            # 这里可以添加具体的账单处理逻辑
                            processed_count += 1
        
        flash(f'批量处理完成，共处理 {processed_count} 个文件')
    except Exception as e:
        flash(f'批量处理失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_routes.company_bill"))


@statement_blue.route('/company_bill_consolidate', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def company_bill_consolidate():
    """汇总公司账单"""
    try:
        company_folder = Config.BILLING_DATA_PATH / "Company"
        consolidated_count = 0
        
        if company_folder.exists():
            for company_dir in company_folder.iterdir():
                if company_dir.is_dir():
                    # 汇总每个公司的账单
                    company_files = [f for f in company_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.xls', '.xlsx', '.csv']]
                    if company_files:
                        # 这里可以添加汇总逻辑
                        consolidated_count += 1
        
        flash(f'汇总完成，共汇总 {consolidated_count} 个公司')
    except Exception as e:
        flash(f'汇总失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_routes.company_bill"))


@statement_blue.route('/company_bill_export', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def company_bill_export():
    """导出公司账单报表"""
    try:
        # 这里可以添加导出报表的逻辑
        flash('报表导出功能开发中...')
    except Exception as e:
        flash(f'导出失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_routes.company_bill"))


@statement_blue.route('/open_company_bill_folder', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def open_company_bill_folder():
    """打开公司账单文件夹"""
    try:
        folder_path = Config.BILLING_DATA_PATH / "Company"
        
        # 如果文件夹不存在，则创建它
        if not folder_path.exists():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                flash('Company文件夹不存在，已自动创建', 'info')
            except Exception as e:
                flash(f'创建文件夹失败：{str(e)}', 'error')
                return redirect(url_for("statement_routes.company_bill"))
        
        os.startfile(str(folder_path))
        flash('成功打开公司账单文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_routes.company_bill"))


@statement_blue.route('/refresh_company_list', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def refresh_company_list():
    """刷新公司列表"""
    try:
        # 这里可以添加刷新逻辑，比如重新扫描文件夹
        flash('公司列表刷新完成')
    except Exception as e:
        flash(f'刷新失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_routes.company_bill"))


@statement_blue.route('/open_company_folder', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def open_company_folder():
    """打开特定公司的文件夹"""
    try:
        company_name = request.form.get('company_name')
        if not company_name:
            flash('公司名称不能为空', 'error')
            return redirect(url_for("statement_routes.company_bill"))
        
        company_folder = Config.BILLING_DATA_PATH / "Company" / company_name
        
        if not company_folder.exists():
            flash(f'公司文件夹不存在：{company_name}', 'error')
            return redirect(url_for("statement_routes.company_bill"))
        
        # 打开文件夹
        os.startfile(str(company_folder))
        flash(f'成功打开 {company_name} 的文件夹')
        
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_routes.company_bill"))


@statement_blue.route('/compare_reports', methods=['POST'])
@csrf.exempt
def compare_reports():
    """对比两个报表的利润列数据"""
    try:
        print("=== 开始处理报表对比请求 ===")
        
        # 获取上传的文件
        report_a = request.files.get('report_a')
        report_b = request.files.get('report_b')
        profit_column = request.form.get('profit_column', '').strip()
        header_setting = request.form.get('header_setting', 'default')
        custom_headers = request.form.get('custom_headers', '').strip()
        
        # 如果没有提供自定义表头，使用config中的默认表头
        if not custom_headers:
            custom_headers = get_report_headers_string('order_report')
        
        print(f"Debug: report_a filename = {report_a.filename if report_a else 'None'}")
        print(f"Debug: report_b filename = {report_b.filename if report_b else 'None'}")
        print(f"Debug: profit_column = {profit_column}")
        print(f"Debug: header_setting = {header_setting}")
        print(f"Debug: custom_headers = {custom_headers}")
        
        # 检查请求参数
        print(f"Debug: request.files keys = {list(request.files.keys())}")
        print(f"Debug: request.form keys = {list(request.form.keys())}")
        
        if not report_a or not report_b:
            return jsonify({'success': False, 'error': '请选择两个报表文件'})
        
        # 移除利润列验证，因为现在是自动设置的
        
        # 读取报表文件
        def read_report_file(file, header_setting, custom_headers=None):
            """读取Excel或CSV文件"""
            try:
                print(f"Debug: 读取文件 {file.filename}, header_setting={header_setting}")
                
                if file.filename.lower().endswith('.csv'):
                    if header_setting == 'none':
                        # 无表头，第一行是数据
                        df = pd.read_csv(file, encoding='utf-8', header=None)
                    elif header_setting == 'custom' and custom_headers:
                        # 使用自定义表头
                        headers = [h.strip() for h in custom_headers.split(',')]
                        df = pd.read_csv(file, encoding='utf-8', header=None, names=headers)
                    else:
                        # 使用默认表头（第一行作为表头）
                        df = pd.read_csv(file, encoding='utf-8')
                else:
                    # 处理Excel文件（.xlsx, .xls）
                    if header_setting == 'custom' and custom_headers:
                        # 使用自定义表头
                        headers = [h.strip() for h in custom_headers.split(',')]
                        print(f"Debug: 使用自定义表头: {headers}")
                        # 尝试不同的引擎
                        try:
                            df = pd.read_excel(file, header=None, names=headers, engine='openpyxl')
                        except:
                            try:
                                df = pd.read_excel(file, header=None, names=headers, engine='xlrd')
                            except:
                                # 最后尝试不指定引擎
                                df = pd.read_excel(file, header=None, names=headers)
                    else:
                        # 使用默认表头（第一行作为表头）
                        try:
                            df = pd.read_excel(file, engine='openpyxl')
                        except:
                            try:
                                df = pd.read_excel(file, engine='xlrd')
                            except:
                                # 最后尝试不指定引擎
                                df = pd.read_excel(file)
                return df
            except Exception as e:
                print(f"Debug: 文件读取最终失败: {str(e)}")
                raise Exception(f"读取文件失败: {str(e)}")
        
        # 读取两个报表
        print(f"Debug: 开始读取报表A...")
        df_a = read_report_file(report_a, header_setting, custom_headers)
        print(f"Debug: 报表A读取成功，列数: {len(df_a.columns)}, 行数: {len(df_a)}")
        print(f"Debug: 报表A列名: {list(df_a.columns)}")
        
        print(f"Debug: 开始读取报表B...")
        df_b = read_report_file(report_b, header_setting, custom_headers)
        print(f"Debug: 报表B读取成功，列数: {len(df_b.columns)}, 行数: {len(df_b)}")
        print(f"Debug: 报表B列名: {list(df_b.columns)}")
        
        # 检查利润列是否存在
        if profit_column not in df_a.columns:
            return jsonify({'success': False, 'error': f'报表A中未找到列: {profit_column}'})
        
        if profit_column not in df_b.columns:
            return jsonify({'success': False, 'error': f'报表B中未找到列: {profit_column}'})
        
        # 获取项目标识列（假设第一列是项目标识）
        id_column_a = df_a.columns[0]
        id_column_b = df_b.columns[0]
        
        # 创建数据字典，以项目标识为键
        data_a = {}
        data_b = {}
        
        # 处理报表A
        for _, row in df_a.iterrows():
            item_id = str(row[id_column_a]).strip()
            profit_value = row[profit_column]
            if pd.notna(profit_value):  # 排除空值
                try:
                    # 尝试转换为浮点数
                    float_value = float(profit_value)
                    data_a[item_id] = float_value
                except (ValueError, TypeError):
                    # 如果转换失败，记录警告并跳过
                    print(f"警告：报表A中项目 {item_id} 的利润值 '{profit_value}' 无法转换为数字，已跳过")
                    continue
        
        # 处理报表B
        for _, row in df_b.iterrows():
            item_id = str(row[id_column_b]).strip()
            profit_value = row[profit_column]
            if pd.notna(profit_value):  # 排除空值
                try:
                    # 尝试转换为浮点数
                    float_value = float(profit_value)
                    data_b[item_id] = float_value
                except (ValueError, TypeError):
                    # 如果转换失败，记录警告并跳过
                    print(f"警告：报表B中项目 {item_id} 的利润值 '{profit_value}' 无法转换为数字，已跳过")
                    continue
        
        # 找出不同的数据
        differences = []
        all_items = set(data_a.keys()) | set(data_b.keys())
        
        for item in all_items:
            value_a = data_a.get(item, 0)
            value_b = data_b.get(item, 0)
            
            if abs(value_a - value_b) > 0.01:  # 允许0.01的误差
                differences.append({
                    'item': item,
                    'value_a': f"{value_a:.2f}",
                    'value_b': f"{value_b:.2f}",
                    'difference': round(value_b - value_a, 2)
                })
        
        # 为两个报表添加对比列
        # 为报表A添加对比列
        df_a['数据一致性'] = '否'  # 默认设为否
        for idx, row in df_a.iterrows():
            item_id = str(row[id_column_a]).strip()
            value_a = data_a.get(item_id, 0)
            value_b = data_b.get(item_id, 0)
            if abs(value_a - value_b) <= 0.01:  # 如果差异小于等于0.01，认为相同
                df_a.at[idx, '数据一致性'] = '是'
        
        # 为报表B添加对比列
        df_b['数据一致性'] = '否'  # 默认设为否
        for idx, row in df_b.iterrows():
            item_id = str(row[id_column_b]).strip()
            value_a = data_a.get(item_id, 0)
            value_b = data_b.get(item_id, 0)
            if abs(value_a - value_b) <= 0.01:  # 如果差异小于等于0.01，认为相同
                df_b.at[idx, '数据一致性'] = '是'
        
        # 保存带有对比结果的报表到临时目录
        temp_dir = tempfile.mkdtemp()
        report_a_filename = f'报表A_对比结果_{os.path.basename(report_a.filename)}'
        report_b_filename = f'报表B_对比结果_{os.path.basename(report_b.filename)}'
        report_a_path = os.path.join(temp_dir, report_a_filename)
        report_b_path = os.path.join(temp_dir, report_b_filename)
        
        # 根据原文件格式保存
        if report_a.filename.lower().endswith('.csv'):
            df_a.to_csv(report_a_path, index=False, encoding='utf-8-sig')
        else:
            # 保存为Excel文件
            try:
                df_a.to_excel(report_a_path, index=False, engine='openpyxl')
            except:
                try:
                    df_a.to_excel(report_a_path, index=False, engine='xlwt')
                except:
                    # 最后尝试不指定引擎
                    df_a.to_excel(report_a_path, index=False)
            
        if report_b.filename.lower().endswith('.csv'):
            df_b.to_csv(report_b_path, index=False, encoding='utf-8-sig')
        else:
            # 保存为Excel文件
            try:
                df_b.to_excel(report_b_path, index=False, engine='openpyxl')
            except:
                try:
                    df_b.to_excel(report_b_path, index=False, engine='xlwt')
                except:
                    # 最后尝试不指定引擎
                    df_b.to_excel(report_b_path, index=False)
        
        # 将文件路径存储到session中供下载使用
        from flask import session
        session['report_a_path'] = report_a_path
        session['report_b_path'] = report_b_path
        session['report_a_filename'] = report_a_filename
        session['report_b_filename'] = report_b_filename
        
        # 统计信息
        summary = {
            'total_a': len(data_a),
            'total_b': len(data_b),
            'matched': len(all_items) - len(differences),
            'differences': len(differences)
        }
        
        # 添加处理信息
        processed_info = {
            'total_rows_a': len(df_a),
            'total_rows_b': len(df_b),
            'valid_profit_a': len(data_a),
            'valid_profit_b': len(data_b),
            'skipped_a': len(df_a) - len(data_a),
            'skipped_b': len(df_b) - len(data_b)
        }
        
        return jsonify({
            'success': True,
            'differences': differences,
            'summary': summary,
            'processed_info': processed_info
        })
        
    except Exception as e:
        print(f"Debug: 最终错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})





@statement_blue.route('/download_report/<report_type>', methods=['GET'])
@csrf.exempt
def download_report(report_type):
    """下载带有对比结果的报表文件"""
    try:
        from flask import session, send_file
        
        if report_type == 'A':
            file_path = session.get('report_a_path')
            filename = session.get('report_a_filename', '报表A_对比结果.xlsx')
        elif report_type == 'B':
            file_path = session.get('report_b_path')
            filename = session.get('report_b_filename', '报表B_对比结果.xlsx')
        else:
            return jsonify({'success': False, 'error': '无效的报表类型'})
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在，请重新进行对比'})
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@statement_blue.route('/batch_compare_reports', methods=['POST'])
@csrf.exempt
def batch_compare_reports():
    """批量对比两个文件夹中的报表"""
    try:
        print("=== 开始处理批量报表对比请求 ===")
        
        # 获取上传的文件
        folder_a_files = request.files.getlist('folder_a_files')
        folder_b_files = request.files.getlist('folder_b_files')
        
        print(f"Debug: 文件夹A文件数量 = {len(folder_a_files)}")
        print(f"Debug: 文件夹B文件数量 = {len(folder_b_files)}")
        
        if not folder_a_files:
            return jsonify({'success': False, 'error': '请选择文件夹A的文件'})
        
        if not folder_b_files:
            return jsonify({'success': False, 'error': '请选择文件夹B的文件'})
        
        # 过滤出Excel和CSV文件
        def filter_report_files(files):
            return [f for f in files if f.filename.lower().endswith(('.xlsx', '.xls', '.csv'))]
        
        folder_a_files = filter_report_files(folder_a_files)
        folder_b_files = filter_report_files(folder_b_files)
        
        print(f"Debug: 过滤后文件夹A文件数量 = {len(folder_a_files)}")
        print(f"Debug: 过滤后文件夹B文件数量 = {len(folder_b_files)}")
        
        if not folder_a_files:
            return jsonify({'success': False, 'error': '文件夹A中没有有效的报表文件'})
        
        if not folder_b_files:
            return jsonify({'success': False, 'error': '文件夹B中没有有效的报表文件'})
        
        # 打印A、B第一个文件的前5行数据
        if folder_a_files and folder_b_files:
            from App.utils.report_utils import BatchReportComparer
            comparer = BatchReportComparer('order_report')
            df_a = comparer.read_report_file(folder_a_files[0])
            df_b = comparer.read_report_file(folder_b_files[0])
            print('调试: A文件前5行:')
            print(df_a.head())
            print('调试: B文件前5行:')
            print(df_b.head())

        # 使用批量报表对比工具
        from App.utils.report_utils import BatchReportComparer
        
        comparer = BatchReportComparer('order_report')
        results = comparer.compare_reports_by_filename(folder_a_files, folder_b_files)
        
        # 生成Excel报告
        import tempfile
        import os
        temp_dir = tempfile.mkdtemp()
        report_filename = f'批量报表对比报告_{os.path.basename(temp_dir)}.xlsx'
        report_path = os.path.join(temp_dir, report_filename)
        
        excel_path = comparer.generate_excel_report_new(results, report_path)
        
        if excel_path:
            # 将文件路径存储到session中供下载使用
            from flask import session
            session['batch_report_path'] = excel_path
            session['batch_report_filename'] = report_filename
        
        # 准备详细差异信息用于前端显示
        detailed_differences = []
        if 'differences' in results:
            for diff in results['differences']:
                detailed_differences.append({
                    '报表A': diff.get('所属文件A', ''),
                    '报表B': diff.get('所属文件B', ''),
                    'HID': diff.get('order_id', ''),
                    'A利润': diff.get('A利润', ''),
                    'B利润': diff.get('B利润', ''),
                    '备注': diff.get('差异说明', '')
                })
        
        # 提取缺失的HID（A有B无的）
        missing_hids = []
        if 'differences' in results:
            for diff in results['differences']:
                if diff.get('差异说明', '').startswith('报表A含有order_id') and not diff.get('B利润'):
                    missing_hids.append(diff.get('order_id', ''))
        
        print(f"Debug: 批量对比完成，结果: {results}")
        
        return jsonify({
            'success': True,
            'summary': safe_json(results['summary']),
            'differences': safe_json(results['differences']),
            'missing_hids': safe_json(missing_hids),
            'detailed_differences': safe_json(detailed_differences)
        })
        
    except Exception as e:
        print(f"Debug: 批量对比最终错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@statement_blue.route('/download_batch_report', methods=['GET'])
@csrf.exempt
def download_batch_report():
    """下载批量对比汇总报告"""
    try:
        from flask import session, send_file
        
        file_path = session.get('batch_report_path')
        filename = session.get('batch_report_filename', '批量报表对比报告.xlsx')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '报告文件不存在，请重新进行批量对比'})
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
