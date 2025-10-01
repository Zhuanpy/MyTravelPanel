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
    
    # 如果没有指定月份，默认使用最新一个月
    if not month_param:
        # 查询UOB银行最新的交易记录，获取最新的月份
        latest_transaction = BankTransaction.query.join(BankStatement).filter(
            BankStatement.bank_name == 'UOB'
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
    
    # 获取UOB银行的对账单数据，按创建时间降序排列
    statements = BankStatement.query.filter(
        BankStatement.bank_name == 'UOB'
    ).order_by(desc(BankStatement.created_at)).limit(10).all()
    
    # 获取UOB银行的交易数据
    transactions_query = BankTransaction.query.join(BankStatement).filter(
        BankStatement.bank_name == 'UOB'
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


@uob_blue.route('/download_uob_statement/<statement_number>', methods=['GET'])
@login_required
@staff_only
def download_uob_statement(statement_number):
    """下载UOB对账单"""
    try:
        # 查找对账单
        statement = BankStatement.query.filter_by(
            statement_number=statement_number,
            bank_name='UOB'
        ).first()
        
        if not statement:
            flash(f'对账单 {statement_number} 不存在', 'error')
            return redirect(url_for('uob_routes.uob_bank'))
        
        # 这里应该生成对账单文件，暂时返回提示
        flash('对账单下载功能正在开发中', 'info')
        return redirect(url_for('uob_routes.uob_bank'))
        
    except Exception as e:
        flash(f'下载对账单失败: {str(e)}', 'error')
        return redirect(url_for('uob_routes.uob_bank'))


@uob_blue.route('/delete_uob_statement', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_uob_statement():
    """删除UOB对账单"""
    try:
        statement_number = request.form.get('statement_number')
        
        if not statement_number:
            flash('对账单号不能为空', 'error')
            return redirect(url_for('uob_routes.uob_bank'))
        
        # 查找对账单
        statement = BankStatement.query.filter_by(
            statement_number=statement_number,
            bank_name='UOB'
        ).first()
        
        if not statement:
            flash(f'对账单 {statement_number} 不存在', 'error')
            return redirect(url_for('uob_routes.uob_bank'))
        
        # 删除对账单（关联的交易记录会自动删除）
        db.session.delete(statement)
        db.session.commit()
        
        flash(f'对账单 {statement_number} 已成功删除', 'success')
        return redirect(url_for('uob_routes.uob_bank'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除对账单失败: {str(e)}', 'error')
        return redirect(url_for('uob_routes.uob_bank'))


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


@uob_blue.route('/open_uob_statement_folder', methods=['GET', 'POST'])
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


@uob_blue.route('/uob_bank_processing', methods=['GET', 'POST'])
@csrf.exempt
def uob_bank_processing():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    st = OriginalStatement(str(folder_path))
    st.statement_process()
    flash('账单整理完成')
    return redirect(url_for('uob_routes.uob_bank'))


@uob_blue.route('/uob_to_company', methods=['GET', 'POST'])
@csrf.exempt
def uob_to_company():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "UOB"
    flash('UOB公司账单生成功能尚未实现')
    return redirect(url_for('uob_routes.uob_bank'))


@uob_blue.route('/uob_latest_company_statement', methods=['GET', 'POST'])
@csrf.exempt
def uob_latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "UOB"
    flash('UOB最新公司账单功能尚未实现')
    return redirect(url_for('uob_routes.uob_bank'))


@uob_blue.route('/uob_latest_self_statement', methods=['GET', 'POST'])
@csrf.exempt
def uob_latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "UOB"
    flash('UOB最新个人账单功能尚未实现')
    return redirect(url_for('uob_routes.uob_bank'))


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




@uob_blue.route('/uob_upload_file', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def uob_upload_file():
    """处理UOB银行XLS文件上传"""
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
        from datetime import datetime
        
        # 读取文件内容到内存
        file_content = file.read()
        
        # 使用pandas读取Excel
        try:
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
                    try:
                        # 如果还是失败，尝试不指定引擎
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
                return jsonify({
                    'success': False, 
                    'message': '无法读取Excel文件。请确保文件格式正确，UOB银行账单第8行应该是标题行。'
                })
            
            # 标准化列名
            df.columns = df.columns.astype(str)
            
            # 查找包含日期、描述、金额等关键信息的列
            date_col = None
            desc_col = None
            amount_col = None
            balance_col = None
            
            # 调试信息：显示所有列名
            print(f"Excel文件列名: {list(df.columns)}")
            print(f"Excel文件形状: {df.shape}")
            print(f"前几行数据:\n{df.head()}")
            
            for col in df.columns:
                col_lower = str(col).lower().strip()
                print(f"检查列: '{col}' -> '{col_lower}'")
                
                if any(keyword in col_lower for keyword in ['date', '日期', 'transaction date', 't-date']):
                    date_col = col
                    print(f"找到日期列: {col}")
                elif any(keyword in col_lower for keyword in ['description', '描述', 'transaction description', 'desc']):
                    desc_col = col
                    print(f"找到描述列: {col}")
                elif any(keyword in col_lower for keyword in ['withdrawal', 'deposit']):
                    amount_col = col
                    print(f"找到金额列: {col}")
                elif any(keyword in col_lower for keyword in ['available balance', 'balance', '余额']):
                    balance_col = col
                    print(f"找到余额列: {col}")
            
            # 如果没有找到明确的列，尝试按位置猜测
            if not date_col and len(df.columns) > 0:
                # 假设第一列是日期
                date_col = df.columns[0]
                print(f"按位置猜测日期列: {date_col}")
            
            if not desc_col and len(df.columns) > 1:
                # 假设第二列是描述
                desc_col = df.columns[1]
                print(f"按位置猜测描述列: {desc_col}")
            
            if not amount_col and len(df.columns) > 2:
                # 查找包含数字的列
                for col in df.columns[2:]:
                    if df[col].dtype in ['int64', 'float64'] or any(pd.notna(val) and str(val).replace('.', '').replace('-', '').isdigit() for val in df[col].head(10)):
                        amount_col = col
                        print(f"按数字类型猜测金额列: {col}")
                        break
            
            print(f"最终识别的列 - 日期: {date_col}, 描述: {desc_col}, 金额: {amount_col}, 余额: {balance_col}")
            
            if not date_col or not desc_col:
                return jsonify({
                    'success': False, 
                    'message': f'Excel文件格式不正确，无法识别必要的列。\n文件列名: {list(df.columns)}\n请确保文件包含日期和描述列。'
                })
            
            # 重命名列 - 针对UOB银行账单结构
            column_mapping = {}
            if date_col:
                column_mapping[date_col] = 'T-Date'
            if desc_col:
                column_mapping[desc_col] = 'Description'
            
            # UOB银行账单已经有Withdrawal和Deposit列，不需要重命名
            # 只需要重命名余额列
            if balance_col:
                column_mapping[balance_col] = 'Balance'
            
            df = df.rename(columns=column_mapping)
            
            # 确保Withdrawal和Deposit列存在
            if 'Withdrawal' not in df.columns:
                print("警告: 未找到Withdrawal列")
            if 'Deposit' not in df.columns:
                print("警告: 未找到Deposit列")
            if 'Balance' not in df.columns:
                print("警告: 未找到Balance列")
            
            # 数据清洗
            print(f"清洗前数据形状: {df.shape}")
            
            # 只删除日期和描述都为空的行
            df = df.dropna(subset=['T-Date', 'Description'])
            print(f"删除空值后数据形状: {df.shape}")
            
            # 处理日期 - 更加灵活
            try:
                df['T-Date'] = pd.to_datetime(df['T-Date'], errors='coerce').dt.date
                # 删除日期解析失败的行
                df = df.dropna(subset=['T-Date'])
                print(f"日期处理后数据形状: {df.shape}")
            except Exception as e:
                print(f"日期处理错误: {e}")
                return jsonify({'success': False, 'message': f'日期格式处理失败: {str(e)}'})
            
            # 创建唯一ID - 包含日期、描述、金额、余额来确保唯一性
            try:
                # 确保所有列都是字符串类型
                df['Description'] = df['Description'].astype(str)
                
                # 处理金额列
                withdrawal_str = df['Withdrawal'].fillna(0).astype(str) if 'Withdrawal' in df.columns else '0'
                deposit_str = df['Deposit'].fillna(0).astype(str) if 'Deposit' in df.columns else '0'
                
                # 处理余额列
                if 'Balance' in df.columns:
                    balance_str = df['Balance'].fillna('0').astype(str)
                else:
                    balance_str = '0'
                
                # 将T-Date转换为字符串用于ID创建
                df['T-Date-Str'] = df['T-Date'].astype(str)
                
                # 创建复合唯一ID：日期+描述+Withdrawal+Deposit+余额
                df['Id'] = (df['T-Date-Str'] + '|' + df['Description'] + '|' + 
                           withdrawal_str + '|' + deposit_str + '|' + balance_str)
                df['Id'] = df['Id'].str.replace('[\s\.\\/]', '', regex=True).str[-50:].str.lower()
                
                print(f"ID创建后数据形状: {df.shape}")
                print(f"示例ID: {df['Id'].head().tolist()}")
            except Exception as e:
                print(f"ID创建错误: {e}")
                return jsonify({'success': False, 'message': f'创建唯一ID失败: {str(e)}'})
            
            # 去除重复数据
            df = df.drop_duplicates(subset=['Id']).reset_index(drop=True)
            print(f"去重后数据形状: {df.shape}")
            
            if df.empty:
                return jsonify({'success': False, 'message': '没有有效的数据可以导入'})
            
            print(f"最终处理的数据样本:\n{df.head()}")
            
            # 按月份分组创建对账单
            # 确保T-Date是datetime类型，如果不是则重新转换
            if df['T-Date'].dtype == 'object':
                df['T-Date'] = pd.to_datetime(df['T-Date'], errors='coerce')
            
            df['Month'] = df['T-Date'].apply(lambda x: x.strftime('%Y-%m') if pd.notna(x) else 'Unknown')
            monthly_groups = df.groupby('Month')
            
            print(f"数据按月份分组: {list(monthly_groups.groups.keys())}")
            
            total_processed_count = 0
            statement_numbers = []
            updated_statements = []  # 记录更新的对账单
            
            # 总体关键字统计
            total_keyword_stats = {
                'personal': 0,
                'business': 0,
                'personal_business': 0,
                'no_match': 0,
                'total_keywords_matched': 0
            }
            
            for month, month_data in monthly_groups:
                print(f"处理月份: {month}, 数据行数: {len(month_data)}")
                
                # 检查该月份是否已有对账单 - 使用更精确的月份匹配
                # 构造该月份的对账单号格式: UOB-2025-09
                month_year = month  # 例如: "2025-09"
                expected_statement_number = f"UOB-{month_year}"
                
                existing_statement = BankStatement.query.filter(
                    BankStatement.bank_name == 'UOB',
                    BankStatement.statement_number == expected_statement_number
                ).first()
                
                if existing_statement:
                    print(f"月份 {month} 已存在对账单: {existing_statement.statement_number}")
                    
                    # 更新对账单的期间，确保覆盖所有数据
                    new_period_start = month_data['T-Date'].min()
                    new_period_end = month_data['T-Date'].max()
                    
                    # 转换为date对象以便比较
                    if hasattr(new_period_start, 'date'):
                        new_period_start = new_period_start.date()
                    if hasattr(new_period_end, 'date'):
                        new_period_end = new_period_end.date()
                    
                    # 如果新数据的开始日期更早，更新period_start
                    if new_period_start < existing_statement.period_start:
                        existing_statement.period_start = new_period_start
                        print(f"更新对账单开始日期: {new_period_start}")
                    
                    # 如果新数据的结束日期更晚，更新period_end
                    if new_period_end > existing_statement.period_end:
                        existing_statement.period_end = new_period_end
                        print(f"更新对账单结束日期: {new_period_end}")
                    
                    # 更新对账单的statement_date为当前日期
                    existing_statement.statement_date = datetime.now().date()
                    print(f"更新对账单日期: {existing_statement.statement_date}")
                    
                    # 记录更新的对账单信息
                    updated_statements.append({
                        'statement_number': existing_statement.statement_number,
                        'period_start': existing_statement.period_start,
                        'period_end': existing_statement.period_end,
                        'updated': True
                    })
                    
                    statement_id = existing_statement.id
                else:
                    # 创建新的对账单记录
                    statement_number = expected_statement_number
                    # 计算该月的开始和结束日期
                    month_start = month_data['T-Date'].min()
                    month_end = month_data['T-Date'].max()
                    
                    # 设置该月的第一天和最后一天
                    year, month_num = month.split('-')
                    month_start = datetime(int(year), int(month_num), 1).date()
                    
                    # 计算该月的最后一天
                    if int(month_num) == 12:
                        next_month = datetime(int(year) + 1, 1, 1).date()
                    else:
                        next_month = datetime(int(year), int(month_num) + 1, 1).date()
                    
                    month_end = next_month - timedelta(days=1)
                    
                    bank_statement = BankStatement(
                        statement_number=statement_number,
                        bank_name='UOB',
                        account_number='UPLOAD',
                        account_name='上传文件',
                        statement_date=datetime.now().date(),
                        period_start=month_start,
                        period_end=month_end,
                        opening_balance=0.00,
                        closing_balance=0.00,
                        currency='SGD',
                        status='draft',
                        created_by='upload'
                    )
                    
                    db.session.add(bank_statement)
                    db.session.flush()  # 获取ID
                    statement_id = bank_statement.id
                    statement_numbers.append(statement_number)
                    
                    # 记录新创建的对账单信息
                    updated_statements.append({
                        'statement_number': statement_number,
                        'period_start': month_start,
                        'period_end': month_end,
                        'updated': False
                    })
                    
                    print(f"创建新对账单: {statement_number}, 期间: {month_start} 到 {month_end}")
                
                # 处理该月份的交易记录
                month_result = process_monthly_transactions(month_data, statement_id, month, 'UOB')
                month_processed_count = month_result['processed_count']
                month_keyword_stats = month_result['keyword_stats']
                
                total_processed_count += month_processed_count
                
                # 累计关键字统计
                for key in total_keyword_stats:
                    total_keyword_stats[key] += month_keyword_stats[key]
            
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'文件上传成功！',
                'processed_count': total_processed_count,
                'statement_numbers': statement_numbers,
                'months_processed': list(monthly_groups.groups.keys()),
                'keyword_stats': total_keyword_stats,
                'statement_updates': updated_statements
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'处理Excel文件时出错：{str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'})






@uob_blue.route('/uob_original_processing', methods=['GET', 'POST'])
@csrf.exempt
def uob_original_processing():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.organized_statement_data()
    flash('原始账单整理完成')
    return redirect(url_for('uob_routes.uob_bank'))


@uob_blue.route('/latest_company_statement', methods=['GET', 'POST'])
@csrf.exempt
def latest_company_statement():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.latest_company_statement()
    flash('公司账单整理完成')
    return redirect(url_for('uob_routes.uob_bank'))


@uob_blue.route('/latest_self_statement', methods=['GET', 'POST'])
@csrf.exempt
def latest_self_statement():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.latest_self_statement()
    flash('个人账单整理完成')
    return redirect(url_for('uob_routes.uob_bank'))


@uob_blue.route('/statement_to_company', methods=['GET', 'POST'])
@csrf.exempt
def statement_to_company():
    if request.method == 'GET':
        return redirect(url_for('uob_routes.uob_bank'))
    folder_path = Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER"
    statement = OriginalStatement(str(folder_path))
    statement.statement_to_company()
    flash('最终公司账单生成完成')
    return redirect(url_for('uob_routes.uob_bank'))


