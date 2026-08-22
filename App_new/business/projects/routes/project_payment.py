# -*- coding: utf-8 -*-
"""
供应商付款记录路由
管理批量付款记录的查看和管理
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.utils.decorators import staff_only, admin_only
from App_new.business.projects.models.supplier_payment import SupplierPayment
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.project import CustomerCompany
from datetime import datetime, date

project_payment = Blueprint('project_payment', __name__, url_prefix='/payment')


@project_payment.route('/')
@login_required
@staff_only
def list_payments():
    """付款记录列表页面"""
    from sqlalchemy import and_, or_, func
    from App_new.finance.models.bank_transaction_match import BankTransactionMatch
    from App_new.finance.models.statement import BankTransaction

    # 获取筛选参数
    supplier_id = request.args.get('supplier_id', type=int)
    status = request.args.get('status', '')
    payment_source = request.args.get('payment_source', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    keyword = request.args.get('keyword', '')
    match_status = request.args.get('match_status', '')  # 匹配状态筛选

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 构建查询
    query = SupplierPayment.query

    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)
    if status:
        query = query.filter_by(status=status)
    if payment_source:
        query = query.filter_by(payment_source=payment_source)
    if start_date:
        query = query.filter(SupplierPayment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(SupplierPayment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if keyword:
        query = query.filter(SupplierPayment.payment_no.ilike(f'%{keyword}%'))

    # 确认状态筛选
    if match_status:
        if match_status == 'reconciled':
            # 已核对
            query = query.filter(SupplierPayment.is_reconciled == True)
        elif match_status == 'unmatched':
            # 待确认
            query = query.filter(or_(
                SupplierPayment.is_reconciled == False,
                SupplierPayment.is_reconciled.is_(None)
            ))

    # 计算汇总：基于整个筛选集（所有页），不仅当前页
    summary_row = query.with_entities(
        func.coalesce(func.sum(SupplierPayment.total_amount), 0).label('total_amount'),
        func.coalesce(func.sum(SupplierPayment.prepayment_amount), 0).label('total_prepayment')
    ).order_by(None).first()
    total_amount = float(summary_row.total_amount or 0) if summary_row else 0
    total_prepayment = float(summary_row.total_prepayment or 0) if summary_row else 0

    # 排序并分页
    query = query.order_by(SupplierPayment.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    payment_records = pagination.items

    # 获取供应商列表（用于筛选）：只列真有付款记录的，
    # 否则一堆从没付过款的公司挤在下拉里，选中只会筛出 0 条。
    # 不按 status='active' 过滤——供应商停用后旧付款记录还得能筛。
    payer_ids = [r[0] for r in db.session.query(SupplierPayment.supplier_id).filter(
        SupplierPayment.supplier_id.isnot(None)
    ).distinct().all()]
    suppliers = CustomerCompany.query.filter(
        CustomerCompany.id.in_(payer_ids)
    ).order_by(CustomerCompany.company_name).all() if payer_ids else []

    # 批量获取匹配信息
    payment_ids = [p.id for p in payment_records]
    matched_info = {}
    if payment_ids:
        # 获取所有匹配记录
        matches = BankTransactionMatch.query.filter(
            BankTransactionMatch.match_type == 'payment',
            BankTransactionMatch.match_id.in_(payment_ids)
        ).all()

        # 按 payment_id 分组
        for match in matches:
            if match.match_id not in matched_info:
                matched_info[match.match_id] = []
            matched_info[match.match_id].append(match.transaction_id)

        # 获取相关银行交易详情
        tx_ids = [tx_id for tx_list in matched_info.values() for tx_id in tx_list]
        if tx_ids:
            transactions = BankTransaction.query.filter(BankTransaction.id.in_(tx_ids)).all()
            tx_dict = {tx.id: tx for tx in transactions}

            # 更新匹配信息为交易详情
            for payment_id, tx_id_list in matched_info.items():
                matched_info[payment_id] = [tx_dict.get(tx_id) for tx_id in tx_id_list if tx_dict.get(tx_id)]

    # 构建 payments 数据
    payments = []
    for p in payment_records:
        matched_txs = matched_info.get(p.id, [])
        is_matched = len(matched_txs) > 0

        # 构建匹配详情
        matched_tx_info = []
        for tx in matched_txs[:2]:  # 最多显示2条
            matched_tx_info.append({
                'date': tx.transaction_date.strftime('%m-%d') if tx.transaction_date else '',
                'amount': float(tx.amount) if tx.amount else 0,
                'counterparty': tx.counterparty_name or (tx.description[:15] if tx.description else '')
            })

        payments.append({
            'id': p.id,
            'payment_no': p.payment_no,
            'supplier': p.supplier,
            'payment_date': p.payment_date,
            'total_amount': p.total_amount,
            'currency': p.currency,
            'payment_source': p.payment_source,
            'payment_source_display': p.payment_source_display,
            'prepayment_amount': p.prepayment_amount,
            'eo_count': p.eo_count,
            'payment_voucher_no': p.payment_voucher_no,
            'status': p.status,
            'status_display': p.status_display,
            'is_reconciled': p.is_reconciled,
            'is_matched': is_matched,
            'matched_tx_count': len(matched_txs),
            'matched_tx_info': matched_tx_info
        })

    return render_template('business/projects/payment/list.html',
                           payments=payments,
                           pagination=pagination,
                           suppliers=suppliers,
                           total_amount=total_amount,
                           total_prepayment=total_prepayment,
                           current_filters={
                               'supplier_id': supplier_id,
                               'status': status,
                               'payment_source': payment_source,
                               'start_date': start_date,
                               'end_date': end_date,
                               'keyword': keyword,
                               'match_status': match_status
                           })


@project_payment.route('/<int:payment_id>')
@login_required
@staff_only
def payment_detail(payment_id):
    """付款记录详情"""
    payment = SupplierPayment.query.get_or_404(payment_id)

    # 获取关联的 EO 列表
    eos = ProjectEO.query.filter_by(payment_record_id=payment_id).order_by(ProjectEO.id).all()

    # 在路由中安全计算合计，避免模板对 None 求和导致 500
    total_cost = sum(float(eo.ref.cost_price) for eo in eos if eo.ref and eo.ref.cost_price)
    total_pay = sum(float(eo.pay_amount) for eo in eos if eo.pay_amount)

    return render_template('business/projects/payment/detail.html',
                           payment=payment,
                           eos=eos,
                           total_cost=total_cost,
                           total_pay=total_pay)


@project_payment.route('/<int:payment_id>/print')
@login_required
@staff_only
def print_voucher(payment_id):
    """打印 Payment Voucher"""
    payment = SupplierPayment.query.get_or_404(payment_id)

    # 获取关联的 EO 列表
    eos = ProjectEO.query.filter_by(payment_record_id=payment_id).order_by(ProjectEO.id).all()

    # 计算总成本
    total_cost = sum(float(eo.ref.cost_price or 0) for eo in eos if eo.ref)

    return render_template('business/projects/payment/print_voucher.html',
                           payment=payment,
                           eos=eos,
                           total_cost=total_cost)


@project_payment.route('/<int:payment_id>/cancel', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def cancel_payment(payment_id):
    """取消付款记录"""
    try:
        payment = SupplierPayment.query.get_or_404(payment_id)

        if payment.status == 'cancelled':
            return jsonify({'success': False, 'message': '该付款记录已取消'})

        # 获取关联的 EO 并恢复状态
        eos = ProjectEO.query.filter_by(payment_record_id=payment_id).all()

        for eo in eos:
            eo.payment_record_id = None
            eo.payment_no = None
            eo.payment_voucher_no = None
            eo.paid_date = None
            eo.pay_amount = None
            eo.payment_remarks = None
            eo.status = 'confirmed'

        # 如果使用了预付账款，恢复余额
        if payment.payment_source in ('prepayment', 'mixed') and payment.prepayment_amount > 0:
            from App_new.business.projects.models.supplier_prepayment import PrepaymentUsage, SupplierPrepayment

            # 查找并冲销相关的预付使用记录
            for eo in eos:
                usages = PrepaymentUsage.query.filter_by(
                    eo_id=eo.id,
                    status='confirmed'
                ).all()

                for usage in usages:
                    # 恢复预付余额
                    prepayment = SupplierPrepayment.query.get(usage.prepayment_id)
                    if prepayment:
                        prepayment.balance_amount += usage.amount
                        prepayment.update_status()

                    usage.status = 'reversed'
                    usage.description = f'付款取消冲销 ({payment.payment_no})'

        payment.status = 'cancelled'
        db.session.commit()

        return jsonify({'success': True, 'message': f'付款记录 {payment.payment_no} 已取消，{len(eos)} 个EO已恢复'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'取消失败：{str(e)}'})


@project_payment.route('/api/generate-no')
@login_required
@staff_only
def generate_payment_no():
    """生成付款编号 API"""
    payment_no = SupplierPayment.generate_payment_no()
    return jsonify({'success': True, 'payment_no': payment_no})


@project_payment.route('/api/summary')
@login_required
@staff_only
def get_payment_summary():
    """获取付款汇总（按供应商）"""
    from sqlalchemy import func

    # 按供应商汇总
    summary = db.session.query(
        CustomerCompany.id,
        CustomerCompany.company_name,
        func.count(SupplierPayment.id).label('payment_count'),
        func.sum(SupplierPayment.total_amount).label('total_amount'),
        func.sum(SupplierPayment.prepayment_amount).label('total_prepayment'),
        func.sum(SupplierPayment.eo_count).label('total_eo_count')
    ).join(
        SupplierPayment, CustomerCompany.id == SupplierPayment.supplier_id
    ).filter(
        SupplierPayment.status == 'confirmed'
    ).group_by(
        CustomerCompany.id, CustomerCompany.company_name
    ).all()

    result = []
    for item in summary:
        result.append({
            'supplier_id': item.id,
            'supplier_name': item.company_name,
            'payment_count': item.payment_count,
            'total_amount': float(item.total_amount or 0),
            'total_prepayment': float(item.total_prepayment or 0),
            'total_eo_count': item.total_eo_count or 0
        })

    return jsonify({'success': True, 'data': result})


@project_payment.route('/<int:payment_id>/reconcile', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def toggle_reconcile(payment_id):
    """标记/取消核对状态"""
    try:
        payment = SupplierPayment.query.get_or_404(payment_id)
        data = request.get_json() or {}
        reconcile = data.get('reconcile', True)

        payment.is_reconciled = reconcile
        if reconcile:
            payment.reconciled_at = datetime.utcnow()
            payment.reconciled_by = current_user.username if current_user else None
        else:
            payment.reconciled_at = None
            payment.reconciled_by = None

        db.session.commit()

        action = '已核对' if reconcile else '取消核对'
        return jsonify({'success': True, 'message': f'付款记录 {payment.payment_no} {action}'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@project_payment.route('/batch-reconcile', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def batch_reconcile():
    """批量确认（多选一键标记已核对）"""
    try:
        data = request.get_json() or {}
        raw_ids = data.get('payment_ids') or []

        # 去重并转成 int，忽略非法值
        payment_ids = []
        for pid in raw_ids:
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                continue
            if pid not in payment_ids:
                payment_ids.append(pid)

        if not payment_ids:
            return jsonify({'success': False, 'message': '请先勾选要确认的付款记录'})

        payments = SupplierPayment.query.filter(SupplierPayment.id.in_(payment_ids)).all()
        found_ids = {p.id for p in payments}

        confirmed_count = 0
        skipped = []  # 被跳过的记录及原因

        for payment in payments:
            if payment.is_reconciled:
                skipped.append(f'{payment.payment_no}（已核对）')
                continue
            # 已取消的付款不应再确认
            if payment.status == 'cancelled':
                skipped.append(f'{payment.payment_no}（已取消）')
                continue

            payment.is_reconciled = True
            payment.reconciled_at = datetime.utcnow()
            payment.reconciled_by = current_user.username if current_user else None
            confirmed_count += 1

        for pid in payment_ids:
            if pid not in found_ids:
                skipped.append(f'ID {pid}（记录不存在）')

        db.session.commit()

        message = f'已确认 {confirmed_count} 条付款记录'
        if skipped:
            message += f'，跳过 {len(skipped)} 条：' + '、'.join(skipped[:5])
            if len(skipped) > 5:
                message += f' 等 {len(skipped)} 条'

        return jsonify({
            'success': True,
            'message': message,
            'confirmed_count': confirmed_count,
            'skipped_count': len(skipped),
            'skipped': skipped
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@project_payment.route('/<int:payment_id>/unmatch', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def unmatch_payment(payment_id):
    """解除银行账单匹配"""
    try:
        from App_new.finance.models.bank_transaction_match import BankTransactionMatch

        payment = SupplierPayment.query.get_or_404(payment_id)

        # 删除所有匹配记录
        matches = BankTransactionMatch.query.filter_by(
            match_type='payment',
            match_id=payment_id
        ).all()

        for match in matches:
            db.session.delete(match)

        # 重置核对状态
        payment.is_reconciled = False
        payment.reconciled_at = None
        payment.reconciled_by = None

        db.session.commit()

        return jsonify({'success': True, 'message': f'付款记录 {payment.payment_no} 已解除匹配'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@project_payment.route('/<int:payment_id>/update-voucher', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def update_voucher(payment_id):
    """更新付款凭证号"""
    try:
        payment = SupplierPayment.query.get_or_404(payment_id)

        if payment.status != 'confirmed':
            return jsonify({'success': False, 'message': '只能编辑已确认的付款记录'})

        data = request.get_json() or {}
        voucher_no = data.get('voucher_no', '').strip()

        payment.payment_voucher_no = voucher_no if voucher_no else None
        payment.updated_at = datetime.utcnow()

        # 同时更新关联的EO的凭证号
        eos = ProjectEO.query.filter_by(payment_record_id=payment_id).all()
        for eo in eos:
            eo.payment_voucher_no = voucher_no if voucher_no else None

        db.session.commit()

        return jsonify({'success': True, 'message': '凭证号已更新'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
