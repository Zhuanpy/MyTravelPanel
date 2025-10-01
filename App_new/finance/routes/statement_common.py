from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash, send_file
from flask_login import login_required
from App_new.utils.Statement import OriginalStatement
from App_new.utils.Invoice import CountHid
from App_new.exts import db
from App_new.finance.models.statement import BankStatement, BankTransaction
from App_new.finance.models.bank_keywords import BankStatementKeyword
import os
import logging
from App_new.config import Config
import subprocess
import pandas as pd
import tempfile
from datetime import datetime, timedelta
from App_new.exts import csrf
from App_new.utils.decorators import staff_only
from sqlalchemy import desc
from App_new.utils.report_utils import (
    get_report_headers_string,
    read_excel_file,
    read_csv_file,
    compare_profit_columns,
    add_comparison_column
)
# safe_json 已从 Config 类中移除，不再需要

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
statement_common_blue = Blueprint('statement_common_routes', __name__)


@statement_common_blue.route('/open_uob_statement_folder', methods=['GET', 'POST'])
@csrf.exempt
def open_uob_statement_folder():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    
    # 如果文件夹不存在，则创建它
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            flash('UOB文件夹不存在，已自动创建', 'info')
        except Exception as e:
            flash(f'创建文件夹失败：{str(e)}', 'error')
            return redirect(url_for('uob_routes.uob_bank'))
    
    try:
        subprocess.run(['explorer', str(folder_path)], shell=True)
        flash('成功打开UOB账单文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for('uob_routes.uob_bank'))









@statement_common_blue.route('/latest_company_statement', methods=['GET', 'POST'])
@csrf.exempt
def latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.latest_company_statement()
    flash('公司账单整理完成')
    return redirect(url_for('uob_routes.uob_bank'))


@statement_common_blue.route('/latest_self_statement', methods=['GET', 'POST'])
@csrf.exempt
def latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.latest_self_statement()
    flash('个人账单整理完成')
    return redirect(url_for('uob_routes.uob_bank'))


@statement_common_blue.route('/statement_to_company', methods=['GET', 'POST'])
@csrf.exempt
def statement_to_company():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.statement_to_company()
    flash('最终公司账单生成完成')
    return redirect(url_for('uob_routes.uob_bank'))

