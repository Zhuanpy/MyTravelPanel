# -*- coding: utf-8 -*-
"""银行流水与项目收款/EO对比功能"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.finance.models.statement import BankStatement, BankTransaction
from App_new.finance.models.bank_transaction_match import BankTransactionMatch
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.project import CustomerCompany
from App_new.utils.decorators import staff_only
from datetime import datetime, timedelta
from sqlalchemy import desc, func, or_, and_
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
reconciliation_bp = Blueprint('reconciliation', __name__, url_prefix='/reconciliation')


@reconciliation_bp.route('/bank-receipt')
@login_required
@staff_only
def bank_receipt_compare():
    """银行流水与项目收款对比主页面"""
    # 获取筛选参数
    bank_name = request.args.get('bank_name', '')
    account_name = request.args.get('account_name', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status = request.args.get('status', 'all')  # all, unmatched, matched

    # 获取可用的银行和账户选项
    bank_options = db.session.query(BankStatement.bank_name).distinct().order_by(BankStatement.bank_name).all()
    bank_options = [b[0] for b in bank_options]

    # 获取账户选项（根据选择的银行筛选）
    account_query = db.session.query(BankStatement.account_name).filter(
        BankStatement.account_name.isnot(None),
        BankStatement.account_name != '上传文件'
    )
    if bank_name:
        account_query = account_query.filter(BankStatement.bank_name == bank_name)
    account_options = account_query.distinct().order_by(BankStatement.account_name).all()
    account_options = [a[0] for a in account_options]

    # 设置默认日期范围（最近30天）
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    filters = {
        'bank_name': bank_name,
        'account_name': account_name,
        'start_date': start_date,
        'end_date': end_date,
        'status': status
    }

    return render_template('finance/reconciliation/bank_receipt_compare.html',
                         filters=filters,
                         bank_options=bank_options,
                         account_options=account_options)


@reconciliation_bp.route('/api/compare-data')
@login_required
@staff_only
def get_compare_data():
    """获取对比数据API"""
    try:
        bank_name = request.args.get('bank_name', '')
        account_name = request.args.get('account_name', '')
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')
        status = request.args.get('status', 'all')
        hide_reconciled = request.args.get('hide_reconciled', 'true') == 'true'

        # 解析日期
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # 查询银行转入记录（只查Credit类型）
        tx_query = BankTransaction.query.join(BankStatement).filter(
            BankTransaction.transaction_type == 'credit'
        )

        if bank_name:
            tx_query = tx_query.filter(BankStatement.bank_name == bank_name)
        if account_name:
            tx_query = tx_query.filter(BankStatement.account_name == account_name)
        if start_date:
            tx_query = tx_query.filter(BankTransaction.transaction_date >= start_date)
        if end_date:
            tx_query = tx_query.filter(BankTransaction.transaction_date <= end_date)

        # 隐藏已核对的记录
        if hide_reconciled:
            tx_query = tx_query.filter(
                or_(
                    BankTransaction.is_reconciled == False,
                    BankTransaction.is_reconciled == 0,
                    BankTransaction.is_reconciled.is_(None)
                )
            )

        # 同时排除已确认的个人消费记录
        tx_query = tx_query.filter(
            ~and_(
                BankTransaction.owner_label.in_(['个人消费', '个人商用', 'personal']),
                BankTransaction.is_confirmed == True
            )
        )

        # 根据状态筛选
        if status == 'all':
            # 默认排除已匹配的记录（已匹配的不需要再处理）
            tx_query = tx_query.filter(
                or_(
                    BankTransaction.reconciliation_status != 'matched',
                    BankTransaction.reconciliation_status.is_(None)
                )
            )
        elif status == 'unmatched':
            tx_query = tx_query.filter(
                or_(
                    BankTransaction.reconciliation_status == 'unmatched',
                    BankTransaction.reconciliation_status.is_(None)
                ),
                or_(
                    BankTransaction.owner_label.is_(None),
                    BankTransaction.owner_label == '',
                    ~BankTransaction.owner_label.in_(['个人消费', '个人商用', 'personal'])
                )
            )
        elif status == 'matched':
            tx_query = tx_query.filter(BankTransaction.reconciliation_status == 'matched')
        elif status == 'reconciled':
            # 只显示已核对的记录
            tx_query = BankTransaction.query.join(BankStatement).filter(
                BankTransaction.transaction_type == 'credit',
                BankTransaction.is_reconciled == True
            )
            if bank_name:
                tx_query = tx_query.filter(BankStatement.bank_name == bank_name)
            if account_name:
                tx_query = tx_query.filter(BankStatement.account_name == account_name)
            if start_date:
                tx_query = tx_query.filter(BankTransaction.transaction_date >= start_date)
            if end_date:
                tx_query = tx_query.filter(BankTransaction.transaction_date <= end_date)

        tx_query = tx_query.order_by(desc(BankTransaction.transaction_date))
        transactions = tx_query.limit(200).all()

        # 查询项目收款记录
        receipt_query = ProjectReceipt.query.filter(
            ProjectReceipt.status.in_(['pending', 'confirmed'])
        )

        if start_date:
            receipt_query = receipt_query.filter(ProjectReceipt.payment_date >= start_date)
        if end_date:
            receipt_query = receipt_query.filter(ProjectReceipt.payment_date <= end_date)

        # 隐藏已核对的记录
        if hide_reconciled:
            receipt_query = receipt_query.filter(
                or_(
                    ProjectReceipt.is_reconciled == False,
                    ProjectReceipt.is_reconciled.is_(None)
                )
            )

        # 根据状态筛选
        # 先获取已匹配的收款ID列表
        matched_receipt_ids = db.session.query(BankTransaction.matched_receipt_id).filter(
            BankTransaction.matched_receipt_id.isnot(None)
        ).subquery()

        if status == 'all':
            # 默认排除已匹配的收款（已匹配的不需要再处理）
            receipt_query = receipt_query.filter(~ProjectReceipt.id.in_(matched_receipt_ids))
        elif status == 'unmatched':
            # 未匹配的收款：没有关联的银行交易
            receipt_query = receipt_query.filter(~ProjectReceipt.id.in_(matched_receipt_ids))
        elif status == 'matched':
            # 已匹配的收款：有关联的银行交易
            receipt_query = receipt_query.filter(ProjectReceipt.id.in_(matched_receipt_ids))
        elif status == 'reconciled':
            # 只显示已核对的收款
            receipt_query = ProjectReceipt.query.filter(
                ProjectReceipt.status.in_(['pending', 'confirmed']),
                ProjectReceipt.is_reconciled == True
            )
            if start_date:
                receipt_query = receipt_query.filter(ProjectReceipt.payment_date >= start_date)
            if end_date:
                receipt_query = receipt_query.filter(ProjectReceipt.payment_date <= end_date)

        receipt_query = receipt_query.order_by(desc(ProjectReceipt.payment_date))
        receipts = receipt_query.limit(200).all()

        # 格式化数据
        tx_data = []
        for tx in transactions:
            tx_dict = tx.to_dict()
            tx_dict['bank_name'] = tx.statement.bank_name if tx.statement else ''
            tx_dict['account_name'] = tx.statement.account_name if tx.statement else ''
            tx_data.append(tx_dict)

        receipt_data = []
        for r in receipts:
            r_dict = r.to_dict()
            # 添加项目信息
            if r.header:
                r_dict['project_number'] = r.header.hid
                r_dict['project_name'] = r.header.desc or ''
            else:
                r_dict['project_number'] = ''
                r_dict['project_name'] = ''
            # 检查是否已匹配
            matched_tx = BankTransaction.query.filter_by(matched_receipt_id=r.id).first()
            r_dict['is_matched'] = matched_tx is not None
            r_dict['matched_tx_id'] = matched_tx.id if matched_tx else None
            receipt_data.append(r_dict)

        return jsonify({
            'success': True,
            'bank_transactions': tx_data,
            'project_receipts': receipt_data
        })

    except Exception as e:
        logger.error(f"获取对比数据失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取数据失败: {str(e)}'})


@reconciliation_bp.route('/api/auto-match')
@login_required
@staff_only
def auto_match_suggestions():
    """自动匹配建议API"""
    try:
        bank_name = request.args.get('bank_name', '')
        account_name = request.args.get('account_name', '')
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')

        # 解析日期
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # 查询未匹配的银行转入记录
        # 注意：不再自动排除"个人消费"标记的记录，让用户自己决定
        tx_query = BankTransaction.query.join(BankStatement).filter(
            BankTransaction.transaction_type == 'credit',
            or_(
                BankTransaction.reconciliation_status == 'unmatched',
                BankTransaction.reconciliation_status.is_(None)
            ),
            BankTransaction.matched_receipt_id.is_(None)
        )

        if bank_name:
            tx_query = tx_query.filter(BankStatement.bank_name == bank_name)
        if account_name:
            tx_query = tx_query.filter(BankStatement.account_name == account_name)
        if start_date:
            tx_query = tx_query.filter(BankTransaction.transaction_date >= start_date)
        if end_date:
            tx_query = tx_query.filter(BankTransaction.transaction_date <= end_date)

        transactions = tx_query.all()

        # 查询未匹配的项目收款记录
        matched_receipt_ids = db.session.query(BankTransaction.matched_receipt_id).filter(
            BankTransaction.matched_receipt_id.isnot(None)
        ).subquery()

        receipt_query = ProjectReceipt.query.filter(
            ProjectReceipt.status.in_(['pending', 'confirmed']),
            ~ProjectReceipt.id.in_(matched_receipt_ids)
        )

        if start_date:
            # 扩大收款记录的日期范围以便匹配
            extended_start = start_date - timedelta(days=7)
            receipt_query = receipt_query.filter(ProjectReceipt.payment_date >= extended_start)
        if end_date:
            extended_end = end_date + timedelta(days=7)
            receipt_query = receipt_query.filter(ProjectReceipt.payment_date <= extended_end)

        receipts = receipt_query.all()

        # 构建收据号 -> 收据对象的索引，用于REF优先匹配
        receipt_by_number = {}
        for r in receipts:
            if r.receipt_number:
                receipt_by_number[r.receipt_number.strip()] = r

        # 计算匹配建议
        suggestions = []
        for tx in transactions:
            best_match = None
            best_score = 0

            # 优先：通过 accounting_ref 匹配收据号
            ref = (tx.accounting_ref or '').strip()
            if ref and ref in receipt_by_number:
                best_match = receipt_by_number[ref]
                best_score = 200  # REF直接匹配，最高优先级
            else:
                # 回退：金额+日期+名称匹配
                for receipt in receipts:
                    score = calculate_match_score(tx, receipt)
                    if score > best_score and score >= 40:
                        best_score = score
                        best_match = receipt

            if best_match:
                suggestions.append({
                    'transaction_id': tx.id,
                    'transaction_date': tx.transaction_date.isoformat(),
                    'transaction_amount': float(tx.amount),
                    'transaction_counterparty': tx.counterparty_name or tx.description or '',
                    'receipt_id': best_match.id,
                    'receipt_number': best_match.receipt_number,
                    'receipt_date': best_match.payment_date.isoformat() if best_match.payment_date else '',
                    'receipt_amount': float(best_match.amount),
                    'receipt_payer': best_match.payer_name or '',
                    'project_number': best_match.header.hid if best_match.header else '',
                    'match_score': best_score,
                    'match_level': get_match_level(best_score)
                })

        # 按匹配分数降序排列
        suggestions.sort(key=lambda x: x['match_score'], reverse=True)

        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'total_suggestions': len(suggestions)
        })

    except Exception as e:
        logger.error(f"生成匹配建议失败: {str(e)}")
        return jsonify({'success': False, 'message': f'生成匹配建议失败: {str(e)}'})


def calculate_match_score(transaction, receipt):
    """
    计算银行交易与收款记录的匹配分数

    匹配规则：
    1. 精确匹配（100分）：金额完全相等 + 日期相同
    2. 高度匹配（80分）：金额完全相等 + 日期±3天内
    3. 可能匹配（60分）：金额完全相等 + 日期±7天内
    4. 参考匹配（40分）：对方名称包含收款项目联系人名称

    名称匹配会检查银行记录的 counterparty_name 和 description 字段
    日期匹配考虑收款日期可能在银行转账日期当天或之后
    """
    score = 0

    tx_amount = float(transaction.amount or 0)
    receipt_amount = float(receipt.amount or 0)

    # 金额匹配（允许0.01误差）
    amount_match = abs(tx_amount - receipt_amount) < 0.01

    if not amount_match:
        return 0  # 金额不匹配直接返回0分

    # 日期匹配
    tx_date = transaction.transaction_date
    receipt_date = receipt.payment_date

    if tx_date and receipt_date:
        # 收款日期通常在银行转账日期当天或之后几天
        date_diff = (receipt_date - tx_date).days

        if date_diff == 0:
            score = 100  # 精确匹配：同一天
        elif 0 <= date_diff <= 3:
            score = 90  # 高度匹配：收款在转账后1-3天内
        elif -3 <= date_diff < 0:
            score = 80  # 收款日期在转账前1-3天（可能是预录入）
        elif 0 <= date_diff <= 7:
            score = 70  # 可能匹配：收款在转账后4-7天
        elif -7 <= date_diff < -3:
            score = 60  # 收款日期在转账前4-7天
        else:
            score = 40  # 仅金额匹配
    else:
        score = 40  # 仅金额匹配

    # 名称匹配加分 - 同时检查 counterparty_name 和 description
    # 银行记录中的名字可能在 description 中，如 "PAYNOW OTHR SU XIHONG"
    counterparty = (transaction.counterparty_name or '').lower()
    description = (transaction.description or '').lower()
    bank_text = counterparty + ' ' + description  # 合并两个字段进行匹配

    payer_name = (receipt.payer_name or '').lower().strip()
    payer_company = (receipt.payer_company or '').lower().strip()

    name_matched = False
    if payer_name and len(payer_name) >= 2:
        # 检查付款人名字是否出现在银行记录中
        if payer_name in bank_text:
            name_matched = True
        else:
            # 尝试拆分名字匹配（如 "SU XIHONG" 匹配 "苏西红" 的拼音）
            name_parts = payer_name.split()
            if len(name_parts) >= 2:
                # 检查名字的各部分是否都出现在银行记录中
                if all(part in bank_text for part in name_parts if len(part) >= 2):
                    name_matched = True

    if payer_company and len(payer_company) >= 2 and payer_company in bank_text:
        name_matched = True

    if name_matched:
        score = min(100, score + 15)  # 名称匹配加15分

    return score


def get_match_level(score):
    """根据分数获取匹配级别"""
    if score >= 200:
        return 'REF匹配'
    elif score >= 100:
        return '精确匹配'
    elif score >= 80:
        return '高度匹配'
    elif score >= 60:
        return '可能匹配'
    elif score >= 40:
        return '参考匹配'
    else:
        return '不匹配'


@reconciliation_bp.route('/api/manual-match', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def manual_match():
    """手动匹配API"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        receipt_id = data.get('receipt_id')

        if not transaction_id or not receipt_id:
            return jsonify({'success': False, 'message': '缺少交易ID或收款ID'})

        # 查找银行交易
        transaction = BankTransaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'success': False, 'message': '银行交易记录不存在'})

        # 查找收款记录
        receipt = ProjectReceipt.query.get(receipt_id)
        if not receipt:
            return jsonify({'success': False, 'message': '收款记录不存在'})

        # 检查是否已经匹配
        if transaction.matched_receipt_id:
            return jsonify({'success': False, 'message': '该银行交易已匹配其他收款记录'})

        existing_match = BankTransaction.query.filter_by(matched_receipt_id=receipt_id).first()
        if existing_match:
            return jsonify({'success': False, 'message': '该收款记录已被其他银行交易匹配'})

        # 执行匹配
        current_time = datetime.utcnow()
        current_user_name = current_user.username if current_user else 'system'

        transaction.matched_receipt_id = receipt_id
        transaction.reconciliation_status = 'matched'
        # 填充收款单号到 REF/EO 字段
        transaction.accounting_ref = receipt.receipt_number
        # 自动确认该银行记录
        transaction.is_confirmed = True
        transaction.confirmed_at = current_time
        transaction.confirmed_by = current_user_name
        transaction.updated_at = current_time

        # 同时更新收款记录的核对状态
        receipt.is_reconciled = True
        receipt.reconciled_at = current_time
        receipt.reconciled_by = current_user_name

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '匹配成功，已自动确认银行记录和收款记录',
            'transaction_id': transaction_id,
            'receipt_id': receipt_id,
            'receipt_number': receipt.receipt_number
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"手动匹配失败: {str(e)}")
        return jsonify({'success': False, 'message': f'匹配失败: {str(e)}'})


@reconciliation_bp.route('/api/quick-match-by-ref', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def quick_match_by_ref():
    """根据REF/EO字段快速匹配收据或EO"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')

        if not transaction_id:
            return jsonify({'success': False, 'message': '缺少交易ID'})

        transaction = BankTransaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'success': False, 'message': '银行交易记录不存在'})

        ref = (transaction.accounting_ref or '').strip()
        if not ref:
            return jsonify({'success': False, 'message': 'REF/EO字段为空，请先填写收据号或EO号'})

        # 已经匹配过的不再重复匹配
        if transaction.matched_receipt_id or transaction.eo_id:
            return jsonify({'success': False, 'message': '该交易已有匹配记录'})

        current_time = datetime.utcnow()
        current_user_name = current_user.username if current_user else 'system'

        # 尝试匹配收据（收入类型优先匹配收据）
        receipt = ProjectReceipt.query.filter_by(receipt_number=ref).first()
        if receipt:
            # 检查收据是否已被其他交易匹配
            existing = BankTransaction.query.filter_by(matched_receipt_id=receipt.id).first()
            if existing:
                return jsonify({'success': False, 'message': f'收据 {ref} 已被其他银行交易匹配'})

            transaction.matched_receipt_id = receipt.id
            transaction.reconciliation_status = 'matched'
            transaction.updated_at = current_time

            # 更新收款记录核对状态
            receipt.is_reconciled = True
            receipt.reconciled_at = current_time
            receipt.reconciled_by = current_user_name

            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'已匹配收据 {ref}',
                'match_type': 'receipt',
                'receipt_number': receipt.receipt_number
            })

        # 尝试匹配EO（支出类型优先匹配EO）
        eo = ProjectEO.query.filter_by(eo_number=ref).first()
        if eo:
            # 检查EO是否已被其他交易匹配
            existing = BankTransaction.query.filter_by(eo_id=eo.id).first()
            if existing:
                return jsonify({'success': False, 'message': f'EO {ref} 已被其他银行交易匹配'})

            transaction.eo_id = eo.id
            transaction.reconciliation_status = 'matched'
            transaction.updated_at = current_time

            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'已匹配EO {ref}',
                'match_type': 'eo',
                'eo_number': eo.eo_number
            })

        return jsonify({'success': False, 'message': f'未找到匹配的收据或EO: {ref}'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"快速匹配失败: {str(e)}")
        return jsonify({'success': False, 'message': f'匹配失败: {str(e)}'})


@reconciliation_bp.route('/api/unmatch', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def unmatch():
    """取消匹配API - 支持通过transaction_id或receipt_id解除匹配"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        receipt_id = data.get('receipt_id')

        unmatch_count = 0
        old_receipt_id = None

        if receipt_id:
            # 通过receipt_id查找所有关联的银行交易并解除匹配
            transactions = BankTransaction.query.filter_by(matched_receipt_id=receipt_id).all()
            if not transactions:
                return jsonify({'success': False, 'message': '该收据未匹配任何银行流水'})

            old_receipt_id = receipt_id
            for tx in transactions:
                tx.matched_receipt_id = None
                tx.reconciliation_status = 'unmatched'
                tx.accounting_ref = None
                tx.is_confirmed = False
                tx.confirmed_at = None
                tx.confirmed_by = None
                tx.updated_at = datetime.utcnow()
                unmatch_count += 1

            # 更新收据的核对状态
            from App_new.business.projects.models.receipt import ProjectReceipt
            receipt = ProjectReceipt.query.get(receipt_id)
            if receipt:
                receipt.is_reconciled = False
                receipt.reconciled_at = None
                receipt.reconciled_by = None

        elif transaction_id:
            # 原有逻辑：通过transaction_id解除匹配
            transaction = BankTransaction.query.get(transaction_id)
            if not transaction:
                return jsonify({'success': False, 'message': '银行交易记录不存在'})

            if not transaction.matched_receipt_id:
                return jsonify({'success': False, 'message': '该交易未匹配任何收款记录'})

            old_receipt_id = transaction.matched_receipt_id
            transaction.matched_receipt_id = None
            transaction.reconciliation_status = 'unmatched'
            transaction.accounting_ref = None
            transaction.is_confirmed = False
            transaction.confirmed_at = None
            transaction.confirmed_by = None
            transaction.updated_at = datetime.utcnow()
            unmatch_count = 1
        else:
            return jsonify({'success': False, 'message': '缺少交易ID或收据ID'})

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已解除 {unmatch_count} 条匹配记录',
            'transaction_id': transaction_id,
            'old_receipt_id': old_receipt_id,
            'unmatch_count': unmatch_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"取消匹配失败: {str(e)}")
        return jsonify({'success': False, 'message': f'取消匹配失败: {str(e)}'})


@reconciliation_bp.route('/api/mark-personal', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def mark_personal():
    """标记为个人转账API"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        label = data.get('label', '个人转账')  # 可以是：个人消费、个人商用等

        if not transaction_ids:
            return jsonify({'success': False, 'message': '请选择要标记的交易记录'})

        count = 0
        for tx_id in transaction_ids:
            transaction = BankTransaction.query.get(tx_id)
            if transaction:
                transaction.owner_label = label
                transaction.owner_type = 'personal' if '消费' in label else 'personal_business'
                transaction.updated_at = datetime.utcnow()
                count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已将 {count} 条记录标记为{label}',
            'count': count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"标记个人转账失败: {str(e)}")
        return jsonify({'success': False, 'message': f'标记失败: {str(e)}'})


@reconciliation_bp.route('/api/create-receipt', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def create_receipt_from_transaction():
    """从银行记录创建收款API"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        header_id = data.get('header_id')  # 项目ID

        if not transaction_id:
            return jsonify({'success': False, 'message': '缺少银行交易ID'})
        if not header_id:
            return jsonify({'success': False, 'message': '请选择关联项目'})

        # 查找银行交易
        transaction = BankTransaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'success': False, 'message': '银行交易记录不存在'})

        # 检查是否已经匹配
        if transaction.matched_receipt_id:
            return jsonify({'success': False, 'message': '该银行交易已有匹配的收款记录'})

        # 查找项目
        header = ProjectHeader.query.get(header_id)
        if not header:
            return jsonify({'success': False, 'message': '项目不存在'})

        # 创建收款记录
        receipt_number = ProjectReceipt.generate_receipt_number()

        new_receipt = ProjectReceipt(
            receipt_number=receipt_number,
            header_id=header_id,
            amount=transaction.amount,
            currency='SGD',  # 默认新币
            payment_method='bank_transfer',
            payment_date=transaction.transaction_date,
            payer_name=transaction.counterparty_name or '',
            bank_name=transaction.statement.bank_name if transaction.statement else '',
            account_number=transaction.statement.account_number if transaction.statement else '',
            transaction_id=transaction.transaction_id,
            status='confirmed',  # 银行记录已确认，直接确认收款
            remarks=f'从银行流水自动创建 (交易ID: {transaction.id})',
            created_by=current_user.username if current_user else 'system'
        )

        db.session.add(new_receipt)
        db.session.flush()  # 获取新收款记录ID

        # 关联银行交易
        transaction.matched_receipt_id = new_receipt.id
        transaction.reconciliation_status = 'matched'
        # 填充收款单号到 REF/EO 字段
        transaction.accounting_ref = new_receipt.receipt_number
        # 自动确认该银行记录
        transaction.is_confirmed = True
        transaction.confirmed_at = datetime.utcnow()
        transaction.confirmed_by = current_user.username if current_user else 'system'
        transaction.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '收款记录创建成功，已自动确认银行记录',
            'receipt_id': new_receipt.id,
            'receipt_number': new_receipt.receipt_number,
            'transaction_id': transaction_id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"创建收款记录失败: {str(e)}")
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'})


@reconciliation_bp.route('/api/batch-match', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def batch_match():
    """批量匹配API（接受匹配建议）"""
    try:
        data = request.get_json()
        matches = data.get('matches', [])  # [{transaction_id, receipt_id}, ...]

        if not matches:
            return jsonify({'success': False, 'message': '没有选择要匹配的记录'})

        success_count = 0
        failed_items = []

        for match in matches:
            tx_id = match.get('transaction_id')
            receipt_id = match.get('receipt_id')

            transaction = BankTransaction.query.get(tx_id)
            receipt = ProjectReceipt.query.get(receipt_id)

            if not transaction:
                failed_items.append({'tx_id': tx_id, 'reason': '交易不存在'})
                continue
            if not receipt:
                failed_items.append({'tx_id': tx_id, 'reason': '收款不存在'})
                continue
            if transaction.matched_receipt_id:
                failed_items.append({'tx_id': tx_id, 'reason': '已有匹配'})
                continue

            existing = BankTransaction.query.filter_by(matched_receipt_id=receipt_id).first()
            if existing:
                failed_items.append({'tx_id': tx_id, 'reason': '收款已被匹配'})
                continue

            # 执行匹配
            current_time = datetime.utcnow()
            current_user_name = current_user.username if current_user else 'system'

            transaction.matched_receipt_id = receipt_id
            transaction.reconciliation_status = 'matched'
            # 填充收款单号到 REF/EO 字段
            transaction.accounting_ref = receipt.receipt_number
            # 自动确认该银行记录
            transaction.is_confirmed = True
            transaction.confirmed_at = current_time
            transaction.confirmed_by = current_user_name
            transaction.updated_at = current_time

            # 同时更新收款记录的核对状态
            receipt.is_reconciled = True
            receipt.reconciled_at = current_time
            receipt.reconciled_by = current_user_name

            success_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功匹配 {success_count} 条记录，已自动确认',
            'success_count': success_count,
            'failed_count': len(failed_items),
            'failed_items': failed_items
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"批量匹配失败: {str(e)}")
        return jsonify({'success': False, 'message': f'批量匹配失败: {str(e)}'})


@reconciliation_bp.route('/api/projects')
@login_required
@staff_only
def get_projects():
    """获取项目列表（用于创建收款时选择）"""
    try:
        keyword = request.args.get('keyword', '')

        query = ProjectHeader.query.filter(
            ProjectHeader.status.in_(['active', 'draft'])
        )

        if keyword:
            query = query.filter(
                or_(
                    ProjectHeader.hid.ilike(f'%{keyword}%'),
                    ProjectHeader.desc.ilike(f'%{keyword}%')
                )
            )

        query = query.order_by(desc(ProjectHeader.created_at))
        projects = query.limit(50).all()

        project_data = [{
            'id': p.id,
            'project_number': p.hid,
            'name': p.desc or '',
            'status': p.status
        } for p in projects]

        return jsonify({
            'success': True,
            'projects': project_data
        })

    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取项目列表失败: {str(e)}'})


@reconciliation_bp.route('/api/accounts')
@login_required
@staff_only
def get_accounts():
    """获取指定银行的账户列表"""
    try:
        bank_name = request.args.get('bank_name', '')

        query = db.session.query(BankStatement.account_name).filter(
            BankStatement.account_name.isnot(None),
            BankStatement.account_name != '上传文件'
        )

        if bank_name:
            query = query.filter(BankStatement.bank_name == bank_name)

        accounts = query.distinct().order_by(BankStatement.account_name).all()
        account_list = [a[0] for a in accounts]

        return jsonify({
            'success': True,
            'accounts': account_list
        })

    except Exception as e:
        logger.error(f"获取账户列表失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取账户列表失败: {str(e)}'})


@reconciliation_bp.route('/api/mark-reconciled', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def mark_reconciled():
    """标记为已核对API"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        receipt_ids = data.get('receipt_ids', [])
        is_reconciled = data.get('is_reconciled', True)

        if not transaction_ids and not receipt_ids:
            return jsonify({'success': False, 'message': '请选择要标记的记录'})

        tx_count = 0
        receipt_count = 0
        current_time = datetime.utcnow()
        current_user_name = current_user.username if current_user else 'system'

        # 标记银行交易记录
        for tx_id in transaction_ids:
            transaction = BankTransaction.query.get(tx_id)
            if transaction:
                transaction.is_reconciled = is_reconciled
                if is_reconciled:
                    transaction.reconciled_at = current_time
                    transaction.reconciled_by = current_user_name
                else:
                    transaction.reconciled_at = None
                    transaction.reconciled_by = None
                transaction.updated_at = current_time
                tx_count += 1

        # 标记收款记录
        for receipt_id in receipt_ids:
            receipt = ProjectReceipt.query.get(receipt_id)
            if receipt:
                receipt.is_reconciled = is_reconciled
                if is_reconciled:
                    receipt.reconciled_at = current_time
                    receipt.reconciled_by = current_user_name
                else:
                    receipt.reconciled_at = None
                    receipt.reconciled_by = None
                receipt.updated_at = current_time
                receipt_count += 1

        db.session.commit()

        action = '核对' if is_reconciled else '取消核对'
        message_parts = []
        if tx_count > 0:
            message_parts.append(f'{tx_count} 条银行记录')
        if receipt_count > 0:
            message_parts.append(f'{receipt_count} 条收款记录')

        return jsonify({
            'success': True,
            'message': f'已{action} ' + '、'.join(message_parts),
            'transaction_count': tx_count,
            'receipt_count': receipt_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"标记核对状态失败: {str(e)}")
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})


# ==================== 银行支出与EO对比功能 ====================

@reconciliation_bp.route('/bank-eo')
@login_required
@staff_only
def bank_eo_compare():
    """银行支出与EO对比主页面"""
    # 获取筛选参数
    bank_name = request.args.get('bank_name', '')
    account_name = request.args.get('account_name', '')
    supplier_id = request.args.get('supplier_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status = request.args.get('status', 'all')  # all, unmatched, matched

    # 获取可用的银行和账户选项
    bank_options = db.session.query(BankStatement.bank_name).distinct().order_by(BankStatement.bank_name).all()
    bank_options = [b[0] for b in bank_options]

    # 获取账户选项（根据选择的银行筛选）
    account_query = db.session.query(BankStatement.account_name).filter(
        BankStatement.account_name.isnot(None),
        BankStatement.account_name != '上传文件'
    )
    if bank_name:
        account_query = account_query.filter(BankStatement.bank_name == bank_name)
    account_options = account_query.distinct().order_by(BankStatement.account_name).all()
    account_options = [a[0] for a in account_options]

    # 获取供应商选项（只获取有EO记录的供应商）
    supplier_query = db.session.query(CustomerCompany.id, CustomerCompany.company_name).join(
        ProjectRef, ProjectRef.supplier_id == CustomerCompany.id
    ).join(
        ProjectEO, ProjectEO.ref_id == ProjectRef.id
    ).filter(
        CustomerCompany.is_supplier == True
    ).distinct().order_by(CustomerCompany.company_name)
    supplier_options = supplier_query.all()

    # 设置默认日期范围（最近30天）
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    filters = {
        'bank_name': bank_name,
        'account_name': account_name,
        'supplier_id': supplier_id,
        'start_date': start_date,
        'end_date': end_date,
        'status': status
    }

    return render_template('finance/reconciliation/bank_eo_compare.html',
                         filters=filters,
                         bank_options=bank_options,
                         account_options=account_options,
                         supplier_options=supplier_options)


@reconciliation_bp.route('/api/eo-compare-data')
@login_required
@staff_only
def get_eo_compare_data():
    """获取银行支出与EO对比数据API"""
    try:
        bank_name = request.args.get('bank_name', '')
        account_name = request.args.get('account_name', '')
        supplier_id = request.args.get('supplier_id', '')
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')
        status = request.args.get('status', 'all')
        hide_reconciled = request.args.get('hide_reconciled', 'true') == 'true'

        # 解析日期
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # 查询银行支出记录（只查Debit类型）
        tx_query = BankTransaction.query.join(BankStatement).filter(
            BankTransaction.transaction_type == 'debit'
        )

        if bank_name:
            tx_query = tx_query.filter(BankStatement.bank_name == bank_name)
        if account_name:
            tx_query = tx_query.filter(BankStatement.account_name == account_name)
        if start_date:
            tx_query = tx_query.filter(BankTransaction.transaction_date >= start_date)
        if end_date:
            tx_query = tx_query.filter(BankTransaction.transaction_date <= end_date)

        # 隐藏已核对的记录
        if hide_reconciled:
            tx_query = tx_query.filter(
                or_(
                    BankTransaction.is_reconciled == False,
                    BankTransaction.is_reconciled.is_(None)
                )
            )

        # 根据状态筛选
        if status == 'all':
            # 默认排除已匹配EO的记录
            tx_query = tx_query.filter(
                or_(
                    BankTransaction.eo_id.is_(None),
                    BankTransaction.eo_id == 0
                )
            )
            # 排除已确认的个人消费记录
            tx_query = tx_query.filter(
                ~and_(
                    BankTransaction.owner_label.in_(['个人消费', '个人商用', 'personal']),
                    BankTransaction.is_confirmed == True
                )
            )
        elif status == 'unmatched':
            tx_query = tx_query.filter(
                or_(
                    BankTransaction.eo_id.is_(None),
                    BankTransaction.eo_id == 0
                ),
                # 排除个人消费标记的记录
                or_(
                    BankTransaction.owner_label.is_(None),
                    BankTransaction.owner_label == '',
                    ~BankTransaction.owner_label.in_(['个人消费', '个人商用', 'personal'])
                )
            )
        elif status == 'matched':
            tx_query = tx_query.filter(
                BankTransaction.eo_id.isnot(None),
                BankTransaction.eo_id != 0
            )
        elif status == 'reconciled':
            # 只显示已核对的记录
            tx_query = BankTransaction.query.join(BankStatement).filter(
                BankTransaction.transaction_type == 'debit',
                BankTransaction.is_reconciled == True
            )
            if bank_name:
                tx_query = tx_query.filter(BankStatement.bank_name == bank_name)
            if account_name:
                tx_query = tx_query.filter(BankStatement.account_name == account_name)
            if start_date:
                tx_query = tx_query.filter(BankTransaction.transaction_date >= start_date)
            if end_date:
                tx_query = tx_query.filter(BankTransaction.transaction_date <= end_date)

        tx_query = tx_query.order_by(desc(BankTransaction.transaction_date))
        transactions = tx_query.limit(200).all()

        # 查询EO记录（草稿、已确认或已付款的，排除已取消和作废的）
        eo_query = ProjectEO.query.join(ProjectRef, ProjectEO.ref_id == ProjectRef.id).filter(
            ProjectEO.status.in_(['confirmed', 'paid'])
        )

        # 按供应商筛选
        if supplier_id:
            eo_query = eo_query.filter(ProjectRef.supplier_id == int(supplier_id))

        # EO日期筛选：以EO生成日期为准，开始日期往前推7天（因为银行扣款会滞后）
        if start_date:
            eo_start_date = start_date - timedelta(days=7)
            eo_query = eo_query.filter(
                or_(
                    ProjectEO.eo_date >= eo_start_date,
                    and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at >= datetime.combine(eo_start_date, datetime.min.time())),
                    # 如果日期都为空，也显示
                    and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at.is_(None))
                )
            )
        if end_date:
            eo_query = eo_query.filter(
                or_(
                    ProjectEO.eo_date <= end_date,
                    and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at <= datetime.combine(end_date, datetime.max.time())),
                    # 如果日期都为空，也显示
                    and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at.is_(None))
                )
            )

        # 隐藏已核对的记录
        if hide_reconciled:
            eo_query = eo_query.filter(
                or_(
                    ProjectEO.is_reconciled == False,
                    ProjectEO.is_reconciled.is_(None)
                )
            )

        # 根据状态筛选
        # 先获取已匹配的EO ID列表
        matched_eo_ids = db.session.query(BankTransaction.eo_id).filter(
            BankTransaction.eo_id.isnot(None),
            BankTransaction.eo_id != 0
        ).subquery()

        if status == 'all':
            # 默认排除已匹配的EO
            eo_query = eo_query.filter(~ProjectEO.id.in_(matched_eo_ids))
        elif status == 'unmatched':
            eo_query = eo_query.filter(~ProjectEO.id.in_(matched_eo_ids))
        elif status == 'matched':
            eo_query = eo_query.filter(ProjectEO.id.in_(matched_eo_ids))
        elif status == 'reconciled':
            # 只显示已核对的EO
            eo_query = ProjectEO.query.join(ProjectRef, ProjectEO.ref_id == ProjectRef.id).filter(
                ProjectEO.status.in_(['confirmed', 'paid']),
                ProjectEO.is_reconciled == True
            )
            if supplier_id:
                eo_query = eo_query.filter(ProjectRef.supplier_id == int(supplier_id))
            if start_date:
                eo_start_date = start_date - timedelta(days=7)
                eo_query = eo_query.filter(
                    or_(
                        ProjectEO.eo_date >= eo_start_date,
                        and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at >= datetime.combine(eo_start_date, datetime.min.time())),
                        and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at.is_(None))
                    )
                )
            if end_date:
                eo_query = eo_query.filter(
                    or_(
                        ProjectEO.eo_date <= end_date,
                        and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at <= datetime.combine(end_date, datetime.max.time())),
                        and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at.is_(None))
                    )
                )

        eo_query = eo_query.order_by(desc(ProjectEO.eo_date), desc(ProjectEO.created_at))
        eos = eo_query.limit(200).all()

        # 格式化数据
        tx_data = []
        for tx in transactions:
            tx_dict = tx.to_dict()
            tx_dict['bank_name'] = tx.statement.bank_name if tx.statement else ''
            tx_dict['account_name'] = tx.statement.account_name if tx.statement else ''
            tx_data.append(tx_dict)

        eo_data = []
        for eo in eos:
            eo_dict = eo.to_dict()
            # 添加REF和项目信息
            if eo.ref:
                eo_dict['ref_number'] = eo.ref.ref_number if eo.ref.ref_number else ''
                eo_dict['cost_price'] = float(eo.ref.cost_price) if eo.ref.cost_price else 0
                eo_dict['currency'] = eo.ref.currency or 'SGD'
                if eo.ref.header:
                    eo_dict['project_number'] = eo.ref.header.hid
                    eo_dict['project_name'] = eo.ref.header.desc or ''
                    eo_dict['header_id'] = eo.ref.header.id
                else:
                    eo_dict['project_number'] = ''
                    eo_dict['project_name'] = ''
                    eo_dict['header_id'] = None
                # 供应商信息
                if eo.ref.supplier:
                    eo_dict['supplier_name'] = eo.ref.supplier.company_name or ''
                else:
                    eo_dict['supplier_name'] = ''
            else:
                eo_dict['ref_number'] = ''
                eo_dict['cost_price'] = 0
                eo_dict['currency'] = 'SGD'
                eo_dict['project_number'] = ''
                eo_dict['project_name'] = ''
                eo_dict['header_id'] = None
                eo_dict['supplier_name'] = ''

            # 检查是否已匹配
            matched_tx = BankTransaction.query.filter_by(eo_id=eo.id).first()
            eo_dict['is_matched'] = matched_tx is not None
            eo_dict['matched_tx_id'] = matched_tx.id if matched_tx else None
            eo_data.append(eo_dict)

        return jsonify({
            'success': True,
            'bank_transactions': tx_data,
            'project_eos': eo_data
        })

    except Exception as e:
        logger.error(f"获取EO对比数据失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取数据失败: {str(e)}'})


@reconciliation_bp.route('/api/eo-auto-match')
@login_required
@staff_only
def eo_auto_match_suggestions():
    """EO自动匹配建议API"""
    try:
        bank_name = request.args.get('bank_name', '')
        account_name = request.args.get('account_name', '')
        supplier_id = request.args.get('supplier_id', '')
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')

        # 解析日期
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # 查询未匹配的银行支出记录
        tx_query = BankTransaction.query.join(BankStatement).filter(
            BankTransaction.transaction_type == 'debit',
            or_(
                BankTransaction.eo_id.is_(None),
                BankTransaction.eo_id == 0
            )
        )

        # 排除已核对的记录
        tx_query = tx_query.filter(
            or_(
                BankTransaction.is_reconciled == False,
                BankTransaction.is_reconciled.is_(None)
            )
        )

        # 排除已确认的个人消费记录
        tx_query = tx_query.filter(
            ~and_(
                BankTransaction.owner_label.in_(['个人消费', '个人商用', 'personal']),
                BankTransaction.is_confirmed == True
            )
        )

        if bank_name:
            tx_query = tx_query.filter(BankStatement.bank_name == bank_name)
        if account_name:
            tx_query = tx_query.filter(BankStatement.account_name == account_name)
        if start_date:
            tx_query = tx_query.filter(BankTransaction.transaction_date >= start_date)
        if end_date:
            tx_query = tx_query.filter(BankTransaction.transaction_date <= end_date)

        transactions = tx_query.all()

        # 查询未匹配的EO记录
        matched_eo_ids = db.session.query(BankTransaction.eo_id).filter(
            BankTransaction.eo_id.isnot(None),
            BankTransaction.eo_id != 0
        ).subquery()

        eo_query = ProjectEO.query.join(ProjectRef, ProjectEO.ref_id == ProjectRef.id).filter(
            ProjectEO.status.in_(['confirmed', 'paid']),
            ~ProjectEO.id.in_(matched_eo_ids)
        )

        # 按供应商筛选
        if supplier_id:
            eo_query = eo_query.filter(ProjectRef.supplier_id == int(supplier_id))

        # EO日期筛选：以EO生成日期为准，开始日期往前推14天（自动匹配范围更宽）
        if start_date:
            eo_start_date = start_date - timedelta(days=14)
            eo_query = eo_query.filter(
                or_(
                    ProjectEO.eo_date >= eo_start_date,
                    and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at >= datetime.combine(eo_start_date, datetime.min.time())),
                    and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at.is_(None))
                )
            )
        if end_date:
            eo_query = eo_query.filter(
                or_(
                    ProjectEO.eo_date <= end_date,
                    and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at <= datetime.combine(end_date, datetime.max.time())),
                    and_(ProjectEO.eo_date.is_(None), ProjectEO.created_at.is_(None))
                )
            )

        eos = eo_query.all()

        # 构建EO号 -> EO对象的索引，用于REF优先匹配
        eo_by_number = {}
        for e in eos:
            if e.eo_number:
                eo_by_number[e.eo_number.strip()] = e

        # 计算匹配建议
        suggestions = []
        for tx in transactions:
            best_match = None
            best_score = 0

            # 优先：通过 accounting_ref 匹配EO号
            ref = (tx.accounting_ref or '').strip()
            if ref and ref in eo_by_number:
                best_match = eo_by_number[ref]
                best_score = 200  # REF直接匹配，最高优先级
            else:
                # 回退：金额+日期+供应商匹配
                for eo in eos:
                    score = calculate_eo_match_score(tx, eo)
                    if score > best_score and score >= 40:
                        best_score = score
                        best_match = eo

            if best_match:
                # 获取REF信息
                ref_number = ''
                cost_price = 0
                supplier_name = ''
                project_number = ''
                header_id = None
                if best_match.ref:
                    ref_number = best_match.ref.ref_number or ''
                    cost_price = float(best_match.ref.cost_price) if best_match.ref.cost_price else 0
                    if best_match.ref.supplier:
                        supplier_name = best_match.ref.supplier.company_name or ''
                    if best_match.ref.header:
                        project_number = best_match.ref.header.hid or ''
                        header_id = best_match.ref.header.id

                suggestions.append({
                    'transaction_id': tx.id,
                    'transaction_date': tx.transaction_date.isoformat(),
                    'transaction_amount': float(tx.amount),
                    'transaction_counterparty': tx.counterparty_name or '',
                    'transaction_description': tx.description or '',
                    'transaction_accounting_ref': tx.accounting_ref or '',
                    'transaction_bank_name': tx.statement.bank_name if tx.statement else '',
                    'transaction_account_name': tx.statement.account_name if tx.statement else '',
                    'eo_id': best_match.id,
                    'eo_number': best_match.eo_number,
                    'eo_date': best_match.paid_date.isoformat() if best_match.paid_date else (best_match.eo_date.isoformat() if best_match.eo_date else ''),
                    'eo_amount': cost_price,
                    'pay_amount': float(best_match.pay_amount) if best_match.pay_amount else cost_price,
                    'ref_number': ref_number,
                    'supplier_name': supplier_name,
                    'project_number': project_number,
                    'header_id': header_id,
                    'match_score': best_score,
                    'match_level': get_match_level(best_score)
                })

        # 按匹配分数降序排列
        suggestions.sort(key=lambda x: x['match_score'], reverse=True)

        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'total_suggestions': len(suggestions)
        })

    except Exception as e:
        logger.error(f"生成EO匹配建议失败: {str(e)}")
        return jsonify({'success': False, 'message': f'生成匹配建议失败: {str(e)}'})


def calculate_eo_match_score(transaction, eo):
    """
    计算银行支出与EO的匹配分数

    匹配规则：
    1. 精确匹配（100分）：金额完全相等 + 日期相同
    2. 高度匹配（80分）：金额完全相等 + 日期±3天内
    3. 可能匹配（60分）：金额完全相等 + 日期±7天内
    4. 参考匹配（40分）：金额相近（±1%）或供应商名称匹配
    """
    score = 0

    tx_amount = float(transaction.amount or 0)

    # EO金额优先使用pay_amount，否则使用REF的cost_price
    eo_amount = float(eo.pay_amount) if eo.pay_amount else 0
    if eo_amount == 0 and eo.ref and eo.ref.cost_price:
        eo_amount = float(eo.ref.cost_price)

    # 金额为0的记录不参与匹配
    if eo_amount == 0 or tx_amount == 0:
        return 0

    # 金额匹配（允许0.01误差）
    amount_match = abs(tx_amount - eo_amount) < 0.01

    if not amount_match:
        # 检查金额相近（±1%）
        diff_ratio = abs(tx_amount - eo_amount) / eo_amount
        if diff_ratio > 0.01:  # 差异超过1%
            return 0
        else:
            amount_match = True  # 金额相近也算匹配

    # 日期匹配
    tx_date = transaction.transaction_date
    # EO日期优先使用 paid_date，其次 eo_date，最后 created_at
    eo_date = eo.paid_date or eo.eo_date
    if not eo_date and eo.created_at:
        eo_date = eo.created_at.date() if hasattr(eo.created_at, 'date') else eo.created_at

    if tx_date and eo_date:
        date_diff = abs((tx_date - eo_date).days)

        if date_diff == 0:
            score = 100  # 精确匹配：同一天
        elif date_diff <= 3:
            score = 90  # 高度匹配：±3天内
        elif date_diff <= 7:
            score = 70  # 可能匹配：±7天
        elif date_diff <= 14:
            score = 50  # 参考匹配：±14天
        else:
            score = 40  # 仅金额匹配
    else:
        score = 40  # 仅金额匹配

    # 供应商名称匹配加分
    counterparty = (transaction.counterparty_name or '').lower()
    description = (transaction.description or '').lower()
    bank_text = counterparty + ' ' + description

    supplier_name = ''
    if eo.ref and eo.ref.supplier:
        supplier_name = (eo.ref.supplier.name or '').lower().strip()

    if supplier_name and len(supplier_name) >= 2 and supplier_name in bank_text:
        score = min(100, score + 15)

    # EO编号匹配加分
    eo_number = (eo.eo_number or '').lower()
    if eo_number and eo_number in bank_text:
        score = min(100, score + 10)

    return score


@reconciliation_bp.route('/api/eo-manual-match', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def eo_manual_match():
    """EO手动匹配API"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        eo_id = data.get('eo_id')

        if not transaction_id or not eo_id:
            return jsonify({'success': False, 'message': '缺少交易ID或EO ID'})

        # 查找银行交易
        transaction = BankTransaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'success': False, 'message': '银行交易记录不存在'})

        # 查找EO记录
        eo = ProjectEO.query.get(eo_id)
        if not eo:
            return jsonify({'success': False, 'message': 'EO记录不存在'})

        # 检查是否已经匹配
        if transaction.eo_id:
            return jsonify({'success': False, 'message': '该银行交易已匹配其他EO记录'})

        existing_match = BankTransaction.query.filter_by(eo_id=eo_id).first()
        if existing_match:
            return jsonify({'success': False, 'message': '该EO记录已被其他银行交易匹配'})

        # 执行匹配
        transaction.eo_id = eo_id
        transaction.accounting_ref = eo.eo_number
        # 自动确认该银行记录
        transaction.is_confirmed = True
        transaction.confirmed_at = datetime.utcnow()
        transaction.confirmed_by = current_user.username if current_user else 'system'
        transaction.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '匹配成功，已自动确认银行记录',
            'transaction_id': transaction_id,
            'eo_id': eo_id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"EO手动匹配失败: {str(e)}")
        return jsonify({'success': False, 'message': f'匹配失败: {str(e)}'})


@reconciliation_bp.route('/api/eo-unmatch', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def eo_unmatch():
    """取消EO匹配API - 支持通过transaction_id或eo_id解除匹配"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        eo_id = data.get('eo_id')

        if not transaction_id and not eo_id:
            return jsonify({'success': False, 'message': '缺少交易ID或EO ID'})

        unmatch_count = 0
        current_time = datetime.utcnow()

        if transaction_id:
            # 通过银行交易ID解除匹配
            transaction = BankTransaction.query.get(transaction_id)
            if not transaction:
                return jsonify({'success': False, 'message': '银行交易记录不存在'})

            if not transaction.eo_id:
                return jsonify({'success': False, 'message': '该交易未匹配任何EO记录'})

            # 取消匹配
            old_eo_id = transaction.eo_id
            transaction.eo_id = None
            transaction.reconciliation_status = 'unmatched'
            transaction.accounting_ref = None
            transaction.updated_at = current_time
            unmatch_count = 1

        elif eo_id:
            # 通过EO ID解除所有关联的银行交易匹配
            # 1. 查找直接关联的银行交易 (eo_id字段)
            transactions = BankTransaction.query.filter_by(eo_id=eo_id).all()
            for tx in transactions:
                tx.eo_id = None
                tx.reconciliation_status = 'unmatched'
                tx.accounting_ref = None
                tx.updated_at = current_time
                unmatch_count += 1

            # 2. 查找通过多对多匹配表关联的记录
            matches = BankTransactionMatch.query.filter_by(match_type='eo', match_id=eo_id).all()
            for match in matches:
                tx = BankTransaction.query.get(match.transaction_id)
                if tx:
                    # 检查是否还有其他匹配
                    other_matches = BankTransactionMatch.query.filter(
                        BankTransactionMatch.transaction_id == tx.id,
                        BankTransactionMatch.id != match.id
                    ).count()
                    if other_matches == 0:
                        tx.reconciliation_status = 'unmatched'
                    tx.updated_at = current_time
                db.session.delete(match)
                unmatch_count += 1

            # 3. 更新EO的核对状态
            eo = ProjectEO.query.get(eo_id)
            if eo:
                eo.is_reconciled = False
                eo.reconciled_at = None
                eo.reconciled_by = None

            if unmatch_count == 0:
                return jsonify({'success': False, 'message': '该EO没有关联的银行交易记录'})

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已解除 {unmatch_count} 条匹配记录',
            'unmatch_count': unmatch_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"取消EO匹配失败: {str(e)}")
        return jsonify({'success': False, 'message': f'取消匹配失败: {str(e)}'})


@reconciliation_bp.route('/api/eo-batch-match', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def eo_batch_match():
    """EO批量匹配API（接受匹配建议）"""
    try:
        data = request.get_json()
        matches = data.get('matches', [])  # [{transaction_id, eo_id}, ...]

        if not matches:
            return jsonify({'success': False, 'message': '没有选择要匹配的记录'})

        success_count = 0
        failed_items = []

        for match in matches:
            tx_id = match.get('transaction_id')
            eo_id = match.get('eo_id')

            transaction = BankTransaction.query.get(tx_id)
            eo = ProjectEO.query.get(eo_id)

            if not transaction:
                failed_items.append({'tx_id': tx_id, 'reason': '交易不存在'})
                continue
            if not eo:
                failed_items.append({'tx_id': tx_id, 'reason': 'EO不存在'})
                continue
            if transaction.eo_id:
                failed_items.append({'tx_id': tx_id, 'reason': '已有匹配'})
                continue

            existing = BankTransaction.query.filter_by(eo_id=eo_id).first()
            if existing:
                failed_items.append({'tx_id': tx_id, 'reason': 'EO已被匹配'})
                continue

            # 执行匹配
            transaction.eo_id = eo_id
            transaction.accounting_ref = eo.eo_number
            # 自动确认该银行记录
            transaction.is_confirmed = True
            transaction.confirmed_at = datetime.utcnow()
            transaction.confirmed_by = current_user.username if current_user else 'system'
            transaction.updated_at = datetime.utcnow()
            success_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功匹配 {success_count} 条记录，已自动确认',
            'success_count': success_count,
            'failed_count': len(failed_items),
            'failed_items': failed_items
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"EO批量匹配失败: {str(e)}")
        return jsonify({'success': False, 'message': f'批量匹配失败: {str(e)}'})


@reconciliation_bp.route('/api/eo-mark-reconciled', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def eo_mark_reconciled():
    """标记EO为已核对API"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        eo_ids = data.get('eo_ids', [])
        is_reconciled = data.get('is_reconciled', True)

        if not transaction_ids and not eo_ids:
            return jsonify({'success': False, 'message': '请选择要标记的记录'})

        tx_count = 0
        eo_count = 0
        current_time = datetime.utcnow()
        current_user_name = current_user.username if current_user else 'system'

        # 标记银行交易记录
        for tx_id in transaction_ids:
            transaction = BankTransaction.query.get(tx_id)
            if transaction:
                transaction.is_reconciled = is_reconciled
                if is_reconciled:
                    transaction.reconciled_at = current_time
                    transaction.reconciled_by = current_user_name
                else:
                    transaction.reconciled_at = None
                    transaction.reconciled_by = None
                transaction.updated_at = current_time
                tx_count += 1

        # 标记EO记录
        for eo_id in eo_ids:
            eo = ProjectEO.query.get(eo_id)
            if eo:
                eo.is_reconciled = is_reconciled
                if is_reconciled:
                    eo.reconciled_at = current_time
                    eo.reconciled_by = current_user_name
                else:
                    eo.reconciled_at = None
                    eo.reconciled_by = None
                eo.updated_at = current_time
                eo_count += 1

        db.session.commit()

        action = '核对' if is_reconciled else '取消核对'
        message_parts = []
        if tx_count > 0:
            message_parts.append(f'{tx_count} 条银行记录')
        if eo_count > 0:
            message_parts.append(f'{eo_count} 条EO记录')

        return jsonify({
            'success': True,
            'message': f'已{action} ' + '、'.join(message_parts),
            'transaction_count': tx_count,
            'eo_count': eo_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"标记EO核对状态失败: {str(e)}")
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})


# ==================== 多对多匹配功能 ====================

@reconciliation_bp.route('/api/multi-match', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def multi_match():
    """
    多对多匹配API
    支持：
    - 一笔银行转账 → 多个收款/EO
    - 多笔银行转账 → 一个收款/EO

    请求格式：
    {
        "matches": [
            {"transaction_id": 1, "match_type": "receipt", "match_id": 101, "amount": 295.00},
            {"transaction_id": 1, "match_type": "receipt", "match_id": 102, "amount": 315.00},
            {"transaction_id": 2, "match_type": "eo", "match_id": 201, "amount": 416.21}
        ]
    }
    """
    try:
        data = request.get_json()
        matches = data.get('matches', [])

        if not matches:
            return jsonify({'success': False, 'message': '没有提供匹配数据'})

        success_count = 0
        failed_items = []
        current_user_name = current_user.username if current_user else 'system'

        for match in matches:
            tx_id = match.get('transaction_id')
            match_type = match.get('match_type')
            match_id = match.get('match_id')
            amount = match.get('amount')

            # 验证参数
            if not all([tx_id, match_type, match_id, amount]):
                failed_items.append({'transaction_id': tx_id, 'reason': '参数不完整'})
                continue

            if match_type not in ['receipt', 'eo']:
                failed_items.append({'transaction_id': tx_id, 'reason': '无效的匹配类型'})
                continue

            # 验证银行交易存在
            transaction = BankTransaction.query.get(tx_id)
            if not transaction:
                failed_items.append({'transaction_id': tx_id, 'reason': '银行交易不存在'})
                continue

            # 验证收款/EO存在
            if match_type == 'receipt':
                target = ProjectReceipt.query.get(match_id)
                if not target:
                    failed_items.append({'transaction_id': tx_id, 'reason': f'收款记录 {match_id} 不存在'})
                    continue
            else:
                target = ProjectEO.query.get(match_id)
                if not target:
                    failed_items.append({'transaction_id': tx_id, 'reason': f'EO记录 {match_id} 不存在'})
                    continue

            # 检查是否已存在该匹配
            existing = BankTransactionMatch.query.filter_by(
                transaction_id=tx_id,
                match_type=match_type,
                match_id=match_id
            ).first()

            if existing:
                # 更新金额
                existing.allocated_amount = amount
                existing.updated_at = datetime.utcnow()
            else:
                # 创建新匹配
                new_match = BankTransactionMatch(
                    transaction_id=tx_id,
                    match_type=match_type,
                    match_id=match_id,
                    allocated_amount=amount,
                    created_by=current_user_name
                )
                db.session.add(new_match)

            # 更新银行交易状态
            update_transaction_status(transaction, match_type, match_id, current_user_name)

            # 同时更新收款/EO的核对状态
            current_time = datetime.utcnow()
            target.is_reconciled = True
            target.reconciled_at = current_time
            target.reconciled_by = current_user_name

            success_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功创建 {success_count} 条匹配记录',
            'success_count': success_count,
            'failed_count': len(failed_items),
            'failed_items': failed_items
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"多对多匹配失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'匹配失败: {str(e)}'})


def update_transaction_status(transaction, match_type, match_id, username):
    """更新银行交易的匹配状态"""
    current_time = datetime.utcnow()

    # 更新确认状态
    transaction.is_confirmed = True
    transaction.confirmed_at = current_time
    transaction.confirmed_by = username
    transaction.updated_at = current_time

    # 多对多匹配时也要更新状态为已匹配
    transaction.reconciliation_status = 'matched'

    # 根据匹配类型更新对应字段（兼容旧逻辑）
    if match_type == 'receipt':
        # 如果是单一匹配，也更新旧字段
        matches = BankTransactionMatch.query.filter_by(
            transaction_id=transaction.id,
            match_type='receipt'
        ).all()
        if len(matches) == 1:
            transaction.matched_receipt_id = match_id
            receipt = ProjectReceipt.query.get(match_id)
            if receipt:
                transaction.accounting_ref = receipt.receipt_number
        else:
            # 多对多匹配：设置accounting_ref为所有收款单号
            receipt_numbers = []
            for m in matches:
                r = ProjectReceipt.query.get(m.match_id)
                if r:
                    receipt_numbers.append(r.receipt_number)
            if receipt_numbers:
                transaction.accounting_ref = ','.join(receipt_numbers)
    else:
        # EO匹配
        matches = BankTransactionMatch.query.filter_by(
            transaction_id=transaction.id,
            match_type='eo'
        ).all()
        if len(matches) == 1:
            transaction.eo_id = match_id
            eo = ProjectEO.query.get(match_id)
            if eo:
                transaction.accounting_ref = eo.eo_number
        else:
            # 多对多匹配：设置accounting_ref为所有EO单号
            eo_numbers = []
            for m in matches:
                e = ProjectEO.query.get(m.match_id)
                if e:
                    eo_numbers.append(e.eo_number)
            if eo_numbers:
                transaction.accounting_ref = ','.join(eo_numbers)


@reconciliation_bp.route('/api/remove-match', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def remove_match():
    """
    删除指定匹配记录

    请求格式：
    {
        "match_id": 123  // bank_transaction_matches 表的 ID
    }
    或
    {
        "transaction_id": 1,
        "match_type": "receipt",
        "target_id": 101
    }
    """
    try:
        data = request.get_json()

        # 方式1：通过 match_id 删除
        match_id = data.get('match_id')
        if match_id:
            match_record = BankTransactionMatch.query.get(match_id)
            if not match_record:
                return jsonify({'success': False, 'message': '匹配记录不存在'})

            transaction_id = match_record.transaction_id
            db.session.delete(match_record)

            # 检查是否还有其他匹配，如果没有则清除银行交易的匹配状态
            remaining = BankTransactionMatch.query.filter_by(transaction_id=transaction_id).count()
            if remaining == 0:
                transaction = BankTransaction.query.get(transaction_id)
                if transaction:
                    transaction.matched_receipt_id = None
                    transaction.eo_id = None
                    transaction.reconciliation_status = 'unmatched'
                    transaction.accounting_ref = None

            db.session.commit()
            return jsonify({'success': True, 'message': '匹配记录已删除'})

        # 方式2：通过 transaction_id + match_type + target_id 删除
        transaction_id = data.get('transaction_id')
        match_type = data.get('match_type')
        target_id = data.get('target_id')

        if not all([transaction_id, match_type, target_id]):
            return jsonify({'success': False, 'message': '参数不完整'})

        match_record = BankTransactionMatch.query.filter_by(
            transaction_id=transaction_id,
            match_type=match_type,
            match_id=target_id
        ).first()

        if not match_record:
            return jsonify({'success': False, 'message': '匹配记录不存在'})

        db.session.delete(match_record)

        # 检查是否还有其他匹配
        remaining = BankTransactionMatch.query.filter_by(transaction_id=transaction_id).count()
        if remaining == 0:
            transaction = BankTransaction.query.get(transaction_id)
            if transaction:
                transaction.matched_receipt_id = None
                transaction.eo_id = None
                transaction.reconciliation_status = 'unmatched'
                transaction.accounting_ref = None

        db.session.commit()
        return jsonify({'success': True, 'message': '匹配记录已删除'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"删除匹配记录失败: {str(e)}")
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})


@reconciliation_bp.route('/api/get-matches')
@login_required
@staff_only
def get_matches():
    """
    获取匹配记录

    参数：
    - transaction_id: 银行交易ID（可选）
    - match_type: 匹配类型 receipt/eo（可选）
    - match_id: 目标ID（可选）
    """
    try:
        transaction_id = request.args.get('transaction_id', type=int)
        match_type = request.args.get('match_type')
        match_id = request.args.get('match_id', type=int)

        query = BankTransactionMatch.query

        if transaction_id:
            query = query.filter_by(transaction_id=transaction_id)
        if match_type:
            query = query.filter_by(match_type=match_type)
        if match_id:
            query = query.filter_by(match_id=match_id)

        matches = query.order_by(BankTransactionMatch.created_at.desc()).all()

        result = []
        for m in matches:
            item = m.to_dict()

            # 获取银行交易信息
            if m.transaction:
                item['transaction_date'] = m.transaction.transaction_date.isoformat() if m.transaction.transaction_date else None
                item['transaction_amount'] = float(m.transaction.amount) if m.transaction.amount else 0
                item['counterparty'] = m.transaction.counterparty_name or m.transaction.description or ''

            # 获取目标信息
            if m.match_type == 'receipt':
                receipt = ProjectReceipt.query.get(m.match_id)
                if receipt:
                    item['target_number'] = receipt.receipt_number
                    item['target_amount'] = float(receipt.amount) if receipt.amount else 0
                    item['target_date'] = receipt.payment_date.isoformat() if receipt.payment_date else None
                    item['project_number'] = receipt.header.hid if receipt.header else ''
            else:
                eo = ProjectEO.query.get(m.match_id)
                if eo:
                    item['target_number'] = eo.eo_number
                    item['target_amount'] = float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else 0
                    item['target_date'] = (eo.paid_date or eo.eo_date).isoformat() if (eo.paid_date or eo.eo_date) else None
                    item['project_number'] = eo.ref.header.hid if eo.ref and eo.ref.header else ''

            result.append(item)

        return jsonify({
            'success': True,
            'matches': result,
            'total': len(result)
        })

    except Exception as e:
        logger.error(f"获取匹配记录失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})


@reconciliation_bp.route('/api/match-summary')
@login_required
@staff_only
def match_summary():
    """
    获取匹配汇总信息

    参数：
    - transaction_id: 银行交易ID
    或
    - match_type: 匹配类型
    - match_id: 目标ID
    """
    try:
        transaction_id = request.args.get('transaction_id', type=int)
        match_type = request.args.get('match_type')
        match_id = request.args.get('match_id', type=int)

        if transaction_id:
            # 获取银行交易的匹配汇总
            transaction = BankTransaction.query.get(transaction_id)
            if not transaction:
                return jsonify({'success': False, 'message': '银行交易不存在'})

            matched_amount = BankTransactionMatch.get_transaction_matched_amount(transaction_id)
            transaction_amount = float(transaction.amount) if transaction.amount else 0
            remaining = transaction_amount - matched_amount

            matches = BankTransactionMatch.query.filter_by(transaction_id=transaction_id).all()

            return jsonify({
                'success': True,
                'transaction_id': transaction_id,
                'transaction_amount': transaction_amount,
                'matched_amount': matched_amount,
                'remaining_amount': remaining,
                'is_fully_matched': abs(remaining) < 0.01,
                'match_count': len(matches)
            })

        elif match_type and match_id:
            # 获取收款/EO的匹配汇总
            if match_type == 'receipt':
                target = ProjectReceipt.query.get(match_id)
                if not target:
                    return jsonify({'success': False, 'message': '收款记录不存在'})
                target_amount = float(target.amount) if target.amount else 0
                matched_amount = BankTransactionMatch.get_receipt_matched_amount(match_id)
            else:
                target = ProjectEO.query.get(match_id)
                if not target:
                    return jsonify({'success': False, 'message': 'EO记录不存在'})
                target_amount = float(target.ref.cost_price) if target.ref and target.ref.cost_price else 0
                matched_amount = BankTransactionMatch.get_eo_matched_amount(match_id)

            remaining = target_amount - matched_amount
            matches = BankTransactionMatch.query.filter_by(match_type=match_type, match_id=match_id).all()

            return jsonify({
                'success': True,
                'match_type': match_type,
                'match_id': match_id,
                'target_amount': target_amount,
                'matched_amount': matched_amount,
                'remaining_amount': remaining,
                'is_fully_matched': abs(remaining) < 0.01,
                'match_count': len(matches)
            })

        else:
            return jsonify({'success': False, 'message': '请提供 transaction_id 或 match_type + match_id'})

    except Exception as e:
        logger.error(f"获取匹配汇总失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})
