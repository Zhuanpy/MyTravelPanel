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
statement_blue = Blueprint('statement_routes', __name__)


@statement_blue.route('/uob_bank')
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
    
    return render_template('finance/statement/UobBank.html', 
                         statements=statements, 
                         transactions=transactions,
                         filters=filters,
                         owner_options=owner_options,
                         pagination=pagination)


@statement_blue.route('/download_uob_statement/<statement_number>', methods=['GET'])
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
            return redirect(url_for('statement_routes.uob_bank'))
        
        # 这里应该生成对账单文件，暂时返回提示
        flash('对账单下载功能正在开发中', 'info')
        return redirect(url_for('statement_routes.uob_bank'))
        
    except Exception as e:
        flash(f'下载对账单失败: {str(e)}', 'error')
        return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/delete_uob_statement', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_uob_statement():
    """删除UOB对账单"""
    try:
        statement_number = request.form.get('statement_number')
        
        if not statement_number:
            flash('对账单号不能为空', 'error')
            return redirect(url_for('statement_routes.uob_bank'))
        
        # 查找对账单
        statement = BankStatement.query.filter_by(
            statement_number=statement_number,
            bank_name='UOB'
        ).first()
        
        if not statement:
            flash(f'对账单 {statement_number} 不存在', 'error')
            return redirect(url_for('statement_routes.uob_bank'))
        
        # 删除对账单（关联的交易记录会自动删除）
        db.session.delete(statement)
        db.session.commit()
        
        flash(f'对账单 {statement_number} 已成功删除', 'success')
        return redirect(url_for('statement_routes.uob_bank'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除对账单失败: {str(e)}', 'error')
        return redirect(url_for('statement_routes.uob_bank'))


@statement_blue.route('/uob_tx_update', methods=['POST'])
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


@statement_blue.route('/uob_tx_confirm', methods=['POST'])
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


@statement_blue.route('/uob_batch_confirm', methods=['POST'])
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


@statement_blue.route('/uob_create_test_data', methods=['GET'])
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
        return redirect(url_for('statement_routes.uob_bank'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'创建测试数据失败: {str(e)}', 'error')
        return redirect(url_for('statement_routes.uob_bank'))


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


@statement_blue.route('/uob_preview_data', methods=['POST'])
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


def analyze_excel_structure(df):
    """分析Excel文件结构"""
    # 标准化列名
    df.columns = df.columns.astype(str)
    all_columns = list(df.columns)
    
    # 识别关键列
    identified_columns = {}
    date_col = None
    desc_col = None
    amount_col = None
    balance_col = None
    
    for col in df.columns:
        col_lower = str(col).lower().strip()
        
        if any(keyword in col_lower for keyword in ['date', '日期', 'transaction date', 't-date']):
            date_col = col
        elif any(keyword in col_lower for keyword in ['description', '描述', 'transaction description', 'desc']):
            desc_col = col
        elif any(keyword in col_lower for keyword in ['amount', '金额', 'withdrawal', 'deposit', 'debit', 'credit']):
            amount_col = col
        elif any(keyword in col_lower for keyword in ['balance', '余额', 'available balance', 'bal']):
            balance_col = col
    
    # 按位置猜测
    if not date_col and len(df.columns) > 0:
        date_col = df.columns[0]
    if not desc_col and len(df.columns) > 1:
        desc_col = df.columns[1]
    if not amount_col and len(df.columns) > 2:
        for col in df.columns[2:]:
            if df[col].dtype in ['int64', 'float64'] or any(pd.notna(val) and str(val).replace('.', '').replace('-', '').isdigit() for val in df[col].head(10)):
                amount_col = col
                break
    
    identified_columns = {
        'date': date_col,
        'description': desc_col,
        'amount': amount_col,
        'balance': balance_col
    }
    
    # 数据质量分析
    data_issues = []
    recommendations = []
    
    # 检查空值
    null_counts = df.isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            data_issues.append(f"列 '{col}' 有 {count} 个空值")
    
    # 检查日期列
    if date_col:
        try:
            date_parsed = pd.to_datetime(df[date_col], errors='coerce')
            invalid_dates = date_parsed.isnull().sum()
            if invalid_dates > 0:
                data_issues.append(f"日期列 '{date_col}' 有 {invalid_dates} 个无效日期")
        except:
            data_issues.append(f"日期列 '{date_col}' 格式无法解析")
    else:
        data_issues.append("未找到日期列")
    
    # 检查描述列
    if not desc_col:
        data_issues.append("未找到描述列")
    
    # 检查金额列
    if not amount_col:
        data_issues.append("未找到金额列")
        recommendations.append("建议手动指定包含交易金额的列")
    
    # 生成建议
    if len(data_issues) == 0:
        recommendations.append("数据结构良好，可以导入")
    else:
        recommendations.append("建议检查并修复数据问题后再导入")
    
    if len(all_columns) > 6:
        recommendations.append("文件包含较多列，建议确认是否需要所有列")
    
    # 准备预览数据（前10行）
    preview_data = []
    for index, row in df.head(10).iterrows():
        row_data = {}
        for col in all_columns:
            value = row[col]
            if pd.isna(value):
                row_data[col] = ''
            else:
                row_data[col] = str(value)
        preview_data.append(row_data)
    
    return {
        'total_rows': len(df),
        'total_columns': len(all_columns),
        'valid_rows': len(df.dropna(subset=[date_col, desc_col]) if date_col and desc_col else df),
        'all_columns': all_columns,
        'identified_columns': identified_columns,
        'preview_data': preview_data,
        'data_issues': data_issues,
        'recommendations': recommendations
    }


@statement_blue.route('/uob_upload_file', methods=['POST'])
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
                month_result = process_monthly_transactions(month_data, statement_id, month)
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


def apply_keyword_matching(description, bank_name='UOB'):
    """根据交易描述应用关键字匹配，设置owner标签和关键词"""
    try:
        # 从数据库获取关键字
        keywords = BankStatementKeyword.query.filter(
            BankStatementKeyword.bank_name == bank_name
        ).all()
        
        matched_keywords = []
        owner_label = ''
        
        description_lower = str(description).lower()
        
        for keyword in keywords:
            if keyword.keyword.lower() in description_lower:
                matched_keywords.append(keyword.keyword)
                
                # 根据关键字类型设置owner标签
                if keyword.keyword_type == 'personal':
                    owner_label = '个人消费'
                elif keyword.keyword_type == 'business':
                    owner_label = 'Business'
                elif keyword.keyword_type == 'personal_business':
                    owner_label = '个人商用'
                else:
                    owner_label = 'Business'  # 默认
        
        # 如果没有匹配到关键字，设置默认值
        if not matched_keywords:
            owner_label = 'Business'
        
        return {
            'owner_label': owner_label,
            'matched_keywords': ','.join(matched_keywords) if matched_keywords else '',
            'keyword_count': len(matched_keywords)
        }
        
    except Exception as e:
        print(f"关键字匹配错误: {e}")
        return {
            'owner_label': 'Business',
            'matched_keywords': '',
            'keyword_count': 0
        }


def process_monthly_transactions(month_data, statement_id, month):
    """处理单个月份的交易记录"""
    processed_count = 0
    error_count = 0
    duplicate_count = 0
    
    # 关键字匹配统计
    keyword_stats = {
        'personal': 0,
        'business': 0,
        'personal_business': 0,
        'no_match': 0,
        'total_keywords_matched': 0
    }
    
    print(f"开始处理月份 {month} 的交易记录，共 {len(month_data)} 条")
    
    for index, row in month_data.iterrows():
        try:
            # 检查是否已存在相同的交易记录
            existing_transaction = BankTransaction.query.filter(
                BankTransaction.tx_fingerprint == row['Id']
            ).first()
            
            if existing_transaction:
                duplicate_count += 1
                print(f"跳过重复记录 {index}: {row['Id']}")
                continue
            
            # 确定交易类型和金额 - 针对UOB银行账单结构
            transaction_type = 'debit'
            amount = 0.00
            amount_found = False
            
            # UOB银行账单有Withdrawal和Deposit两列，需要分别处理
            withdrawal_amount = 0.00
            deposit_amount = 0.00
            
            # 获取Withdrawal金额
            if 'Withdrawal' in row and pd.notna(row['Withdrawal']):
                try:
                    withdrawal_amount = float(row['Withdrawal'])
                except (ValueError, TypeError):
                    withdrawal_amount = 0.00
            
            # 获取Deposit金额
            if 'Deposit' in row and pd.notna(row['Deposit']):
                try:
                    deposit_amount = float(row['Deposit'])
                except (ValueError, TypeError):
                    deposit_amount = 0.00
            
            # 确定交易类型和金额
            if withdrawal_amount > 0 and deposit_amount == 0:
                # 只有Withdrawal有值，这是借记交易
                amount = withdrawal_amount
                transaction_type = 'debit'
                amount_found = True
                print(f"记录 {index}: Withdrawal = {withdrawal_amount}, 借记交易")
            elif deposit_amount > 0 and withdrawal_amount == 0:
                # 只有Deposit有值，这是贷记交易
                amount = deposit_amount
                transaction_type = 'credit'
                amount_found = True
                print(f"记录 {index}: Deposit = {deposit_amount}, 贷记交易")
            elif withdrawal_amount > 0 and deposit_amount > 0:
                # 两列都有值，这是异常情况，取较大的值
                if withdrawal_amount >= deposit_amount:
                    amount = withdrawal_amount
                    transaction_type = 'debit'
                else:
                    amount = deposit_amount
                    transaction_type = 'credit'
                amount_found = True
                print(f"记录 {index}: 异常情况 Withdrawal={withdrawal_amount}, Deposit={deposit_amount}")
            else:
                # 两列都没有值，跳过这条记录
                print(f"跳过记录 {index}: Withdrawal={withdrawal_amount}, Deposit={deposit_amount}, 无有效金额")
                continue
            
            # 获取余额 - 优先使用Available Balance列
            balance = 0.00
            balance_col_name = None
            
            # 查找余额列
            for col in ['Available Balance', 'Balance']:
                if col in row and pd.notna(row[col]):
                    balance_col_name = col
                    break
            
            if balance_col_name:
                try:
                    balance = float(row[balance_col_name])
                    print(f"记录 {index}: 从列 '{balance_col_name}' 获取余额 = {balance}")
                except (ValueError, TypeError):
                    balance = 0.00
                    print(f"记录 {index}: 余额列 '{balance_col_name}' 值转换失败: {row[balance_col_name]}")
            else:
                print(f"记录 {index}: 未找到余额列")
            
            # 应用关键字匹配，设置owner标签
            keyword_result = apply_keyword_matching(row['Description'], 'UOB')
            owner_label = keyword_result['owner_label']
            matched_keywords = keyword_result['matched_keywords']
            
            print(f"记录 {index}: 描述='{row['Description'][:50]}...', 匹配关键字={matched_keywords}, Owner={owner_label}")
            
            # 统计关键字匹配结果
            if matched_keywords:
                keyword_stats['total_keywords_matched'] += keyword_result['keyword_count']
                if owner_label == '个人消费':
                    keyword_stats['personal'] += 1
                elif owner_label == 'Business':
                    keyword_stats['business'] += 1
                elif owner_label == '个人商用':
                    keyword_stats['personal_business'] += 1
            else:
                keyword_stats['no_match'] += 1
            
            # 创建交易记录
            transaction = BankTransaction(
                statement_id=statement_id,
                transaction_date=row['T-Date'],
                post_date=row['T-Date'],
                transaction_id=row['Id'],
                transaction_type=transaction_type,
                amount=amount,
                balance=balance,
                description=str(row['Description']),
                counterparty_name='',
                reconciliation_status='unmatched',
                is_confirmed=False,
                owner_label=owner_label,  # 使用关键字匹配结果
                accounting_ref='',
                remarks='',
                keyword=matched_keywords,  # 设置匹配的关键字
                tx_fingerprint=row['Id'],  # 使用复合ID作为指纹
                created_at=datetime.utcnow()
            )
            
            db.session.add(transaction)
            processed_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"处理记录 {index} 时出错: {e}")
            continue
    
    print(f"月份 {month} 处理完成:")
    print(f"  - 成功处理: {processed_count} 条")
    print(f"  - 跳过重复: {duplicate_count} 条") 
    print(f"  - 处理错误: {error_count} 条")
    print(f"关键字匹配统计:")
    print(f"  - 个人消费: {keyword_stats['personal']} 条")
    print(f"  - 商业用途: {keyword_stats['business']} 条")
    print(f"  - 个人商用: {keyword_stats['personal_business']} 条")
    print(f"  - 无匹配: {keyword_stats['no_match']} 条")
    print(f"  - 总匹配关键字: {keyword_stats['total_keywords_matched']} 个")
    
    return {
        'processed_count': processed_count,
        'keyword_stats': keyword_stats
    }


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
    
    try:
        folder_path = Config.BILLING_DATA_PATH / "CMB"
        
        # 检查文件夹是否存在
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            flash('CMB文件夹不存在，已自动创建', 'info')
        
        # 导入招商银行处理类
        from App_new.utils.CmbStatement import CmbStatement
        
        # 处理账单
        cmb_processor = CmbStatement(str(folder_path))
        output_file = cmb_processor.statement_process()
        
        # 获取摘要信息
        summary = cmb_processor.get_statement_summary()
        
        if summary:
            flash(f'招商银行账单处理完成！共处理 {summary["total_transactions"]} 笔交易，总金额: {summary["total_amount"]:.2f} CNY', 'success')
        else:
            flash('招商银行账单处理完成！', 'success')
            
    except FileNotFoundError as e:
        flash(f'未找到账单文件：{str(e)}', 'error')
    except Exception as e:
        logger.error(f"招商银行账单处理失败: {str(e)}")
        flash(f'账单处理失败：{str(e)}', 'error')
    
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


# Athina 相关路由已移动到 athina_routes.py

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
            'summary': Config.safe_json(results['summary']),
            'differences': Config.safe_json(results['differences']),
            'missing_hids': Config.safe_json(missing_hids),
            'detailed_differences': Config.safe_json(detailed_differences)
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
