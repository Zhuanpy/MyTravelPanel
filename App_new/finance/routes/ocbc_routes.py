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
from .statement_utils import analyze_excel_structure, apply_keyword_matching, process_monthly_transactions
# safe_json 已从 Config 类中移除，不再需要

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
ocbc_blue = Blueprint('ocbc_routes', __name__)




# OCBC银行相关路由
@ocbc_blue.route('/ocbc_bank')
@login_required
@staff_only
def ocbc_bank():
    # 获取筛选参数
    month_param = request.args.get('month', '')
    
    # 如果没有指定月份，默认使用最新一个月
    if not month_param:
        # 查询OCBC银行最新的交易记录，获取最新的月份
        latest_transaction = BankTransaction.query.join(BankStatement).filter(
            BankStatement.bank_name == 'OCBC'
        ).order_by(desc(BankTransaction.transaction_date)).first()
        
        if latest_transaction:
            # 使用最新交易记录的年份和月份
            latest_date = latest_transaction.transaction_date
            month_param = f"{latest_date.year}-{latest_date.month:02d}"
        else:
            # 如果没有交易记录，使用当前月份
            now = datetime.now()
            month_param = f"{now.year}-{now.month:02d}"
    
    filters = {
        'month': month_param,
        'start_date': request.args.get('start_date', ''),
        'end_date': request.args.get('end_date', ''),
        'type': request.args.get('type', ''),
        'owner': request.args.get('owner', ''),
        'ref': request.args.get('ref', ''),
        'operation_status': request.args.get('operation_status', ''),
        'sort': request.args.get('sort', 'date_desc')
    }
    
    # 获取OCBC银行的对账单数据，按创建时间降序排列
    statements = BankStatement.query.filter(
        BankStatement.bank_name == 'OCBC'
    ).order_by(desc(BankStatement.created_at)).limit(10).all()
    
    # 获取OCBC银行的交易数据
    transactions_query = BankTransaction.query.join(BankStatement).filter(
        BankStatement.bank_name == 'OCBC'
    )
    
    # 应用筛选条件
    if filters['month']:
        # 月份筛选：格式为 YYYY-MM
        year, month = filters['month'].split('-')
        transactions_query = transactions_query.filter(
            db.func.extract('year', BankTransaction.transaction_date) == int(year),
            db.func.extract('month', BankTransaction.transaction_date) == int(month)
        )
    
    if filters['start_date']:
        transactions_query = transactions_query.filter(
            BankTransaction.transaction_date >= datetime.strptime(filters['start_date'], '%Y-%m-%d').date()
        )
    
    if filters['end_date']:
        transactions_query = transactions_query.filter(
            BankTransaction.transaction_date <= datetime.strptime(filters['end_date'], '%Y-%m-%d').date()
        )
    
    if filters['type']:
        transactions_query = transactions_query.filter(
            BankTransaction.transaction_type == filters['type']
        )
    
    if filters['owner']:
        if filters['owner'] == '__blank__':
            transactions_query = transactions_query.filter(
                db.or_(BankTransaction.owner_label == None, BankTransaction.owner_label == '')
            )
        else:
            transactions_query = transactions_query.filter(
                BankTransaction.owner_label == filters['owner']
            )
    
    if filters['ref']:
        transactions_query = transactions_query.filter(
            BankTransaction.accounting_ref.like(f'%{filters["ref"]}%')
        )
    
    if filters['operation_status']:
        if filters['operation_status'] == 'confirmed':
            transactions_query = transactions_query.filter(
                BankTransaction.is_confirmed == True
            )
        elif filters['operation_status'] == 'unconfirmed':
            transactions_query = transactions_query.filter(
                BankTransaction.is_confirmed == False
            )
    
    # 应用排序
    if filters['sort'] == 'date_desc':
        transactions_query = transactions_query.order_by(desc(BankTransaction.transaction_date))
    elif filters['sort'] == 'date_asc':
        transactions_query = transactions_query.order_by(BankTransaction.transaction_date)
    elif filters['sort'] == 'amount_desc':
        transactions_query = transactions_query.order_by(desc(BankTransaction.amount))
    elif filters['sort'] == 'amount_asc':
        transactions_query = transactions_query.order_by(BankTransaction.amount)
    
    # 分页处理
    page = request.args.get('page', 1, type=int)
    pagination = transactions_query.paginate(page=page, per_page=30, error_out=False)
    transactions = pagination.items
    
    # 获取归属选项
    owner_options = ['Business', 'LG', 'JE', '个人消费', '个人商用']
    
    # 检查是否是AJAX请求（只返回表格部分）
    if request.args.get('partial') == 'table':
        return render_template('finance/statement/_ocbc_tx_table.html', 
                             transactions=transactions, 
                             pagination=pagination, 
                             filters=filters)
    
    return render_template('finance/statement/UnifiedBank.html',
                         bank_name='OCBC',
                         transactions=transactions,
                         pagination=pagination,
                         filters=filters,
                         statements=statements,
                         owner_options=owner_options)


@ocbc_blue.route('/download_ocbc_statement/<statement_number>')
@login_required
@staff_only
def download_ocbc_statement(statement_number):
    """下载OCBC对账单"""
    try:
        # 查找对账单
        statement = BankStatement.query.filter_by(
            statement_number=statement_number,
            bank_name='OCBC'
        ).first()
        
        if not statement:
            flash(f'对账单 {statement_number} 不存在', 'error')
            return redirect(url_for('ocbc_routes.ocbc_bank'))
        
        # 这里应该生成对账单文件，暂时返回提示
        flash('对账单下载功能正在开发中', 'info')
        return redirect(url_for('ocbc_routes.ocbc_bank'))
        
    except Exception as e:
        flash(f'下载对账单失败: {str(e)}', 'error')
        return redirect(url_for('ocbc_routes.ocbc_bank'))


@ocbc_blue.route('/delete_ocbc_statement', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_ocbc_statement():
    """删除OCBC对账单"""
    try:
        statement_number = request.form.get('statement_number')
        
        if not statement_number:
            flash('对账单号不能为空', 'error')
            return redirect(url_for('ocbc_routes.ocbc_bank'))
        
        # 查找对账单
        statement = BankStatement.query.filter_by(
            statement_number=statement_number,
            bank_name='OCBC'
        ).first()
        
        if not statement:
            flash(f'对账单 {statement_number} 不存在', 'error')
            return redirect(url_for('ocbc_routes.ocbc_bank'))
        
        # 删除相关的交易记录
        BankTransaction.query.filter_by(statement_id=statement.id).delete()
        
        # 删除对账单
        db.session.delete(statement)
        db.session.commit()
        
        flash(f'成功删除对账单 {statement_number}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除对账单失败: {str(e)}', 'error')
    
    return redirect(url_for('ocbc_routes.ocbc_bank'))


@ocbc_blue.route('/ocbc_tx_update', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def ocbc_tx_update():
    """更新OCBC银行交易记录"""
    try:
        data = request.get_json()
        
        if not data or 'id' not in data:
            return jsonify({'success': False, 'message': '缺少交易记录ID'})
        
        transaction_id = data['id']
        
        # 查找交易记录
        transaction = BankTransaction.query.get(transaction_id)
        
        if not transaction:
            return jsonify({'success': False, 'message': '交易记录不存在'})
        
        # 更新字段
        if 'counterparty_name' in data:
            transaction.counterparty_name = data['counterparty_name']
        
        if 'remarks' in data:
            transaction.remarks = data['remarks']
        
        if 'owner_label' in data:
            transaction.owner_label = data['owner_label']
        
        if 'accounting_ref' in data:
            transaction.accounting_ref = data['accounting_ref']
        
        if 'keyword' in data:
            transaction.keyword = data['keyword']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '交易记录更新成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})


@ocbc_blue.route('/ocbc_tx_confirm', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def ocbc_tx_confirm():
    """确认OCBC银行交易记录"""
    try:
        data = request.get_json()
        
        if not data or 'id' not in data:
            return jsonify({'success': False, 'message': '缺少交易记录ID'})
        
        transaction_id = data['id']
        
        # 查找交易记录
        transaction = BankTransaction.query.get(transaction_id)
        
        if not transaction:
            return jsonify({'success': False, 'message': '交易记录不存在'})
        
        # 确认交易记录
        transaction.is_confirmed = True
        transaction.confirmed_at = datetime.now()
        transaction.confirmed_by = 'user'  # 这里可以改为实际的用户名
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '交易记录确认成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'确认失败: {str(e)}'})


@ocbc_blue.route('/ocbc_batch_confirm', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def ocbc_batch_confirm():
    """批量确认OCBC银行交易记录"""
    try:
        data = request.get_json()
        
        if not data or 'transaction_ids' not in data:
            return jsonify({'success': False, 'message': '缺少交易记录ID列表'})
        
        transaction_ids = data['transaction_ids']
        
        if not isinstance(transaction_ids, list) or len(transaction_ids) == 0:
            return jsonify({'success': False, 'message': '交易记录ID列表不能为空'})
        
        # 查找所有交易记录
        transactions = BankTransaction.query.filter(
            BankTransaction.id.in_(transaction_ids),
            BankTransaction.is_confirmed == False  # 只处理未确认的交易
        ).all()
        
        if not transactions:
            return jsonify({'success': False, 'message': '没有找到需要确认的交易记录'})
        
        # 批量确认交易记录
        confirmed_count = 0
        for transaction in transactions:
            transaction.is_confirmed = True
            transaction.confirmed_at = datetime.utcnow()
            transaction.confirmed_by = 'staff'  # 这里可以改为当前用户信息
            confirmed_count += 1
        
        # 保存更改
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'成功确认 {confirmed_count} 个交易记录',
            'confirmed_count': confirmed_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'批量确认失败: {str(e)}'}), 500


@ocbc_blue.route('/open_ocbc_statement_folder', methods=['GET', 'POST'])
@csrf.exempt
def open_ocbc_statement_folder():
    if request.method == 'GET':
        return redirect(url_for('ocbc_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    
    # 如果文件夹不存在，则创建它
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            flash('OCBC文件夹不存在，已自动创建', 'info')
        except Exception as e:
            flash(f'创建文件夹失败：{str(e)}', 'error')
            return redirect(url_for('ocbc_routes.ocbc_bank'))
    
    try:
        subprocess.run(['explorer', str(folder_path)], shell=True)
        flash('成功打开OCBC账单文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for('ocbc_routes.ocbc_bank'))


@ocbc_blue.route('/ocbc_bank_processing', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_bank_processing():
    if request.method == 'GET':
        return redirect(url_for('ocbc_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC账单整理功能尚未实现')
    return redirect(url_for('ocbc_routes.ocbc_bank'))


@ocbc_blue.route('/ocbc_original_processing', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_original_processing():
    if request.method == 'GET':
        return redirect(url_for('ocbc_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC原始账单整理功能尚未实现')
    return redirect(url_for('ocbc_routes.ocbc_bank'))


@ocbc_blue.route('/ocbc_latest_company_statement', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('ocbc_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC公司账单整理功能尚未实现')
    return redirect(url_for('ocbc_routes.ocbc_bank'))


@ocbc_blue.route('/ocbc_latest_self_statement', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('ocbc_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC个人账单整理功能尚未实现')
    return redirect(url_for('ocbc_routes.ocbc_bank'))


@ocbc_blue.route('/ocbc_to_company', methods=['GET', 'POST'])
@csrf.exempt
def ocbc_to_company():
    if request.method == 'GET':
        return redirect(url_for('ocbc_routes.ocbc_bank'))
    folder_path = Config.BILLING_DATA_PATH / "OCBC"
    flash('OCBC公司账单生成功能尚未实现')
    return redirect(url_for('ocbc_routes.ocbc_bank'))

