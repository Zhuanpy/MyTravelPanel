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
        'amount_min': request.args.get('amount_min', ''),
        'amount_max': request.args.get('amount_max', ''),
        'match_status': request.args.get('match_status', ''),
        'match_category': request.args.get('match_category', ''),
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
    statements = statements_query.order_by(desc(BankStatement.period_start)).limit(50).all()
    
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

    if filters['amount_min']:
        try:
            transactions_query = transactions_query.filter(
                BankTransaction.amount >= float(filters['amount_min'])
            )
        except ValueError:
            pass
    if filters['amount_max']:
        try:
            transactions_query = transactions_query.filter(
                BankTransaction.amount <= float(filters['amount_max'])
            )
        except ValueError:
            pass

    # 标记是否需要后置筛选差额非0
    filter_diff_nonzero = False

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
        elif filters['match_status'] == 'diff_nonzero':
            # 筛选差额非0：首先筛选已匹配的交易，然后在Python层面筛选差额非0的
            filter_diff_nonzero = True
            transactions_query = transactions_query.filter(
                db.or_(
                    BankTransaction.matched_receipt_id.isnot(None),
                    BankTransaction.eo_id.isnot(None),
                    BankTransaction.reconciliation_status == 'matched'
                )
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

    # 匹配分类筛选
    if filters['match_category']:
        category = filters['match_category']
        if category == 'receipt':
            # 收据匹配：旧字段或BankTransactionMatch
            transactions_query = transactions_query.filter(
                db.or_(
                    BankTransaction.matched_receipt_id.isnot(None),
                    BankTransaction.id.in_(
                        db.session.query(BankTransactionMatch.transaction_id).filter(
                            BankTransactionMatch.match_type == 'receipt'
                        )
                    )
                )
            )
        elif category == 'eo':
            # EO匹配：旧字段或BankTransactionMatch
            transactions_query = transactions_query.filter(
                db.or_(
                    db.and_(BankTransaction.eo_id.isnot(None), BankTransaction.eo_id != 0),
                    BankTransaction.id.in_(
                        db.session.query(BankTransactionMatch.transaction_id).filter(
                            BankTransactionMatch.match_type == 'eo'
                        )
                    )
                )
            )
        elif category in ['payment', 'prepayment', 'loan_borrow', 'loan_repay']:
            # 其他类型：仅通过BankTransactionMatch
            transactions_query = transactions_query.filter(
                BankTransaction.id.in_(
                    db.session.query(BankTransactionMatch.transaction_id).filter(
                        BankTransactionMatch.match_type == category
                    )
                )
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
    elif filters['sort'] == 'ref_desc':
        transactions_query = transactions_query.order_by(desc(BankTransaction.accounting_ref))
    elif filters['sort'] == 'ref_asc':
        transactions_query = transactions_query.order_by(BankTransaction.accounting_ref)
    else:
        transactions_query = transactions_query.order_by(desc(BankTransaction.transaction_date))

    # 添加调试信息
    print(f"OCBC银行查询调试:")
    print(f"  筛选条件: {filters}")
    print(f"  查询语句: {transactions_query}")

    # 分页处理
    page = request.args.get('page', 1, type=int)
    per_page = 30

    # 如果需要筛选差额非0，则需要在Python层面进行计算和筛选
    if filter_diff_nonzero:
        # 获取所有符合条件的交易（不分页）
        all_matched_transactions = transactions_query.all()

        # 计算每个交易的差额并筛选
        diff_nonzero_transactions = []
        for t in all_matched_transactions:
            matched_amt = 0.0
            # 计算匹配金额
            if t.matched_receipt:
                matched_amt = float(t.matched_receipt.amount or 0)
            elif t.matched_eo:
                if t.matched_eo.pay_amount:
                    matched_amt = float(t.matched_eo.pay_amount)
                elif t.matched_eo.ref and t.matched_eo.ref.cost_price:
                    matched_amt = float(t.matched_eo.ref.cost_price)
            elif t.reconciliation_status == 'matched' and hasattr(t, 'matched_payment') and t.matched_payment:
                matched_amt = float(t.matched_payment.total_amount or 0)
            elif t.reconciliation_status == 'matched' and hasattr(t, 'matched_prepayment') and t.matched_prepayment:
                matched_amt = float(t.matched_prepayment.amount or 0)
            else:
                # 检查 BankTransactionMatch 表
                match_records = t.matches.all() if t.matches else []
                if match_records:
                    matched_amt = sum(float(m.allocated_amount or 0) for m in match_records)

            # 计算差额
            diff = round(float(t.amount) - matched_amt, 2)
            if diff != 0:
                t._match_diff = diff  # 缓存差额值供模板使用
                diff_nonzero_transactions.append(t)

        # 手动分页
        total = len(diff_nonzero_transactions)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        start = (page - 1) * per_page
        end = start + per_page
        transactions = diff_nonzero_transactions[start:end]

        # 创建一个简单的分页对象
        class SimplePagination:
            def __init__(self, page, per_page, total, items):
                self.page = page
                self.per_page = per_page
                self.total = total
                self.items = items
                self.pages = (total + per_page - 1) // per_page if total > 0 else 1
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None

            def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or \
                       (num > self.page - left_current - 1 and num < self.page + right_current) or \
                       num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num

        pagination = SimplePagination(page, per_page, total, transactions)
        print(f"  差额非0筛选: 共 {total} 条记录符合条件")
    else:
        pagination = transactions_query.paginate(page=page, per_page=per_page, error_out=False)
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
        transaction.confirmed_by = 'user'
        transaction.is_reconciled = True

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
        
        # 统一备注（可选）：追加到每条记录的备注后面
        remark = (data.get('remark') or '').strip()

        # 批量确认交易记录
        confirmed_count = 0
        for transaction in transactions:
            transaction.is_confirmed = True
            transaction.confirmed_at = datetime.utcnow()
            transaction.confirmed_by = 'staff'
            transaction.is_reconciled = True
            if remark:
                if transaction.remarks and transaction.remarks.strip():
                    transaction.remarks = transaction.remarks.rstrip() + ' ' + remark
                else:
                    transaction.remarks = remark
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


@ocbc_blue.route('/ocbc_batch_unlock', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def ocbc_batch_unlock():
    """批量解锁OCBC银行交易记录"""
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


@ocbc_blue.route('/ocbc_unmatch_transaction/<int:transaction_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def ocbc_unmatch_transaction(transaction_id):
    """解除OCBC银行交易的匹配关系"""
    try:
        transaction = BankTransaction.query.get(transaction_id)

        if not transaction:
            return jsonify({'success': False, 'message': '交易记录不存在'}), 404

        if transaction.statement.bank_name != 'OCBC':
            return jsonify({'success': False, 'message': '该交易不属于OCBC银行'}), 400

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


@ocbc_blue.route('/ocbc_reconcile_transaction/<int:transaction_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def ocbc_reconcile_transaction(transaction_id):
    """标记OCBC银行交易为已核对"""
    try:
        transaction = BankTransaction.query.get(transaction_id)

        if not transaction:
            return jsonify({'success': False, 'message': '交易记录不存在'}), 404

        if transaction.statement.bank_name != 'OCBC':
            return jsonify({'success': False, 'message': '该交易不属于OCBC银行'}), 400

        data = request.get_json() or {}
        action = data.get('action', 'reconcile')  # reconcile 或 unreconcile

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


# OCBC所有通用功能已移至通用函数 statement_common.py：
# - open_ocbc_statement_folder → statement_common.open_statement_folder
# - ocbc_bank_processing → statement_common.bank_processing  
# - ocbc_original_processing → statement_common.original_processing
# - ocbc_latest_company_statement → statement_common.latest_company_statement
# - ocbc_latest_self_statement → statement_common.latest_self_statement
# - ocbc_to_company → statement_common.to_company
# - ocbc_upload_file → statement_common.upload_file (已删除)

