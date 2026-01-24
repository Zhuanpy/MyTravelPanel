from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash, send_file
from flask_login import login_required
from App_new.utils.Statement import OriginalStatement
from App_new.utils.Invoice import CountHid
from App_new.exts import db
from App_new.finance.models.statement import BankStatement, BankTransaction
from App_new.finance.models.bank_keywords import BankStatementKeyword
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.eo import ProjectEO
from App_new.finance.models.bank_transaction_match import BankTransactionMatch
from App_new.business.projects.models.supplier_payment import SupplierPayment
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment
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
cmb_blue = Blueprint('cmb_routes', __name__)




# 招商银行相关路由
@cmb_blue.route('/cmb_bank')
@login_required
@staff_only
def cmb_bank():
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
        'match_status': request.args.get('match_status', ''),
        'operation_status': request.args.get('operation_status', ''),
        'sort': request.args.get('sort', 'date_desc')
    }
    
    # 获取CMB银行的对账单数据，按对账单号（月份）降序排列
    statements_query = BankStatement.query.filter(
        BankStatement.bank_name == 'CMB'
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
    
    # 获取CMB银行的交易数据
    transactions_query = BankTransaction.query.join(BankStatement).filter(
        BankStatement.bank_name == 'CMB'
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
    
    if filters['match_status']:
        if filters['match_status'] == 'reconciled':
            transactions_query = transactions_query.filter(
                BankTransaction.is_reconciled == True
            )
        elif filters['match_status'] == 'matched':
            transactions_query = transactions_query.filter(
                BankTransaction.is_reconciled != True,
                db.or_(
                    BankTransaction.matched_receipt_id.isnot(None),
                    BankTransaction.eo_id.isnot(None),
                    BankTransaction.reconciliation_status == 'matched'
                )
            )
        elif filters['match_status'] == 'unmatched':
            transactions_query = transactions_query.filter(
                db.or_(BankTransaction.is_reconciled == False, BankTransaction.is_reconciled.is_(None)),
                BankTransaction.matched_receipt_id.is_(None),
                db.or_(BankTransaction.eo_id.is_(None), BankTransaction.eo_id == 0),
                db.or_(BankTransaction.reconciliation_status != 'matched', BankTransaction.reconciliation_status.is_(None))
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

    # 获取CMB银行现有的账户名称列表（用于筛选和上传时选择）
    account_names = db.session.query(BankStatement.account_name).filter(
        BankStatement.bank_name == 'CMB',
        BankStatement.account_name.isnot(None),
        BankStatement.account_name != '上传文件'
    ).distinct().order_by(BankStatement.account_name).all()
    account_name_options = [name[0] for name in account_names] if account_names else []

    # 检查是否是AJAX请求（只返回表格部分）
    if request.args.get('partial') == 'table':
        return render_template('finance/statement/_cmb_tx_table.html',
                             transactions=transactions,
                             pagination=pagination,
                             filters=filters)

    return render_template('finance/statement/UnifiedBank.html',
                         bank_name='CMB',
                         transactions=transactions,
                         pagination=pagination,
                         filters=filters,
                         statements=statements,
                         owner_options=owner_options,
                         account_name_options=account_name_options)


# CMB下载和删除对账单功能已移至通用函数 statement_common.download_statement 和 statement_common.delete_statement


@cmb_blue.route('/cmb_tx_update', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def cmb_tx_update():
    """更新CMB银行交易记录"""
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
                transaction.is_reconciled = True
            else:
                transaction.confirmed_at = None
                transaction.confirmed_by = None
                transaction.is_reconciled = False

        db.session.commit()
        
        return jsonify({'success': True, 'message': '交易记录更新成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})


@cmb_blue.route('/cmb_tx_confirm', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def cmb_tx_confirm():
    """确认CMB银行交易记录"""
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
        transaction.confirmed_by = 'user'
        transaction.is_reconciled = True

        db.session.commit()

        return jsonify({'success': True, 'message': '交易记录确认成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'确认失败: {str(e)}'})


@cmb_blue.route('/cmb_batch_confirm', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def cmb_batch_confirm():
    """批量确认CMB银行交易记录"""
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
            transaction.confirmed_by = 'staff'
            transaction.is_reconciled = True
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


@cmb_blue.route('/cmb_batch_unlock', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def cmb_batch_unlock():
    """批量解锁CMB银行交易记录"""
    try:
        data = request.get_json()

        if not data or 'transaction_ids' not in data:
            return jsonify({'success': False, 'message': '缺少交易记录ID列表'})

        transaction_ids = data['transaction_ids']

        if not isinstance(transaction_ids, list) or len(transaction_ids) == 0:
            return jsonify({'success': False, 'message': '交易记录ID列表不能为空'})

        transactions = BankTransaction.query.filter(
            BankTransaction.id.in_(transaction_ids),
            BankTransaction.is_confirmed == True
        ).all()

        if not transactions:
            return jsonify({'success': False, 'message': '没有找到需要解锁的交易记录'})

        unlocked_count = 0
        for transaction in transactions:
            transaction.is_confirmed = False
            transaction.confirmed_at = None
            transaction.confirmed_by = None
            unlocked_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功解锁 {unlocked_count} 个交易记录',
            'unlocked_count': unlocked_count
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'批量解锁失败: {str(e)}'}), 500


@cmb_blue.route('/cmb_unlock_transaction/<int:transaction_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def cmb_unlock_transaction(transaction_id):
    """解锁已确认的CMB银行交易记录，使其可以重新编辑"""
    try:
        # 查找交易记录
        transaction = BankTransaction.query.get(transaction_id)
        
        if not transaction:
            return jsonify({'success': False, 'message': '交易记录不存在'}), 404
        
        # 验证该交易是否属于CMB银行
        if transaction.statement.bank_name != 'CMB':
            return jsonify({'success': False, 'message': '该交易不属于CMB银行'}), 400
        
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


@cmb_blue.route('/cmb_unmatch_transaction/<int:transaction_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def cmb_unmatch_transaction(transaction_id):
    """解除CMB银行交易的匹配关系"""
    try:
        transaction = BankTransaction.query.get(transaction_id)

        if not transaction:
            return jsonify({'success': False, 'message': '交易记录不存在'}), 404

        if transaction.statement.bank_name != 'CMB':
            return jsonify({'success': False, 'message': '该交易不属于CMB银行'}), 400

        # 解除匹配
        old_receipt_id = transaction.matched_receipt_id
        old_eo_id = transaction.eo_id

        # 同步清除收据的核对状态
        if old_receipt_id:
            receipt = ProjectReceipt.query.get(old_receipt_id)
            if receipt:
                receipt.is_reconciled = False
                receipt.reconciled_at = None
                receipt.reconciled_by = None

        # 同步清除EO的核对状态
        if old_eo_id:
            eo = ProjectEO.query.get(old_eo_id)
            if eo:
                eo.is_reconciled = False
                eo.reconciled_at = None
                eo.reconciled_by = None

        # 清除BankTransactionMatch关联（Payment/Prepayment）
        btm_matches = BankTransactionMatch.query.filter_by(transaction_id=transaction_id).all()
        for m in btm_matches:
            if m.match_type == 'payment':
                payment = SupplierPayment.query.get(m.match_id)
                if payment:
                    payment.is_reconciled = False
                    payment.reconciled_at = None
                    payment.reconciled_by = None
            elif m.match_type == 'prepayment':
                prepayment = SupplierPrepayment.query.get(m.match_id)
                if prepayment:
                    prepayment.is_reconciled = False
                    prepayment.reconciled_at = None
                    prepayment.reconciled_by = None
            db.session.delete(m)

        transaction.matched_receipt_id = None
        transaction.eo_id = None
        transaction.accounting_ref = None
        transaction.reconciliation_status = 'unmatched'
        transaction.is_reconciled = False
        transaction.reconciled_at = None
        transaction.reconciled_by = None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '匹配关系已解除',
            'old_receipt_id': old_receipt_id,
            'old_eo_id': old_eo_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'解除匹配失败: {str(e)}'}), 500


@cmb_blue.route('/cmb_reconcile_transaction/<int:transaction_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def cmb_reconcile_transaction(transaction_id):
    """标记CMB银行交易为已核对"""
    try:
        transaction = BankTransaction.query.get(transaction_id)

        if not transaction:
            return jsonify({'success': False, 'message': '交易记录不存在'}), 404

        if transaction.statement.bank_name != 'CMB':
            return jsonify({'success': False, 'message': '该交易不属于CMB银行'}), 400

        data = request.get_json() or {}
        action = data.get('action', 'reconcile')

        if action == 'reconcile':
            transaction.is_reconciled = True
            transaction.reconciled_at = datetime.now()
            transaction.reconciled_by = 'user'
            message = '已标记为已核对'
        else:
            transaction.is_reconciled = False
            transaction.reconciled_at = None
            transaction.reconciled_by = None
            message = '已取消核对状态'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'is_reconciled': transaction.is_reconciled
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500


# CMB所有通用功能已移至通用函数 statement_common.py：
# - open_cmb_statement_folder → statement_common.open_statement_folder
# - cmb_bank_processing → statement_common.bank_processing
# - cmb_original_processing → statement_common.original_processing
# - cmb_latest_company_statement → statement_common.latest_company_statement
# - cmb_latest_self_statement → statement_common.latest_self_statement
# - cmb_to_company → statement_common.to_company
# - cmb_upload_file → statement_common.upload_file (已删除)


# Athina 相关路由已移动到 athina_routes.py

@cmb_blue.route('/statement/company_bill', methods=['GET', 'POST'])
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
                return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))
        
        try:
            os.startfile(str(folder_path))
            flash('成功打开公司账单文件夹', 'success')
        except Exception as e:
            flash(f'打开文件夹失败：{str(e)}', 'error')
        
        return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))
    
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


@cmb_blue.route('/company_bill_processing', methods=['POST'])
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
    
    return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))


@cmb_blue.route('/company_bill_consolidate', methods=['POST'])
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
    
    return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))


@cmb_blue.route('/company_bill_export', methods=['POST'])
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
    
    return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))


@cmb_blue.route('/open_company_bill_folder', methods=['POST'])
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
                return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))
        
        os.startfile(str(folder_path))
        flash('成功打开公司账单文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))


@cmb_blue.route('/refresh_company_list', methods=['POST'])
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
    
    return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))


@cmb_blue.route('/open_company_folder', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def open_company_folder():
    """打开特定公司的文件夹"""
    try:
        company_name = request.form.get('company_name')
        if not company_name:
            flash('公司名称不能为空', 'error')
            return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))
        
        company_folder = Config.BILLING_DATA_PATH / "Company" / company_name
        
        if not company_folder.exists():
            flash(f'公司文件夹不存在：{company_name}', 'error')
            return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))
        
        # 打开文件夹
        os.startfile(str(company_folder))
        flash(f'成功打开 {company_name} 的文件夹')
        
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for("statement_common_routes.to_company", bank_name="CMB"))


@cmb_blue.route('/compare_reports', methods=['POST'])
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





@cmb_blue.route('/download_report/<report_type>', methods=['GET'])
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


@cmb_blue.route('/batch_compare_reports', methods=['POST'])
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


@cmb_blue.route('/download_batch_report', methods=['GET'])
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
