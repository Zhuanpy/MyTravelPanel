# -*- coding: utf-8 -*-
"""
供应商预付账款路由
管理航司账户充值等预付款项
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.utils.decorators import staff_only, admin_only
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment, PrepaymentUsage
from App_new.business.projects.models.project import CustomerCompany
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.ref import ProjectRef
from App_new.finance.models.chart_of_account import ChartOfAccount
from App_new.finance.models.journal_entry import JournalEntry, JournalEntryLine
from datetime import datetime, date
from decimal import Decimal
import traceback

project_prepayment = Blueprint('project_prepayment', __name__, url_prefix='/prepayment')


@project_prepayment.route('/')
@login_required
@staff_only
def list_prepayments():
    """预付款记录列表页面（扁平化列表，支持筛选和分页）"""
    from sqlalchemy import func, or_

    # 获取筛选参数
    payment_method = request.args.get('payment_method', '')
    supplier_id = request.args.get('supplier_id', type=int)
    status = request.args.get('status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    keyword = request.args.get('keyword', '')
    reconcile_status = request.args.get('reconcile_status', '')

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 构建查询
    query = SupplierPrepayment.query

    if payment_method:
        query = query.filter_by(payment_method=payment_method)
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)
    if status:
        query = query.filter_by(status=status)
    if start_date:
        query = query.filter(SupplierPrepayment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(SupplierPrepayment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if keyword:
        query = query.filter(or_(
            SupplierPrepayment.prepayment_number.ilike(f'%{keyword}%'),
            SupplierPrepayment.reference.ilike(f'%{keyword}%')
        ))
    if reconcile_status:
        if reconcile_status == 'reconciled':
            query = query.filter(SupplierPrepayment.is_reconciled == True)
        elif reconcile_status == 'unreconciled':
            query = query.filter(or_(
                SupplierPrepayment.is_reconciled == False,
                SupplierPrepayment.is_reconciled.is_(None)
            ))

    # 排序并分页
    query = query.order_by(SupplierPrepayment.payment_date.desc(), SupplierPrepayment.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    prepayment_records = pagination.items

    # 计算已使用金额和可用余额
    for p in prepayment_records:
        p._cached_used_amount = float(p.amount) - float(p.balance_amount)
        p._cached_available_balance = float(p.balance_amount)

    # 批量查询银行对账匹配信息
    from App_new.finance.models.bank_transaction_match import BankTransactionMatch
    from App_new.finance.models.statement import BankTransaction
    prepayment_ids = [p.id for p in prepayment_records]
    match_info = {}
    if prepayment_ids:
        matches = db.session.query(
            BankTransactionMatch, BankTransaction
        ).join(
            BankTransaction, BankTransactionMatch.transaction_id == BankTransaction.id
        ).filter(
            BankTransactionMatch.match_type == 'prepayment',
            BankTransactionMatch.match_id.in_(prepayment_ids)
        ).all()
        for btm, tx in matches:
            match_info[btm.match_id] = {
                'tx_date': tx.transaction_date.strftime('%Y-%m-%d') if tx.transaction_date else '',
                'tx_amount': float(tx.amount or 0),
                'tx_counterparty': tx.counterparty_name or '',
                'tx_description': tx.description or '',
                'tx_bank': tx.statement.bank_name if tx.statement else '',
                'tx_account': tx.statement.account_name if tx.statement else '',
            }

    # 获取供应商列表（用于筛选）
    suppliers = CustomerCompany.query.filter(
        CustomerCompany.is_supplier == True,
        CustomerCompany.status == 'active'
    ).order_by(CustomerCompany.company_name).all()

    # 计算当前页汇总
    total_amount = sum(float(p.amount or 0) for p in prepayment_records)
    total_balance = sum(float(p.balance_amount or 0) for p in prepayment_records)
    total_used = total_amount - total_balance

    return render_template('business/projects/prepayment/list.html',
                           prepayments=prepayment_records,
                           pagination=pagination,
                           suppliers=suppliers,
                           total_amount=total_amount,
                           total_balance=total_balance,
                           total_used=total_used,
                           match_info=match_info,
                           current_filters={
                               'payment_method': payment_method,
                               'supplier_id': supplier_id,
                               'status': status,
                               'start_date': start_date,
                               'end_date': end_date,
                               'keyword': keyword,
                               'reconcile_status': reconcile_status
                           })


@project_prepayment.route('/create', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def create_prepayment():
    """创建预付账款"""
    if request.method == 'GET':
        # 获取供应商列表
        suppliers = CustomerCompany.query.filter(
            CustomerCompany.is_supplier == True,
            CustomerCompany.status == 'active'
        ).order_by(CustomerCompany.company_name).all()

        # 获取银行账户科目（1000-1099）
        bank_accounts = ChartOfAccount.query.filter(
            ChartOfAccount.code.between('1000', '1099'),
            ChartOfAccount.is_active == True
        ).order_by(ChartOfAccount.code).all()

        # 获取预付账款科目（1200-1299）
        prepayment_accounts = ChartOfAccount.query.filter(
            ChartOfAccount.code.between('1200', '1299'),
            ChartOfAccount.is_active == True
        ).order_by(ChartOfAccount.code).all()

        # 复制功能：从已有记录预填数据
        copy_data = None
        copy_from = request.args.get('copy_from', type=int)
        if copy_from:
            source = SupplierPrepayment.query.get(copy_from)
            if source:
                copy_data = {
                    'supplier_id': source.supplier_id,
                    'amount': float(source.amount),
                    'currency': source.currency,
                    'payment_method': source.payment_method,
                    'bank_account_id': source.bank_account_id,
                    'prepayment_account_id': source.prepayment_account_id,
                    'remarks': source.remarks or ''
                }

        return render_template('business/projects/prepayment/create.html',
                               suppliers=suppliers,
                               bank_accounts=bank_accounts,
                               prepayment_accounts=prepayment_accounts,
                               copy_data=copy_data)

    # POST 处理
    try:
        supplier_id = request.form.get('supplier_id', type=int)
        amount = request.form.get('amount', type=float)
        currency = request.form.get('currency', 'SGD')
        payment_date_str = request.form.get('payment_date')
        payment_method = request.form.get('payment_method', 'bank_transfer')
        bank_account_id = request.form.get('bank_account_id', type=int)
        prepayment_account_id = request.form.get('prepayment_account_id', type=int)
        remarks = request.form.get('remarks', '')
        reference = request.form.get('reference', '')

        # 验证
        if not supplier_id:
            flash('请选择供应商', 'error')
            return redirect(url_for('business_projects.project_prepayment.create_prepayment'))
        if not amount or amount <= 0:
            flash('请输入有效的充值金额', 'error')
            return redirect(url_for('business_projects.project_prepayment.create_prepayment'))

        # 解析日期
        payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else date.today()

        # 生成编号
        prepayment_number = SupplierPrepayment.generate_prepayment_number()

        # 创建预付记录
        prepayment = SupplierPrepayment(
            prepayment_number=prepayment_number,
            supplier_id=supplier_id,
            amount=Decimal(str(amount)),
            balance_amount=Decimal(str(amount)),  # 初始余额等于充值金额
            currency=currency,
            payment_date=payment_date,
            payment_method=payment_method,
            bank_account_id=bank_account_id if bank_account_id else None,
            prepayment_account_id=prepayment_account_id if prepayment_account_id else None,
            remarks=remarks,
            reference=reference,
            status='draft',
            created_by=current_user.username if current_user else None
        )

        db.session.add(prepayment)
        db.session.commit()

        flash('预付款创建成功', 'success')
        return redirect(url_for('business_projects.project_prepayment.list_prepayments'))

    except Exception as e:
        db.session.rollback()
        flash(f'创建失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.project_prepayment.create_prepayment'))


@project_prepayment.route('/<int:prepayment_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def edit_prepayment(prepayment_id):
    """编辑预付账款（仅草稿状态可编辑，已确认的单据只读）"""
    prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)

    detail_url = url_for('business_projects.project_prepayment.prepayment_detail',
                         prepayment_id=prepayment_id)

    # 确认后已生成会计分录、可被 EO 核销，一律不允许再改
    if prepayment.status != 'draft':
        flash(f'只有草稿状态的预付账款可以编辑（当前状态：{prepayment.status_display}）', 'error')
        return redirect(detail_url)

    if request.method == 'GET':
        # 获取供应商列表
        suppliers = CustomerCompany.query.filter(
            CustomerCompany.is_supplier == True,
            CustomerCompany.status == 'active'
        ).order_by(CustomerCompany.company_name).all()

        # 获取银行账户科目（1000-1099）
        bank_accounts = ChartOfAccount.query.filter(
            ChartOfAccount.code.between('1000', '1099'),
            ChartOfAccount.is_active == True
        ).order_by(ChartOfAccount.code).all()

        # 获取预付账款科目（1200-1299）
        prepayment_accounts = ChartOfAccount.query.filter(
            ChartOfAccount.code.between('1200', '1299'),
            ChartOfAccount.is_active == True
        ).order_by(ChartOfAccount.code).all()

        return render_template('business/projects/prepayment/edit.html',
                               prepayment=prepayment,
                               suppliers=suppliers,
                               bank_accounts=bank_accounts,
                               prepayment_accounts=prepayment_accounts)

    # POST 处理
    edit_url = url_for('business_projects.project_prepayment.edit_prepayment',
                       prepayment_id=prepayment_id)
    try:
        supplier_id = request.form.get('supplier_id', type=int)
        amount = request.form.get('amount', type=float)
        currency = request.form.get('currency', 'SGD')
        payment_date_str = request.form.get('payment_date')
        payment_method = request.form.get('payment_method', 'bank_transfer')
        bank_account_id = request.form.get('bank_account_id', type=int)
        prepayment_account_id = request.form.get('prepayment_account_id', type=int)
        remarks = request.form.get('remarks', '')
        reference = request.form.get('reference', '')

        # 验证
        if not supplier_id:
            flash('请选择供应商', 'error')
            return redirect(edit_url)
        if not amount or amount <= 0:
            flash('请输入有效的充值金额', 'error')
            return redirect(edit_url)

        # 草稿理论上不会有使用记录，兜底防止改金额把余额算错
        if prepayment.used_amount > 0:
            flash('该预付账款已有使用记录，无法编辑', 'error')
            return redirect(detail_url)

        # 解析日期
        payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else prepayment.payment_date

        prepayment.supplier_id = supplier_id
        prepayment.amount = Decimal(str(amount))
        prepayment.balance_amount = Decimal(str(amount))  # 草稿未使用，余额跟随充值金额
        prepayment.currency = currency
        prepayment.payment_date = payment_date
        prepayment.payment_method = payment_method
        prepayment.bank_account_id = bank_account_id if bank_account_id else None
        prepayment.prepayment_account_id = prepayment_account_id if prepayment_account_id else None
        prepayment.remarks = remarks
        prepayment.reference = reference

        db.session.commit()

        flash('预付款修改成功', 'success')
        return redirect(detail_url)

    except Exception as e:
        db.session.rollback()
        flash(f'修改失败：{str(e)}', 'error')
        return redirect(edit_url)


@project_prepayment.route('/<int:prepayment_id>')
@login_required
@staff_only
def prepayment_detail(prepayment_id):
    """预付账款详情"""
    prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)

    # 获取使用记录
    usages = PrepaymentUsage.query.filter_by(prepayment_id=prepayment_id).order_by(
        PrepaymentUsage.usage_date.desc()
    ).all()

    # 获取供应商邮箱
    supplier_email = ''
    if prepayment.supplier and prepayment.supplier.contact_email:
        email = prepayment.supplier.contact_email.strip()
        # 排除特殊值
        if email.lower() not in ['n/a', 'none', '无', 'na', 'null', '']:
            supplier_email = email

    return render_template('business/projects/prepayment/detail.html',
                           prepayment=prepayment,
                           usages=usages,
                           supplier_email=supplier_email)


@project_prepayment.route('/<int:prepayment_id>/confirm', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def confirm_prepayment(prepayment_id):
    """确认预付账款（生成日记账分录）"""
    try:
        prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)

        if prepayment.status != 'draft':
            return jsonify({'success': False, 'message': '只有草稿状态的预付账款可以确认'})

        # 生成日记账分录
        # 借：预付账款(1200) 贷：银行存款(1002)
        if prepayment.prepayment_account_id and prepayment.bank_account_id:
            entry_number = JournalEntry._generate_entry_number()

            journal_entry = JournalEntry(
                entry_number=entry_number,
                entry_date=prepayment.payment_date,
                source_type='manual',  # 使用manual类型
                source_id=prepayment.id,
                source_number=prepayment.prepayment_number,
                description=f'预付账款充值 - {prepayment.supplier.name if prepayment.supplier else ""}',
                total_amount=prepayment.amount,
                status='posted',
                posted_at=datetime.utcnow(),
                posted_by=current_user.username if current_user else None,
                created_by=current_user.username if current_user else None
            )
            db.session.add(journal_entry)
            db.session.flush()

            # 借方：预付账款
            debit_line = JournalEntryLine(
                entry_id=journal_entry.id,
                line_no=1,
                account_id=prepayment.prepayment_account_id,
                debit=prepayment.amount,
                credit=Decimal('0'),
                memo=f'预付充值 {prepayment.prepayment_number}'
            )
            db.session.add(debit_line)

            # 贷方：银行存款
            credit_line = JournalEntryLine(
                entry_id=journal_entry.id,
                line_no=2,
                account_id=prepayment.bank_account_id,
                debit=Decimal('0'),
                credit=prepayment.amount,
                memo=f'预付充值 {prepayment.prepayment_number}'
            )
            db.session.add(credit_line)

            prepayment.journal_entry_id = journal_entry.id

        # 更新状态
        prepayment.status = 'confirmed'
        db.session.commit()

        return jsonify({'success': True, 'message': '预付账款已确认'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'确认失败：{str(e)}'})


@project_prepayment.route('/<int:prepayment_id>/reconcile', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def toggle_reconcile(prepayment_id):
    """标记/取消核对状态"""
    try:
        prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)
        data = request.get_json() or {}
        reconcile = data.get('reconcile', True)

        if reconcile:
            prepayment.is_reconciled = True
            prepayment.reconciled_at = datetime.utcnow()
            prepayment.reconciled_by = current_user.username if current_user else None
            msg = '已标记为核对'
        else:
            prepayment.is_reconciled = False
            prepayment.reconciled_at = None
            prepayment.reconciled_by = None
            msg = '已取消核对'

        db.session.commit()
        return jsonify({'success': True, 'message': msg})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败：{str(e)}'})


@project_prepayment.route('/<int:prepayment_id>/unmatch', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def unmatch_prepayment(prepayment_id):
    """解除预付款的银行匹配"""
    try:
        from App_new.finance.models.bank_transaction_match import BankTransactionMatch
        from App_new.finance.models.statement import BankTransaction

        prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)

        # 查找并删除匹配记录
        matches = BankTransactionMatch.query.filter_by(
            match_type='prepayment',
            match_id=prepayment_id
        ).all()

        if not matches:
            return jsonify({'success': False, 'message': '未找到匹配记录'})

        for match in matches:
            # 恢复银行交易状态
            tx = BankTransaction.query.get(match.transaction_id)
            if tx:
                tx.is_confirmed = False
                tx.confirmed_at = None
                tx.confirmed_by = None
                tx.reconciliation_status = 'unmatched'
                tx.accounting_ref = None
                tx.updated_at = datetime.utcnow()
            db.session.delete(match)

        # 恢复预付款核对状态
        prepayment.is_reconciled = False
        prepayment.reconciled_at = None
        prepayment.reconciled_by = None

        db.session.commit()
        return jsonify({'success': True, 'message': f'已解除 {len(matches)} 条银行匹配'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'解除失败：{str(e)}'})


@project_prepayment.route('/<int:prepayment_id>/cancel', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def cancel_prepayment(prepayment_id):
    """取消预付账款"""
    try:
        prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)

        if prepayment.status not in ('draft', 'confirmed'):
            return jsonify({'success': False, 'message': '只有草稿或已确认状态的预付账款可以取消'})

        if prepayment.used_amount > 0:
            return jsonify({'success': False, 'message': '已有使用记录，无法取消'})

        prepayment.status = 'cancelled'
        db.session.commit()

        return jsonify({'success': True, 'message': '预付账款已取消'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'取消失败：{str(e)}'})


@project_prepayment.route('/<int:prepayment_id>/delete', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_prepayment(prepayment_id):
    """删除预付账款（仅管理员）"""
    try:
        prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)

        if prepayment.status not in ('draft', 'cancelled'):
            return jsonify({'success': False, 'message': '只有草稿或已取消状态的预付账款可以删除'})

        # 删除使用记录
        PrepaymentUsage.query.filter_by(prepayment_id=prepayment_id).delete()

        db.session.delete(prepayment)
        db.session.commit()

        return jsonify({'success': True, 'message': '预付账款已删除'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'})


@project_prepayment.route('/use', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def use_prepayment():
    """使用预付账款（扣减余额）"""
    try:
        data = request.get_json() or request.form

        prepayment_id = data.get('prepayment_id', type=int) if hasattr(data, 'get') else int(data.get('prepayment_id', 0))
        amount = float(data.get('amount', 0))
        usage_date_str = data.get('usage_date')
        description = data.get('description', '')
        eo_id = data.get('eo_id', type=int) if hasattr(data, 'get') else data.get('eo_id')
        ref_id = data.get('ref_id', type=int) if hasattr(data, 'get') else data.get('ref_id')

        if not prepayment_id:
            return jsonify({'success': False, 'message': '请选择预付账款'})
        if not amount or amount <= 0:
            return jsonify({'success': False, 'message': '请输入有效的使用金额'})

        prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)

        if prepayment.status not in ('confirmed', 'partial_used'):
            return jsonify({'success': False, 'message': '该预付账款状态不允许使用'})

        if Decimal(str(amount)) > prepayment.balance_amount:
            return jsonify({'success': False, 'message': f'使用金额超过可用余额 {prepayment.balance_amount}'})

        # 解析日期
        usage_date = datetime.strptime(usage_date_str, '%Y-%m-%d').date() if usage_date_str else date.today()

        # 创建使用记录
        usage = PrepaymentUsage(
            prepayment_id=prepayment_id,
            amount=Decimal(str(amount)),
            usage_date=usage_date,
            description=description,
            eo_id=int(eo_id) if eo_id else None,
            ref_id=int(ref_id) if ref_id else None,
            status='confirmed',
            created_by=current_user.username if current_user else None
        )
        db.session.add(usage)

        # 扣减预付余额
        prepayment.balance_amount -= Decimal(str(amount))
        prepayment.update_status()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功使用 {amount} {prepayment.currency}',
            'balance_amount': float(prepayment.balance_amount)
        })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'使用失败：{str(e)}'})


@project_prepayment.route('/api/supplier/<int:supplier_id>/prepayments')
@login_required
@staff_only
def get_supplier_prepayments(supplier_id):
    """获取供应商的可用预付账款（API）"""
    from sqlalchemy import func

    # 用 balance_amount > 0 过滤，不依赖 status，
    # 防止历史脏数据（status='consumed' 但余额恢复后 > 0）导致漏算
    prepayments = SupplierPrepayment.query.filter(
        SupplierPrepayment.supplier_id == supplier_id,
        SupplierPrepayment.balance_amount > 0,
        SupplierPrepayment.status != 'cancelled',
        SupplierPrepayment.status != 'draft'
    ).order_by(SupplierPrepayment.payment_date.asc()).all()

    # 批量查询 confirmed 使用金额
    prepayment_ids = [p.id for p in prepayments]
    confirmed_usage_sums = {}
    if prepayment_ids:
        usage_query = db.session.query(
            PrepaymentUsage.prepayment_id,
            func.sum(PrepaymentUsage.amount).label('total')
        ).filter(
            PrepaymentUsage.prepayment_id.in_(prepayment_ids),
            PrepaymentUsage.status == 'confirmed'
        ).group_by(PrepaymentUsage.prepayment_id).all()
        confirmed_usage_sums = {row.prepayment_id: float(row.total or 0) for row in usage_query}

    # 计算可用余额（充值金额 - confirmed 使用）
    total_available = 0
    result_data = []
    for p in prepayments:
        used = confirmed_usage_sums.get(p.id, 0)
        available = float(p.amount) - used
        if available > 0:
            p_dict = p.to_dict()
            p_dict['available_balance'] = available
            result_data.append(p_dict)
            total_available += available

    return jsonify({
        'success': True,
        'data': result_data,
        'total_balance': total_available
    })


@project_prepayment.route('/api/summary')
@login_required
@staff_only
def get_prepayment_summary():
    """获取预付账款汇总（按供应商）"""
    from sqlalchemy import func

    # 按供应商汇总
    summary = db.session.query(
        CustomerCompany.id,
        CustomerCompany.company_name,
        func.sum(SupplierPrepayment.amount).label('total_amount'),
        func.sum(SupplierPrepayment.balance_amount).label('total_balance')
    ).join(
        SupplierPrepayment, CustomerCompany.id == SupplierPrepayment.supplier_id
    ).filter(
        SupplierPrepayment.status.in_(['confirmed', 'partial_used', 'consumed'])
    ).group_by(
        CustomerCompany.id, CustomerCompany.company_name
    ).all()

    result = []
    for item in summary:
        total_amount = float(item.total_amount or 0)
        total_balance = float(item.total_balance or 0)
        result.append({
            'supplier_id': item.id,
            'supplier_name': item.company_name,
            'total_amount': total_amount,
            'total_balance': total_balance,
            'total_used': total_amount - total_balance
        })

    return jsonify({'success': True, 'data': result})


# ========== 邮件通知 ==========

@project_prepayment.route('/email/templates')
@login_required
@staff_only
def get_prepayment_email_templates():
    """获取可用的邮件模板列表（供发送邮件弹窗选择）"""
    try:
        from App_new.business.projects.models.project import EmailTemplate
        templates = EmailTemplate.query.filter_by(is_active=True).order_by(
            EmailTemplate.category, EmailTemplate.name
        ).all()
        return jsonify({
            'success': True,
            'templates': [t.to_dict() for t in templates]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@project_prepayment.route('/<int:prepayment_id>/email/send', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def send_prepayment_email(prepayment_id):
    """发送预付款邮件通知"""
    try:
        from flask import current_app
        from flask_mail import Mail, Message
        import logging

        logger = logging.getLogger(__name__)
        prepayment = SupplierPrepayment.query.get_or_404(prepayment_id)

        # 支持 multipart/form-data（带附件）与 JSON（无附件）两种提交
        attachments = []
        if request.content_type and 'multipart/form-data' in request.content_type:
            recipients_str = (request.form.get('recipient') or '').strip()
            cc_str = (request.form.get('cc') or '').strip()
            subject = (request.form.get('subject') or '').strip()
            body = (request.form.get('body') or '').strip()
            attachments = [f for f in request.files.getlist('attachments') if f and f.filename]
        else:
            data = request.get_json() or {}
            recipients_str = data.get('recipient', '').strip()
            cc_str = data.get('cc', '').strip()
            subject = data.get('subject', '').strip()
            body = data.get('body', '').strip()

        if not recipients_str:
            return jsonify({'success': False, 'message': '请填写收件人邮箱'}), 400
        if not subject:
            return jsonify({'success': False, 'message': '请填写邮件主题'}), 400
        if not body:
            return jsonify({'success': False, 'message': '请填写邮件内容'}), 400

        # 解析收件人（支持逗号/分号分隔多个邮箱）
        import re
        recipients = [e.strip() for e in re.split(r'[,;，；]', recipients_str) if e.strip()]
        cc = [e.strip() for e in re.split(r'[,;，；]', cc_str) if e.strip()] if cc_str else []

        # 检查邮件配置
        mail_server = current_app.config.get('MAIL_SERVER')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')

        if not mail_server or not mail_username or not mail_password:
            return jsonify({'success': False, 'message': '邮件服务器未配置，请联系管理员'}), 500

        # 发送邮件
        mail = Mail(current_app)
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or mail_username

        # 正文：富文本编辑器已是 HTML 则直接用，纯文本则转义并换行
        has_html_tags = '<' in body and '>' in body and any(
            tag in body.lower() for tag in ['<br', '<p', '<div', '<span', '<h', '<strong', '<em', '<u', '<ol', '<ul', '<a', '<b>', '<i>']
        )
        if has_html_tags:
            html_body = body
        else:
            import html as html_module
            escaped_body = html_module.escape(body)
            html_body = escaped_body.replace('\n', '<br>')
            html_body = f'<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">{html_body}</div>'

        msg = Message(
            subject=subject,
            sender=sender_email,
            recipients=recipients,
            cc=cc if cc else None,
            html=html_body
        )

        # 添加附件
        import mimetypes
        for f in attachments:
            mime_type, _ = mimetypes.guess_type(f.filename)
            msg.attach(f.filename, mime_type or 'application/octet-stream', f.read())

        logger.info(f"预付款邮件发送 - 编号: {prepayment.prepayment_number}, 收件人: {recipients}, 附件: {len(attachments)}")
        mail.send(msg)
        logger.info("预付款邮件发送成功")

        return jsonify({
            'success': True,
            'message': f'邮件已发送至 {", ".join(recipients)}'
                       + (f'（含 {len(attachments)} 个附件）' if attachments else '')
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"预付款邮件发送失败: {str(e)}")
        return jsonify({'success': False, 'message': f'发送失败: {str(e)}'}), 500
