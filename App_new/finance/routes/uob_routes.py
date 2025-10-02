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
uob_blue = Blueprint('uob_routes', __name__)


@uob_blue.route('/uob_bank')
@login_required
@staff_only
def uob_bank():
    # 获取筛选参数
    month_param = request.args.get('month', '')
    
    # 如果没有指定月份，显示全部数据（不设置默认月份）
    
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
    
    # 获取UOB银行的对账单数据，按对账单号（月份）降序排列
    statements = BankStatement.query.filter(
        BankStatement.bank_name == 'UOB'
    ).order_by(desc(BankStatement.statement_number)).limit(10).all()
    
    # 更新每个对账单的状态（基于交易确认状态）
    for statement in statements:
        statement.update_status_based_on_transactions()
    
    # 提交状态更新到数据库
    if statements:
        db.session.commit()
    
    # 获取UOB银行的交易数据
    transactions_query = BankTransaction.query.join(BankStatement).filter(
        BankStatement.bank_name == 'UOB'
    )
    
    # 应用筛选条件
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
    else:
        transactions_query = transactions_query.order_by(desc(BankTransaction.transaction_date))
    
    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 30  # 每页显示30条记录
    
    # 获取分页数据
    transactions_pagination = transactions_query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    transactions = transactions_pagination.items
    pagination = transactions_pagination
    
    # 获取可用的归属选项（从数据库或其他来源获取）
    owner_options = ['Business', 'LG', 'JE', '个人消费', '个人商用']
    
    # 检查是否是部分请求（AJAX筛选）
    if request.args.get('partial') == 'table':
        return render_template('finance/statement/_uob_tx_table.html', 
                             transactions=transactions,
                             filters=filters,
                             owner_options=owner_options,
                             pagination=pagination)
    
    return render_template('finance/statement/UnifiedBank.html',
                         bank_name='UOB',
                         statements=statements, 
                         transactions=transactions,
                         filters=filters,
                         owner_options=owner_options,
                         pagination=pagination)


# UOB下载和删除对账单功能已移至通用函数 statement_common.download_statement 和 statement_common.delete_statement


@uob_blue.route('/uob_tx_update', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def uob_tx_update():
    """更新UOB银行交易记录"""
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
        
        # 保存更改
        db.session.commit()
        
        return jsonify({'success': True, 'message': '交易记录更新成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500


@uob_blue.route('/uob_tx_confirm', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def uob_tx_confirm():
    """确认UOB银行交易记录"""
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
        transaction.confirmed_at = datetime.utcnow()
        transaction.confirmed_by = 'staff'  # 这里可以改为当前用户信息
        
        # 保存更改
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': '交易记录确认成功',
            'confirmed_at': transaction.confirmed_at.isoformat(),
            'confirmed_by': transaction.confirmed_by
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'确认失败: {str(e)}'}), 500


@uob_blue.route('/uob_batch_confirm', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def uob_batch_confirm():
    """批量确认UOB银行交易记录"""
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


@uob_blue.route('/uob_create_test_data', methods=['GET'])
@login_required
@staff_only
def uob_create_test_data():
    """创建UOB测试数据"""
    try:
        from datetime import date, datetime
        
        # 创建测试对账单
        test_statement = BankStatement(
            statement_number='UOB-TEST-001',
            bank_name='UOB',
            account_number='1234567890',
            account_name='TEST ACCOUNT',
            statement_date=date.today(),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            opening_balance=1000.00,
            closing_balance=1200.00,
            currency='SGD',
            status='draft',
            created_by='test'
        )
        
        db.session.add(test_statement)
        db.session.flush()  # 获取ID
        
        # 创建测试交易记录（确保有未确认的交易用于测试）
        test_transactions = [
            BankTransaction(
                statement_id=test_statement.id,
                transaction_date=date(2024, 1, 15),
                post_date=date(2024, 1, 15),
                transaction_id='TXN001',
                transaction_type='debit',
                amount=100.00,
                balance=900.00,
                description='Test transaction 1 - 未确认',
                counterparty_name='Test Counterparty 1',
                is_confirmed=False,
                owner_label='Business',
                accounting_ref='REF001',
                remarks='这是一个测试交易，用于测试确认功能'
            ),
            BankTransaction(
                statement_id=test_statement.id,
                transaction_date=date(2024, 1, 20),
                post_date=date(2024, 1, 20),
                transaction_id='TXN002',
                transaction_type='credit',
                amount=300.00,
                balance=1200.00,
                description='Test transaction 2 - 已确认',
                counterparty_name='Test Counterparty 2',
                is_confirmed=True,
                confirmed_at=datetime.utcnow(),
                confirmed_by='test',
                owner_label='个人商用',
                accounting_ref='EO002',
                remarks='这是一个已确认的测试交易'
            ),
            BankTransaction(
                statement_id=test_statement.id,
                transaction_date=date(2024, 1, 25),
                post_date=date(2024, 1, 25),
                transaction_id='TXN003',
                transaction_type='debit',
                amount=50.00,
                balance=1150.00,
                description='Test transaction 3 - 未确认',
                counterparty_name='Test Counterparty 3',
                is_confirmed=False,
                owner_label='',
                accounting_ref='',
                remarks=''
            )
        ]
        
        for transaction in test_transactions:
            db.session.add(transaction)
        
        db.session.commit()
        
        flash('UOB测试数据创建成功！', 'success')
        return redirect(url_for('uob_routes.uob_bank'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'创建测试数据失败: {str(e)}', 'error')
        return redirect(url_for('uob_routes.uob_bank'))


# UOB所有通用功能已移至通用函数 statement_common.py：
# - open_uob_statement_folder → statement_common.open_statement_folder
# - uob_bank_processing → statement_common.bank_processing
# - uob_to_company → statement_common.to_company
# - uob_latest_company_statement → statement_common.latest_company_statement
# - uob_latest_self_statement → statement_common.latest_self_statement


@uob_blue.route('/uob_preview_data', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def uob_preview_data():
    """预览和分析UOB银行Excel文件数据结构"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        if not file.filename.lower().endswith(('.xls', '.xlsx')):
            return jsonify({'success': False, 'message': '只支持XLS/XLSX格式的文件'})
        
        # 读取Excel文件
        import pandas as pd
        import io
        
        # 读取文件内容到内存
        file_content = file.read()
        
        # 尝试读取Excel文件
        df = None
        error_messages = []
        
        # UOB银行账单第8行是header，所以跳过前7行
        target_skiprows = 7
        
        try:
            # 首先尝试openpyxl引擎
            df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, skiprows=target_skiprows, engine='openpyxl')
            print(f"使用openpyxl引擎，跳过{target_skiprows}行读取成功")
        except Exception as e1:
            try:
                # 如果openpyxl失败，尝试xlrd引擎
                df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, skiprows=target_skiprows, engine='xlrd')
                print(f"使用xlrd引擎，跳过{target_skiprows}行读取成功")
            except Exception as e2:
                # 如果还是失败，尝试不指定引擎
                try:
                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, skiprows=target_skiprows)
                    print(f"使用默认引擎，跳过{target_skiprows}行读取成功")
                except Exception as e3:
                    print(f"所有引擎都失败: openpyxl={e1}, xlrd={e2}, default={e3}")
                    # 最后尝试其他skiprows值
                    for skiprows in [0, 1, 2, 3, 4, 5, 6, 8, 9, 10]:
                        try:
                            df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, skiprows=skiprows, engine='openpyxl')
                            if df is not None and not df.empty and df.shape[1] > 3:
                                print(f"备用方案：跳过{skiprows}行读取成功")
                                break
                        except:
                            continue
        
        if df is None or df.empty:
            return jsonify({'success': False, 'message': '无法读取Excel文件，请检查文件格式'})
        
        # 分析数据结构
        analysis_result = analyze_excel_structure(df)
        
        return jsonify({
            'success': True,
            'data': analysis_result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'分析失败：{str(e)}'})




# UOB其他通用功能也已移至通用函数 statement_common.py：
# - uob_original_processing → statement_common.original_processing
# - latest_company_statement → statement_common.latest_company_statement
# - latest_self_statement → statement_common.latest_self_statement
# - statement_to_company → statement_common.to_company


