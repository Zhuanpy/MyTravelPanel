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
    
    # 如果没有指定月份，显示全部数据（不设置默认月份）
    
    filters = {
        'account_name': request.args.get('account_name', ''),
        'month': month_param,
        'start_date': request.args.get('start_date', ''),
        'end_date': request.args.get('end_date', ''),
        'type': request.args.get('type', ''),
        'owner': request.args.get('owner', ''),
        'ref': request.args.get('ref', ''),
        'operation_status': request.args.get('operation_status', ''),
        'sort': request.args.get('sort', 'date_desc')
    }
    
    # 获取OCBC银行的对账单数据，按对账单号（月份）降序排列
    statements_query = BankStatement.query.filter(
        BankStatement.bank_name == 'OCBC'
    )
    # 如果选择了账户，筛选对账单
    if filters['account_name']:
        statements_query = statements_query.filter(
            BankStatement.account_name == filters['account_name']
        )
    statements = statements_query.order_by(desc(BankStatement.statement_number)).limit(10).all()
    
    # 更新每个对账单的状态（基于交易确认状态）
    for statement in statements:
        statement.update_status_based_on_transactions()
    
    # 提交状态更新到数据库
    if statements:
        db.session.commit()
    
    # 获取OCBC银行的交易数据
    transactions_query = BankTransaction.query.join(BankStatement).filter(
        BankStatement.bank_name == 'OCBC'
    )

    # 应用筛选条件
    # 账户名称筛选
    if filters['account_name']:
        transactions_query = transactions_query.filter(
            BankStatement.account_name == filters['account_name']
        )

    if filters['month']:
        # 月份筛选：格式为 YYYY-MM
        try:
            year, month = filters['month'].split('-')
            # 使用更简单的日期范围筛选
            from datetime import date
            start_date = date(int(year), int(month), 1)
            if int(month) == 12:
                end_date = date(int(year) + 1, 1, 1)
            else:
                end_date = date(int(year), int(month) + 1, 1)
            
            transactions_query = transactions_query.filter(
                BankTransaction.transaction_date >= start_date,
                BankTransaction.transaction_date < end_date
            )
        except Exception as e:
            print(f"月份筛选错误: {e}")
            # 如果月份解析失败，使用原来的方法
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
        print(f"应用操作状态筛选: {filters['operation_status']}")
        if filters['operation_status'] == 'confirmed':
            transactions_query = transactions_query.filter(
                BankTransaction.is_confirmed == True
            )
            print("筛选条件: is_confirmed = True")
        elif filters['operation_status'] == 'unconfirmed':
            transactions_query = transactions_query.filter(
                BankTransaction.is_confirmed == False
            )
            print("筛选条件: is_confirmed = False")
    
    # 应用排序
    if filters['sort'] == 'date_desc':
        transactions_query = transactions_query.order_by(desc(BankTransaction.transaction_date))
    elif filters['sort'] == 'date_asc':
        transactions_query = transactions_query.order_by(BankTransaction.transaction_date)
    elif filters['sort'] == 'amount_desc':
        transactions_query = transactions_query.order_by(desc(BankTransaction.amount))
    elif filters['sort'] == 'amount_asc':
        transactions_query = transactions_query.order_by(BankTransaction.amount)
    
    # 添加调试信息
    print(f"OCBC银行查询调试:")
    print(f"  筛选条件: {filters}")
    print(f"  查询语句: {transactions_query}")
    
    # 分页处理
    page = request.args.get('page', 1, type=int)
    pagination = transactions_query.paginate(page=page, per_page=30, error_out=False)
    transactions = pagination.items
    
    print(f"  查询结果: 找到 {len(transactions)} 个交易记录")
    print(f"  分页信息: 第 {pagination.page} 页 / 共 {pagination.pages} 页, 总计 {pagination.total} 条")
    
    # 添加操作状态调试信息
    if transactions:
        confirmed_count = sum(1 for tx in transactions if tx.is_confirmed)
        unconfirmed_count = len(transactions) - confirmed_count
        print(f"  当前页面操作状态统计: 已确认 {confirmed_count} 条, 未确认 {unconfirmed_count} 条")
    
    # 获取归属选项
    owner_options = ['Business', 'LG', 'JE', '个人消费', '个人商用']

    # 获取OCBC银行现有的账户名称列表（用于筛选和上传时选择）
    account_names = db.session.query(BankStatement.account_name).filter(
        BankStatement.bank_name == 'OCBC',
        BankStatement.account_name.isnot(None),
        BankStatement.account_name != '上传文件'
    ).distinct().order_by(BankStatement.account_name).all()
    account_name_options = [name[0] for name in account_names] if account_names else []

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
                         owner_options=owner_options,
                         account_name_options=account_name_options)


# OCBC下载和删除对账单功能已移至通用函数 statement_common.download_statement 和 statement_common.delete_statement


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
        
        # 处理确认状态
        if 'is_confirmed' in data:
            transaction.is_confirmed = data['is_confirmed']
            if data['is_confirmed']:
                transaction.confirmed_at = datetime.utcnow()
                transaction.confirmed_by = data.get('confirmed_by', 'system')
            else:
                transaction.confirmed_at = None
                transaction.confirmed_by = None
        
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


@ocbc_blue.route('/ocbc_unlock_transaction/<int:transaction_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def ocbc_unlock_transaction(transaction_id):
    """解锁已确认的OCBC银行交易记录，使其可以重新编辑"""
    try:
        # 查找交易记录
        transaction = BankTransaction.query.get(transaction_id)
        
        if not transaction:
            return jsonify({'success': False, 'message': '交易记录不存在'}), 404
        
        # 验证该交易是否属于OCBC银行
        if transaction.statement.bank_name != 'OCBC':
            return jsonify({'success': False, 'message': '该交易不属于OCBC银行'}), 400
        
        # 检查是否已确认
        if not transaction.is_confirmed:
            return jsonify({'success': False, 'message': '该交易尚未确认，无需解锁'})
        
        # 解锁交易记录
        transaction.is_confirmed = False
        transaction.confirmed_at = None
        transaction.confirmed_by = None
        
        # 保存更改
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '交易记录已解锁，现在可以重新编辑'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'解锁失败: {str(e)}'}), 500


# OCBC所有通用功能已移至通用函数 statement_common.py：
# - open_ocbc_statement_folder → statement_common.open_statement_folder
# - ocbc_bank_processing → statement_common.bank_processing  
# - ocbc_original_processing → statement_common.original_processing
# - ocbc_latest_company_statement → statement_common.latest_company_statement
# - ocbc_latest_self_statement → statement_common.latest_self_statement
# - ocbc_to_company → statement_common.to_company
# - ocbc_upload_file → statement_common.upload_file (已删除)

