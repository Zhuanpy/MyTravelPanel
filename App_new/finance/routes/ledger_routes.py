# -*- coding: utf-8 -*-
"""
总账与会计科目管理路由
提供科目表管理、日记账分录、财务报表等功能
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from App_new.exts import csrf, db
from App_new.utils.decorators import staff_only
from App_new.finance.models.chart_of_account import ChartOfAccount
from App_new.finance.models.journal_entry import JournalEntry, JournalEntryLine
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
ledger_blue = Blueprint('ledger_routes', __name__)


# ==================== Ledger 首页 ====================

@ledger_blue.route('/')
@ledger_blue.route('/home')
@login_required
@staff_only
def ledger_home():
    """Ledger 首页/仪表板"""
    from App_new.business.projects.models.invoice import ProjectInvoice
    from App_new.business.projects.models.receipt import ProjectReceipt
    from App_new.business.projects.models.eo import ProjectEO

    # 统计数据
    stats = {
        # 会计科目
        'account_count': ChartOfAccount.query.filter_by(is_active=True).count(),
        'account_asset': ChartOfAccount.query.filter_by(is_active=True, account_type='asset').count(),
        'account_liability': ChartOfAccount.query.filter_by(is_active=True, account_type='liability').count(),
        'account_income': ChartOfAccount.query.filter_by(is_active=True, account_type='income').count(),
        'account_expense': ChartOfAccount.query.filter_by(is_active=True, account_type='expense').count(),

        # 日记账
        'journal_total': JournalEntry.query.count(),
        'journal_posted': JournalEntry.query.filter_by(status='posted').count(),
        'journal_draft': JournalEntry.query.filter_by(status='draft').count(),

        # 按来源统计
        'journal_invoice': JournalEntry.query.filter_by(source_type='invoice', status='posted').count(),
        'journal_receipt': JournalEntry.query.filter_by(source_type='receipt', status='posted').count(),
        'journal_eo': JournalEntry.query.filter_by(source_type='eo', status='posted').count(),
        'journal_manual': JournalEntry.query.filter_by(source_type='manual', status='posted').count(),

        # 业务数据（待生成日记账）- 已确认的发票都应生成日记账
        'invoice_pending': ProjectInvoice.query.filter_by(status='confirmed').count(),
        'receipt_pending': ProjectReceipt.query.filter_by(status='confirmed').count(),
        'eo_pending': ProjectEO.query.filter_by(status='paid').count(),
    }

    # 计算已生成日记账的数量
    stats['invoice_with_journal'] = JournalEntry.query.filter_by(source_type='invoice').count()
    stats['receipt_with_journal'] = JournalEntry.query.filter_by(source_type='receipt').count()
    stats['eo_with_journal'] = JournalEntry.query.filter_by(source_type='eo').count()

    # 最近的日记账
    recent_entries = JournalEntry.query.filter_by(status='posted').order_by(
        JournalEntry.entry_date.desc(), JournalEntry.id.desc()
    ).limit(10).all()

    # 计算总借贷
    total_debit = db.session.query(func.sum(JournalEntry.total_amount)).filter_by(status='posted').scalar() or 0

    return render_template('finance/ledger/home.html',
                           stats=stats,
                           recent_entries=recent_entries,
                           total_debit=total_debit)


# ==================== 会计科目表 ====================

@ledger_blue.route('/chart-of-accounts')
@login_required
@staff_only
def chart_of_accounts():
    """会计科目表列表"""
    account_type = request.args.get('type', '').strip()

    query = ChartOfAccount.query.filter_by(is_active=True)
    if account_type:
        query = query.filter_by(account_type=account_type)

    accounts = query.order_by(ChartOfAccount.code).all()

    # 获取科目类型统计
    type_stats = db.session.query(
        ChartOfAccount.account_type,
        func.count(ChartOfAccount.id)
    ).filter_by(is_active=True).group_by(ChartOfAccount.account_type).all()

    return render_template('finance/ledger/chart_of_accounts.html',
                           accounts=accounts,
                           type_stats=dict(type_stats),
                           current_type=account_type)


@ledger_blue.route('/chart-of-accounts/tree')
@login_required
@staff_only
def chart_of_accounts_tree():
    """获取科目表树结构（JSON）"""
    try:
        tree = ChartOfAccount.get_tree()
        return jsonify({'success': True, 'data': tree})
    except Exception as e:
        logger.error(f"获取科目树失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ledger_blue.route('/chart-of-accounts/add', methods=['GET', 'POST'])
@login_required
@staff_only
def chart_of_accounts_add():
    """添加会计科目"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form

            account = ChartOfAccount(
                code=data.get('code', '').strip(),
                name=data.get('name', '').strip(),
                name_cn=data.get('name_cn', '').strip() or None,
                account_type=data.get('account_type'),
                parent_id=int(data.get('parent_id')) if data.get('parent_id') else None,
                level=int(data.get('level', 1)),
                balance_direction=data.get('balance_direction'),
                currency=data.get('currency', 'SGD'),
                description=data.get('description', '').strip() or None,
                is_system=False,
                allow_manual_entry=data.get('allow_manual_entry', '1') in ['1', 'true', 'True', 'on', True]
            )

            db.session.add(account)
            db.session.commit()

            if request.is_json:
                return jsonify({'success': True, 'message': 'Account added successfully', 'data': account.to_dict()})
            flash('Account added successfully', 'success')
            return redirect(url_for('ledger_routes.chart_of_accounts'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"添加科目失败: {str(e)}")
            if request.is_json:
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Failed: {str(e)}', 'error')

    # 获取可选父级科目
    parent_accounts = ChartOfAccount.query.filter_by(is_active=True).order_by(ChartOfAccount.code).all()

    return render_template('finance/ledger/account_form.html',
                           form_title="Add Account",
                           parent_accounts=parent_accounts)


@ledger_blue.route('/chart-of-accounts/edit/<int:account_id>', methods=['GET', 'POST'])
@login_required
@staff_only
def chart_of_accounts_edit(account_id):
    """编辑会计科目"""
    account = ChartOfAccount.query.get_or_404(account_id)

    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form

            # 系统预设科目只能修改部分字段
            if not account.is_system:
                account.code = data.get('code', '').strip()
                account.account_type = data.get('account_type')
                account.balance_direction = data.get('balance_direction')

            account.name = data.get('name', '').strip()
            account.name_cn = data.get('name_cn', '').strip() or None
            account.parent_id = int(data.get('parent_id')) if data.get('parent_id') else None
            account.level = int(data.get('level', 1))
            account.currency = data.get('currency', 'SGD')
            account.description = data.get('description', '').strip() or None
            account.allow_manual_entry = data.get('allow_manual_entry', '1') in ['1', 'true', 'True', 'on', True]

            db.session.commit()

            if request.is_json:
                return jsonify({'success': True, 'message': 'Account updated successfully'})
            flash('Account updated successfully', 'success')
            return redirect(url_for('ledger_routes.chart_of_accounts'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"更新科目失败: {str(e)}")
            if request.is_json:
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Failed: {str(e)}', 'error')

    parent_accounts = ChartOfAccount.query.filter(
        ChartOfAccount.id != account_id,
        ChartOfAccount.is_active == True
    ).order_by(ChartOfAccount.code).all()

    return render_template('finance/ledger/account_form.html',
                           form_title="Edit Account",
                           account=account,
                           parent_accounts=parent_accounts)


@ledger_blue.route('/chart-of-accounts/delete/<int:account_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def chart_of_accounts_delete(account_id):
    """删除会计科目（软删除）"""
    try:
        account = ChartOfAccount.query.get_or_404(account_id)

        # 系统预设科目不能删除
        if account.is_system:
            return jsonify({'success': False, 'message': 'System accounts cannot be deleted'})

        # 检查是否有子科目
        if account.children:
            return jsonify({'success': False, 'message': 'Cannot delete account with sub-accounts'})

        # 检查是否有分录使用此科目
        if account.journal_lines.count() > 0:
            return jsonify({'success': False, 'message': 'Cannot delete account with journal entries'})

        account.is_active = False
        db.session.commit()

        return jsonify({'success': True, 'message': 'Account deleted successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"删除科目失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ledger_blue.route('/chart-of-accounts/init', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def chart_of_accounts_init():
    """初始化默认科目表"""
    try:
        ChartOfAccount.init_default_accounts()
        return jsonify({'success': True, 'message': 'Default accounts initialized successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"初始化科目表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ledger_blue.route('/generate-from-business', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def generate_journal_from_business():
    """从现有业务数据生成日记账分录"""
    try:
        from App_new.business.projects.models.invoice import ProjectInvoice
        from App_new.business.projects.models.receipt import ProjectReceipt
        from App_new.business.projects.models.eo import ProjectEO

        # 确保科目已初始化
        if ChartOfAccount.query.count() == 0:
            ChartOfAccount.init_default_accounts()

        invoice_created = 0
        receipt_created = 0
        eo_created = 0
        skipped = 0

        # 处理已确认的 Invoice（排除 cancelled）
        invoices = ProjectInvoice.query.filter_by(status='confirmed').all()
        for invoice in invoices:
            existing = JournalEntry.query.filter_by(source_type='invoice', source_id=invoice.id).first()
            if existing:
                skipped += 1
                continue
            try:
                entry = JournalEntry.create_from_invoice(invoice, user=current_user.username)
                if entry and entry.lines:
                    db.session.add(entry)
                    db.session.flush()
                    entry.post(user=current_user.username)
                    invoice_created += 1
            except Exception as e:
                logger.warning(f"Invoice {invoice.invoice_number} 生成日记账失败: {str(e)}")

        # 处理已确认的 Receipt
        receipts = ProjectReceipt.query.filter_by(status='confirmed').all()
        for receipt in receipts:
            existing = JournalEntry.query.filter_by(source_type='receipt', source_id=receipt.id).first()
            if existing:
                skipped += 1
                continue
            try:
                entry = JournalEntry.create_from_receipt(receipt, user=current_user.username)
                if entry and entry.lines:
                    db.session.add(entry)
                    db.session.flush()
                    entry.post(user=current_user.username)
                    receipt_created += 1
            except Exception as e:
                logger.warning(f"Receipt {receipt.receipt_number} 生成日记账失败: {str(e)}")

        # 处理已付款的 EO
        eos = ProjectEO.query.filter_by(status='paid').all()
        for eo in eos:
            existing = JournalEntry.query.filter_by(source_type='eo', source_id=eo.id).first()
            if existing:
                skipped += 1
                continue
            try:
                entry = JournalEntry.create_from_eo(eo, user=current_user.username)
                if entry and entry.lines:
                    db.session.add(entry)
                    db.session.flush()
                    entry.post(user=current_user.username)
                    eo_created += 1
            except Exception as e:
                logger.warning(f"EO {eo.eo_number} 生成日记账失败: {str(e)}")

        db.session.commit()

        total_created = invoice_created + receipt_created + eo_created
        message = f'Generated {total_created} journal entries (Invoice: {invoice_created}, Receipt: {receipt_created}, EO: {eo_created}, Skipped: {skipped})'

        return jsonify({'success': True, 'message': message})

    except Exception as e:
        db.session.rollback()
        logger.error(f"生成日记账失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ledger_blue.route('/migrate-invoice-status', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def migrate_invoice_status():
    """迁移旧发票状态到新格式（用于数据迁移）"""
    try:
        from App_new.business.projects.models.invoice import ProjectInvoice
        from sqlalchemy import text

        # 确保科目已初始化
        if ChartOfAccount.query.count() == 0:
            ChartOfAccount.init_default_accounts()

        # 使用原生SQL处理旧状态值
        updated_count = 0
        journal_created = 0

        # 查找需要迁移的发票（旧状态值）
        # 由于ORM可能无法查询旧的枚举值，使用原生SQL
        try:
            result = db.session.execute(text(
                "SELECT id, status FROM project_invoices WHERE status IN ('draft', 'sent', 'paid', 'partial_paid', 'overdue')"
            ))
            old_invoices = result.fetchall()

            for row in old_invoices:
                invoice_id, old_status = row[0], row[1]
                # 根据旧状态设置新状态
                if old_status in ['draft', 'sent', 'overdue']:
                    new_status = 'confirmed'
                    payment_status = 'unpaid'
                elif old_status == 'partial_paid':
                    new_status = 'confirmed'
                    payment_status = 'partial_paid'
                elif old_status == 'paid':
                    new_status = 'confirmed'
                    payment_status = 'paid'
                else:
                    continue

                db.session.execute(text(
                    "UPDATE project_invoices SET status = :new_status, payment_status = :payment_status WHERE id = :id"
                ), {'new_status': new_status, 'payment_status': payment_status, 'id': invoice_id})
                updated_count += 1

            db.session.commit()
        except Exception as e:
            logger.warning(f"迁移状态时出错: {str(e)}")

        # 为已确认的发票生成日记账
        invoices = ProjectInvoice.query.filter_by(status='confirmed').all()
        for invoice in invoices:
            existing = JournalEntry.query.filter_by(source_type='invoice', source_id=invoice.id).first()
            if not existing:
                try:
                    entry = JournalEntry.create_from_invoice(invoice, user=current_user.username)
                    if entry and entry.lines:
                        db.session.add(entry)
                        db.session.flush()
                        entry.post(user=current_user.username)
                        journal_created += 1
                except Exception as je:
                    logger.warning(f"Invoice {invoice.invoice_number} 日记账生成失败: {str(je)}")

        db.session.commit()

        message = f'已迁移 {updated_count} 张发票状态，生成 {journal_created} 条日记账'
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        db.session.rollback()
        logger.error(f"迁移发票状态失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ==================== 日记账分录 ====================

@ledger_blue.route('/journal-entries')
@login_required
@staff_only
def journal_entries():
    """日记账分录列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    source_type = request.args.get('source_type', '').strip()
    status = request.args.get('status', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    query = JournalEntry.query

    if source_type:
        query = query.filter_by(source_type=source_type)
    if status:
        query = query.filter_by(status=status)
    if start_date:
        query = query.filter(JournalEntry.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(JournalEntry.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    pagination = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    entries = pagination.items

    return render_template('finance/ledger/journal_entries.html',
                           entries=entries,
                           pagination=pagination,
                           current_source_type=source_type,
                           current_status=status,
                           start_date=start_date,
                           end_date=end_date)


@ledger_blue.route('/journal-entries/<int:entry_id>')
@login_required
@staff_only
def journal_entry_detail(entry_id):
    """日记账分录详情"""
    entry = JournalEntry.query.get_or_404(entry_id)
    return render_template('finance/ledger/journal_entry_detail.html', entry=entry)


@ledger_blue.route('/journal-entries/add', methods=['GET', 'POST'])
@login_required
@staff_only
def journal_entry_add():
    """添加手工分录"""
    if request.method == 'POST':
        try:
            data = request.get_json()

            entry = JournalEntry(
                entry_number=JournalEntry._generate_entry_number(),
                entry_date=datetime.strptime(data.get('entry_date'), '%Y-%m-%d').date(),
                source_type='manual',
                description=data.get('description', '').strip(),
                currency=data.get('currency', 'SGD'),
                remarks=data.get('remarks', '').strip() or None,
                created_by=current_user.username if current_user else None
            )

            # 添加分录行
            lines_data = data.get('lines', [])
            for i, line_data in enumerate(lines_data, 1):
                line = JournalEntryLine(
                    line_no=i,
                    account_id=int(line_data.get('account_id')),
                    debit=Decimal(str(line_data.get('debit', 0))) if line_data.get('debit') else Decimal('0'),
                    credit=Decimal(str(line_data.get('credit', 0))) if line_data.get('credit') else Decimal('0'),
                    memo=line_data.get('memo', '').strip() or None
                )
                entry.lines.append(line)

            # 验证借贷平衡
            if not entry.is_balanced:
                return jsonify({'success': False, 'message': 'Debit and Credit must be balanced'})

            entry.total_amount = entry.total_debit

            db.session.add(entry)
            db.session.commit()

            return jsonify({'success': True, 'message': 'Journal entry created successfully', 'entry_id': entry.id})

        except Exception as e:
            db.session.rollback()
            logger.error(f"创建分录失败: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})

    # 获取科目列表
    accounts = ChartOfAccount.query.filter_by(is_active=True, allow_manual_entry=True).order_by(ChartOfAccount.code).all()

    return render_template('finance/ledger/journal_entry_form.html',
                           form_title="Add Journal Entry",
                           accounts=accounts)


@ledger_blue.route('/journal-entries/<int:entry_id>/post', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def journal_entry_post(entry_id):
    """过账分录"""
    try:
        entry = JournalEntry.query.get_or_404(entry_id)
        entry.post(user=current_user.username if current_user else None)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Journal entry posted successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"过账失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ledger_blue.route('/journal-entries/<int:entry_id>/reverse', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def journal_entry_reverse(entry_id):
    """冲销分录"""
    try:
        entry = JournalEntry.query.get_or_404(entry_id)
        reverse_entry = entry.reverse(user=current_user.username if current_user else None)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Journal entry reversed successfully', 'reverse_entry_id': reverse_entry.id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"冲销失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ==================== 财务报表 ====================

@ledger_blue.route('/reports/ledger')
@login_required
@staff_only
def report_ledger():
    """总账报表 (Ledger Listing)"""
    account_id = request.args.get('account_id', type=int)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    accounts = ChartOfAccount.query.filter_by(is_active=True).order_by(ChartOfAccount.code).all()

    ledger_data = []
    if account_id:
        account = ChartOfAccount.query.get(account_id)
        if account:
            # 查询该科目的所有分录行
            query = JournalEntryLine.query.join(JournalEntry).filter(
                JournalEntryLine.account_id == account_id,
                JournalEntry.status == 'posted'
            )

            if start_date:
                query = query.filter(JournalEntry.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
            if end_date:
                query = query.filter(JournalEntry.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date())

            lines = query.order_by(JournalEntry.entry_date, JournalEntry.id).all()

            # 计算期初余额
            opening_balance = Decimal('0')
            if start_date:
                opening_query = db.session.query(
                    func.coalesce(func.sum(JournalEntryLine.debit), 0) - func.coalesce(func.sum(JournalEntryLine.credit), 0)
                ).join(JournalEntry).filter(
                    JournalEntryLine.account_id == account_id,
                    JournalEntry.status == 'posted',
                    JournalEntry.entry_date < datetime.strptime(start_date, '%Y-%m-%d').date()
                )
                result = opening_query.scalar()
                opening_balance = Decimal(str(result)) if result else Decimal('0')

            # 构建总账数据
            running_balance = opening_balance
            for line in lines:
                running_balance += (line.debit or Decimal('0')) - (line.credit or Decimal('0'))
                ledger_data.append({
                    'date': line.entry.entry_date,
                    'entry_id': line.entry.id,
                    'entry_number': line.entry.entry_number,
                    'description': line.entry.description,
                    'memo': line.memo,
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': running_balance
                })

            return render_template('finance/ledger/report_ledger.html',
                                   accounts=accounts,
                                   selected_account=account,
                                   ledger_data=ledger_data,
                                   opening_balance=opening_balance,
                                   start_date=start_date,
                                   end_date=end_date)

    return render_template('finance/ledger/report_ledger.html',
                           accounts=accounts,
                           ledger_data=[],
                           start_date=start_date,
                           end_date=end_date)


@ledger_blue.route('/reports/trial-balance')
@login_required
@staff_only
def report_trial_balance():
    """试算平衡表 (Trial Balance Listing) - 三维度：期初、本期、本年至今"""
    # 获取日期参数
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    # 默认日期范围（本月）
    if not start_date:
        start_date = date.today().replace(day=1).isoformat()
    if not end_date:
        end_date = date.today().isoformat()

    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    year_start_dt = date(end_dt.year, 1, 1)

    # 获取所有活跃科目
    accounts = ChartOfAccount.query.filter_by(is_active=True).order_by(ChartOfAccount.code).all()

    # 构建试算平衡表数据
    trial_balance = []

    # 汇总数据
    totals = {
        'opening_debit': Decimal('0'),
        'opening_credit': Decimal('0'),
        'current_debit': Decimal('0'),
        'current_credit': Decimal('0'),
        'ytd_debit': Decimal('0'),
        'ytd_credit': Decimal('0')
    }

    for account in accounts:
        # 1. 期初余额 (Opening Balance) - start_date 之前的所有交易
        opening_query = db.session.query(
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label('debit'),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label('credit')
        ).join(JournalEntry).filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.status == 'posted',
            JournalEntry.entry_date < start_dt
        ).first()

        opening_debit = Decimal(str(opening_query.debit)) if opening_query else Decimal('0')
        opening_credit = Decimal(str(opening_query.credit)) if opening_query else Decimal('0')

        # 2. 本期发生额 (Current Period) - start_date 到 end_date 之间的交易
        current_query = db.session.query(
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label('debit'),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label('credit')
        ).join(JournalEntry).filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.status == 'posted',
            JournalEntry.entry_date >= start_dt,
            JournalEntry.entry_date <= end_dt
        ).first()

        current_debit = Decimal(str(current_query.debit)) if current_query else Decimal('0')
        current_credit = Decimal(str(current_query.credit)) if current_query else Decimal('0')

        # 3. 本年至今 (Year To Date) - 年初到 end_date 的所有交易
        ytd_query = db.session.query(
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label('debit'),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label('credit')
        ).join(JournalEntry).filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.status == 'posted',
            JournalEntry.entry_date >= year_start_dt,
            JournalEntry.entry_date <= end_dt
        ).first()

        ytd_debit = Decimal(str(ytd_query.debit)) if ytd_query else Decimal('0')
        ytd_credit = Decimal(str(ytd_query.credit)) if ytd_query else Decimal('0')

        # 只显示有数据的科目
        if (opening_debit > 0 or opening_credit > 0 or
            current_debit > 0 or current_credit > 0 or
            ytd_debit > 0 or ytd_credit > 0):

            trial_balance.append({
                'code': account.code,
                'name': account.name,
                'name_cn': account.name_cn,
                'account_type': account.account_type,
                'opening_debit': opening_debit,
                'opening_credit': opening_credit,
                'current_debit': current_debit,
                'current_credit': current_credit,
                'ytd_debit': ytd_debit,
                'ytd_credit': ytd_credit
            })

            # 累计汇总
            totals['opening_debit'] += opening_debit
            totals['opening_credit'] += opening_credit
            totals['current_debit'] += current_debit
            totals['current_credit'] += current_credit
            totals['ytd_debit'] += ytd_debit
            totals['ytd_credit'] += ytd_credit

    # 公司名称
    company_name = 'JOYFUL ESCAPES PTE LTD'

    return render_template('finance/ledger/report_trial_balance.html',
                           trial_balance=trial_balance,
                           totals=totals,
                           company_name=company_name,
                           start_date=start_date,
                           end_date=end_date)


@ledger_blue.route('/reports/profit-loss')
@login_required
@staff_only
def report_profit_loss():
    """损益表 (Profit and Loss) - 升级版

    分类结构:
    - REVENUE (收入): income类型科目, 代码以4开头
    - COST OF SALES (销售成本): expense类型科目, 代码以5开头
    - COSTS AND EXPENSES (费用): expense类型科目, 代码以6或7开头
    - TAXATION (税务): expense类型科目, 代码以8或9开头

    计算:
    - Gross Profit = Revenue - Cost of Sales
    - Nett/Profit Loss = Gross Profit - Costs and Expenses
    - Nett/Profit Loss After Taxation = Nett/Profit Loss - Taxation
    """
    start_date = request.args.get('start_date', date.today().replace(month=1, day=1).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())

    # 计算年初日期用于 Year To Date
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        year_start = date(end_dt.year, 1, 1)
    except:
        start_dt = date.today().replace(month=1, day=1)
        end_dt = date.today()
        year_start = date(end_dt.year, 1, 1)

    # 公司名称
    company_name = 'JOYFUL ESCAPES PTE LTD'

    def get_account_amounts(account_type, code_prefix, period_start, period_end):
        """查询指定类型和代码前缀的科目金额

        Args:
            account_type: 'income' 或 'expense'
            code_prefix: 代码前缀，如 '4', '5', ('6', '7')
            period_start: 期间开始日期
            period_end: 期间结束日期
        """
        # 构建代码过滤条件
        if isinstance(code_prefix, tuple):
            code_filter = db.or_(*[ChartOfAccount.code.like(f'{p}%') for p in code_prefix])
        else:
            code_filter = ChartOfAccount.code.like(f'{code_prefix}%')

        query = db.session.query(
            ChartOfAccount.id,
            ChartOfAccount.code,
            ChartOfAccount.name,
            ChartOfAccount.name_cn,
            ChartOfAccount.parent_id,
            ChartOfAccount.level,
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label('debit'),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label('credit')
        ).outerjoin(
            JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id
        ).outerjoin(
            JournalEntry, JournalEntryLine.entry_id == JournalEntry.id
        ).filter(
            ChartOfAccount.is_active == True,
            ChartOfAccount.account_type == account_type,
            code_filter
        ).filter(
            db.or_(
                JournalEntry.id.is_(None),
                db.and_(
                    JournalEntry.status == 'posted',
                    JournalEntry.entry_date >= period_start,
                    JournalEntry.entry_date <= period_end
                )
            )
        ).group_by(ChartOfAccount.id).order_by(ChartOfAccount.code)

        return query.all()

    def process_accounts(data, is_income=True):
        """处理科目数据，计算金额并组织层级结构"""
        items = []
        total = Decimal('0')

        # 创建ID到数据的映射
        id_to_data = {}
        for row in data:
            if is_income:
                amount = Decimal(str(row.credit)) - Decimal(str(row.debit))
            else:
                amount = Decimal(str(row.debit)) - Decimal(str(row.credit))

            id_to_data[row.id] = {
                'id': row.id,
                'code': row.code,
                'name': row.name,
                'name_cn': row.name_cn,
                'parent_id': row.parent_id,
                'level': row.level,
                'amount': amount,
                'is_parent': False
            }

        # 标记有子科目的父科目
        for item_id, item in id_to_data.items():
            if item['parent_id'] and item['parent_id'] in id_to_data:
                id_to_data[item['parent_id']]['is_parent'] = True

        # 按代码排序并构建结果
        sorted_items = sorted(id_to_data.values(), key=lambda x: x['code'])

        for item in sorted_items:
            # 只累加叶子节点的金额到总计
            if not item['is_parent'] and item['amount'] != 0:
                total += item['amount']

            # 所有有金额的科目都显示
            if item['amount'] != 0 or item['is_parent']:
                items.append(item)

        return items, total

    # ============ REVENUE (收入) - 代码以4开头 ============
    revenue_current = get_account_amounts('income', '4', start_dt, end_dt)
    revenue_ytd = get_account_amounts('income', '4', year_start, end_dt)

    revenue_items_current, total_revenue_current = process_accounts(revenue_current, is_income=True)
    revenue_items_ytd, total_revenue_ytd = process_accounts(revenue_ytd, is_income=True)

    # 合并当期和年累计数据
    revenue_items = []
    ytd_map = {item['code']: item['amount'] for item in revenue_items_ytd}
    for item in revenue_items_current:
        revenue_items.append({
            'code': item['code'],
            'name': item['name'],
            'name_cn': item['name_cn'],
            'level': item['level'],
            'is_parent': item['is_parent'],
            'current_period': item['amount'],
            'year_to_date': ytd_map.get(item['code'], Decimal('0'))
        })

    # ============ COST OF SALES (销售成本) - 代码以5开头 ============
    cos_current = get_account_amounts('expense', '5', start_dt, end_dt)
    cos_ytd = get_account_amounts('expense', '5', year_start, end_dt)

    cos_items_current, total_cos_current = process_accounts(cos_current, is_income=False)
    cos_items_ytd, total_cos_ytd = process_accounts(cos_ytd, is_income=False)

    cos_items = []
    ytd_map = {item['code']: item['amount'] for item in cos_items_ytd}
    for item in cos_items_current:
        cos_items.append({
            'code': item['code'],
            'name': item['name'],
            'name_cn': item['name_cn'],
            'level': item['level'],
            'is_parent': item['is_parent'],
            'current_period': item['amount'],
            'year_to_date': ytd_map.get(item['code'], Decimal('0'))
        })

    # ============ COSTS AND EXPENSES (费用) - 代码以6或7开头 ============
    expenses_current = get_account_amounts('expense', ('6', '7'), start_dt, end_dt)
    expenses_ytd = get_account_amounts('expense', ('6', '7'), year_start, end_dt)

    expenses_items_current, total_expenses_current = process_accounts(expenses_current, is_income=False)
    expenses_items_ytd, total_expenses_ytd = process_accounts(expenses_ytd, is_income=False)

    expenses_items = []
    ytd_map = {item['code']: item['amount'] for item in expenses_items_ytd}
    for item in expenses_items_current:
        expenses_items.append({
            'code': item['code'],
            'name': item['name'],
            'name_cn': item['name_cn'],
            'level': item['level'],
            'is_parent': item['is_parent'],
            'current_period': item['amount'],
            'year_to_date': ytd_map.get(item['code'], Decimal('0'))
        })

    # ============ TAXATION (税务) - 代码以8或9开头 ============
    tax_current = get_account_amounts('expense', ('8', '9'), start_dt, end_dt)
    tax_ytd = get_account_amounts('expense', ('8', '9'), year_start, end_dt)

    tax_items_current, total_tax_current = process_accounts(tax_current, is_income=False)
    tax_items_ytd, total_tax_ytd = process_accounts(tax_ytd, is_income=False)

    tax_items = []
    ytd_map = {item['code']: item['amount'] for item in tax_items_ytd}
    for item in tax_items_current:
        tax_items.append({
            'code': item['code'],
            'name': item['name'],
            'name_cn': item['name_cn'],
            'level': item['level'],
            'is_parent': item['is_parent'],
            'current_period': item['amount'],
            'year_to_date': ytd_map.get(item['code'], Decimal('0'))
        })

    # ============ 计算各项汇总 ============
    # 毛利润 = 收入 - 销售成本
    gross_profit_current = total_revenue_current - total_cos_current
    gross_profit_ytd = total_revenue_ytd - total_cos_ytd

    # 净利润(税前) = 毛利润 - 费用
    net_profit_current = gross_profit_current - total_expenses_current
    net_profit_ytd = gross_profit_ytd - total_expenses_ytd

    # 税后净利润 = 净利润 - 税务
    net_profit_after_tax_current = net_profit_current - total_tax_current
    net_profit_after_tax_ytd = net_profit_ytd - total_tax_ytd

    return render_template('finance/ledger/report_profit_loss.html',
                           company_name=company_name,
                           # Revenue
                           revenue_items=revenue_items,
                           total_revenue_current=total_revenue_current,
                           total_revenue_ytd=total_revenue_ytd,
                           # Cost of Sales
                           cos_items=cos_items,
                           total_cos_current=total_cos_current,
                           total_cos_ytd=total_cos_ytd,
                           # Gross Profit
                           gross_profit_current=gross_profit_current,
                           gross_profit_ytd=gross_profit_ytd,
                           # Costs and Expenses
                           expenses_items=expenses_items,
                           total_expenses_current=total_expenses_current,
                           total_expenses_ytd=total_expenses_ytd,
                           # Net Profit (before tax)
                           net_profit_current=net_profit_current,
                           net_profit_ytd=net_profit_ytd,
                           # Taxation
                           tax_items=tax_items,
                           total_tax_current=total_tax_current,
                           total_tax_ytd=total_tax_ytd,
                           # Net Profit After Tax
                           net_profit_after_tax_current=net_profit_after_tax_current,
                           net_profit_after_tax_ytd=net_profit_after_tax_ytd,
                           # Dates
                           start_date=start_date,
                           end_date=end_date)


@ledger_blue.route('/reports/balance-sheet')
@login_required
@staff_only
def report_balance_sheet():
    """资产负债表 (Balance Sheet) - 升级版

    结构:
    - ASSETS 资产
      - Current Assets 流动资产 (1xxx)
      - Total Current Assets
    - Total Assets

    - LIABILITIES AND CAPITAL 负债和资本
      - Current Liabilities 流动负债 (2xxx)
      - Total Current Liabilities
    - Total Liabilities

    - Capital 资本 (3xxx + Net Income)
      - Net Income 净利润
    - Total Capital

    - Total Liabilities Capital = Total Assets
    """
    as_of_date = request.args.get('as_of_date', date.today().isoformat())

    # 公司名称
    company_name = 'JOYFUL ESCAPES PTE LTD'

    try:
        as_of_dt = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        year_start = date(as_of_dt.year, 1, 1)
    except:
        as_of_dt = date.today()
        year_start = date(as_of_dt.year, 1, 1)

    def get_account_balances(account_type, period_end, period_start=None):
        """查询指定类型科目的余额

        Args:
            account_type: 'asset', 'liability', 'equity'
            period_end: 期间结束日期
            period_start: 期间开始日期 (用于计算当期变动)
        """
        query = db.session.query(
            ChartOfAccount.id,
            ChartOfAccount.code,
            ChartOfAccount.name,
            ChartOfAccount.name_cn,
            ChartOfAccount.level,
            ChartOfAccount.parent_id,
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label('debit'),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label('credit')
        ).outerjoin(
            JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id
        ).outerjoin(
            JournalEntry, JournalEntryLine.entry_id == JournalEntry.id
        ).filter(
            ChartOfAccount.is_active == True,
            ChartOfAccount.account_type == account_type
        )

        # 根据是否有开始日期决定是期末余额还是当期变动
        if period_start:
            # 当期变动: 从 period_start 到 period_end
            query = query.filter(
                db.or_(
                    JournalEntry.id.is_(None),
                    db.and_(
                        JournalEntry.status == 'posted',
                        JournalEntry.entry_date >= period_start,
                        JournalEntry.entry_date <= period_end
                    )
                )
            )
        else:
            # 期末余额: 从开始到 period_end
            query = query.filter(
                db.or_(
                    JournalEntry.id.is_(None),
                    db.and_(
                        JournalEntry.status == 'posted',
                        JournalEntry.entry_date <= period_end
                    )
                )
            )

        return query.group_by(ChartOfAccount.id).order_by(ChartOfAccount.code).all()

    def process_balance_accounts(data, is_debit_normal=True):
        """处理资产负债表科目数据"""
        items = []
        total = Decimal('0')

        for row in data:
            if is_debit_normal:
                balance = Decimal(str(row.debit)) - Decimal(str(row.credit))
            else:
                balance = Decimal(str(row.credit)) - Decimal(str(row.debit))

            if balance != 0:
                items.append({
                    'code': row.code,
                    'name': row.name,
                    'name_cn': row.name_cn,
                    'level': row.level,
                    'amount': balance
                })
                total += balance

        return items, total

    def get_net_income(period_start, period_end):
        """计算净利润 (收入 - 费用)"""
        income_query = db.session.query(
            func.coalesce(func.sum(JournalEntryLine.credit - JournalEntryLine.debit), 0)
        ).join(JournalEntry).join(ChartOfAccount).filter(
            JournalEntry.status == 'posted',
            ChartOfAccount.account_type == 'income',
            JournalEntry.entry_date >= period_start,
            JournalEntry.entry_date <= period_end
        )

        expense_query = db.session.query(
            func.coalesce(func.sum(JournalEntryLine.debit - JournalEntryLine.credit), 0)
        ).join(JournalEntry).join(ChartOfAccount).filter(
            JournalEntry.status == 'posted',
            ChartOfAccount.account_type == 'expense',
            JournalEntry.entry_date >= period_start,
            JournalEntry.entry_date <= period_end
        )

        total_income = Decimal(str(income_query.scalar() or 0))
        total_expense = Decimal(str(expense_query.scalar() or 0))
        return total_income - total_expense

    # ============ ASSETS 资产 ============
    # Year To Date (从年初到截止日期的累计)
    asset_data_ytd = get_account_balances('asset', as_of_dt)
    asset_items_ytd, total_assets_ytd = process_balance_accounts(asset_data_ytd, is_debit_normal=True)

    # Current Period (当期变动 - 从年初到截止日期)
    # 对于资产负债表，Current Period 通常显示的是期末余额，Year To Date 也是期末余额
    # 但根据参考图片，两列数值不同，Current Period 可能是当月/当期变动
    # 这里我们按照参考图片理解：Current Period = 从某个起始点到截止日期的余额变动
    # 暂时用 as_of_date 当月的数据作为 Current Period
    current_month_start = as_of_dt.replace(day=1)
    asset_data_current = get_account_balances('asset', as_of_dt, current_month_start)
    asset_items_current, total_assets_current = process_balance_accounts(asset_data_current, is_debit_normal=True)

    # 合并数据
    asset_items = []
    ytd_map = {item['code']: item['amount'] for item in asset_items_ytd}
    current_map = {item['code']: item['amount'] for item in asset_items_current}
    all_codes = set(ytd_map.keys()) | set(current_map.keys())
    for code in sorted(all_codes):
        ytd_item = next((i for i in asset_items_ytd if i['code'] == code), None)
        if ytd_item:
            asset_items.append({
                'code': code,
                'name': ytd_item['name'],
                'name_cn': ytd_item['name_cn'],
                'level': ytd_item['level'],
                'current_period': current_map.get(code, Decimal('0')),
                'year_to_date': ytd_map.get(code, Decimal('0'))
            })

    # ============ LIABILITIES 负债 ============
    liability_data_ytd = get_account_balances('liability', as_of_dt)
    liability_items_ytd, total_liabilities_ytd = process_balance_accounts(liability_data_ytd, is_debit_normal=False)

    liability_data_current = get_account_balances('liability', as_of_dt, current_month_start)
    liability_items_current, total_liabilities_current = process_balance_accounts(liability_data_current, is_debit_normal=False)

    liability_items = []
    ytd_map = {item['code']: item['amount'] for item in liability_items_ytd}
    current_map = {item['code']: item['amount'] for item in liability_items_current}
    all_codes = set(ytd_map.keys()) | set(current_map.keys())
    for code in sorted(all_codes):
        ytd_item = next((i for i in liability_items_ytd if i['code'] == code), None)
        if ytd_item:
            liability_items.append({
                'code': code,
                'name': ytd_item['name'],
                'name_cn': ytd_item['name_cn'],
                'level': ytd_item['level'],
                'current_period': current_map.get(code, Decimal('0')),
                'year_to_date': ytd_map.get(code, Decimal('0'))
            })

    # ============ CAPITAL/EQUITY 资本/权益 ============
    equity_data_ytd = get_account_balances('equity', as_of_dt)
    equity_items_ytd, total_equity_ytd = process_balance_accounts(equity_data_ytd, is_debit_normal=False)

    equity_data_current = get_account_balances('equity', as_of_dt, current_month_start)
    equity_items_current, total_equity_current = process_balance_accounts(equity_data_current, is_debit_normal=False)

    capital_items = []
    ytd_map = {item['code']: item['amount'] for item in equity_items_ytd}
    current_map = {item['code']: item['amount'] for item in equity_items_current}
    all_codes = set(ytd_map.keys()) | set(current_map.keys())
    for code in sorted(all_codes):
        ytd_item = next((i for i in equity_items_ytd if i['code'] == code), None)
        if ytd_item:
            capital_items.append({
                'code': code,
                'name': ytd_item['name'],
                'name_cn': ytd_item['name_cn'],
                'level': ytd_item['level'],
                'current_period': current_map.get(code, Decimal('0')),
                'year_to_date': ytd_map.get(code, Decimal('0'))
            })

    # ============ NET INCOME 净利润 ============
    # 当期净利润 (当月)
    net_income_current = get_net_income(current_month_start, as_of_dt)
    # 年累计净利润 (从年初到截止日期)
    net_income_ytd = get_net_income(year_start, as_of_dt)

    # 将净利润加入资本总计
    total_capital_current = total_equity_current + net_income_current
    total_capital_ytd = total_equity_ytd + net_income_ytd

    # ============ 汇总计算 ============
    # Total Liabilities + Capital
    total_liab_capital_current = total_liabilities_current + total_capital_current
    total_liab_capital_ytd = total_liabilities_ytd + total_capital_ytd

    # 重新计算资产总计 (使用YTD作为期末余额)
    # 资产期末余额应该等于负债+权益期末余额
    is_balanced = abs(total_assets_ytd - total_liab_capital_ytd) < Decimal('0.01')

    return render_template('finance/ledger/report_balance_sheet.html',
                           company_name=company_name,
                           # Assets
                           asset_items=asset_items,
                           total_assets_current=total_assets_current,
                           total_assets_ytd=total_assets_ytd,
                           # Liabilities
                           liability_items=liability_items,
                           total_liabilities_current=total_liabilities_current,
                           total_liabilities_ytd=total_liabilities_ytd,
                           # Capital
                           capital_items=capital_items,
                           total_equity_current=total_equity_current,
                           total_equity_ytd=total_equity_ytd,
                           # Net Income
                           net_income_current=net_income_current,
                           net_income_ytd=net_income_ytd,
                           # Total Capital
                           total_capital_current=total_capital_current,
                           total_capital_ytd=total_capital_ytd,
                           # Total Liabilities + Capital
                           total_liab_capital_current=total_liab_capital_current,
                           total_liab_capital_ytd=total_liab_capital_ytd,
                           # Balance check
                           is_balanced=is_balanced,
                           as_of_date=as_of_date)


@ledger_blue.route('/reports/general-journal')
@login_required
@staff_only
def report_general_journal():
    """普通日记账报表 (General Journal)"""
    start_date = request.args.get('start_date', date.today().replace(day=1).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    source_type = request.args.get('source_type', '').strip()

    query = JournalEntry.query.filter_by(status='posted')

    if start_date:
        query = query.filter(JournalEntry.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(JournalEntry.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if source_type:
        query = query.filter_by(source_type=source_type)

    entries = query.order_by(JournalEntry.entry_date, JournalEntry.id).all()

    # 计算总额
    total_debit = sum(entry.total_debit for entry in entries)
    total_credit = sum(entry.total_credit for entry in entries)

    return render_template('finance/ledger/report_general_journal.html',
                           entries=entries,
                           total_debit=total_debit,
                           total_credit=total_credit,
                           start_date=start_date,
                           end_date=end_date,
                           current_source_type=source_type)


@ledger_blue.route('/reports/general-ledger-listing')
@login_required
@staff_only
def report_general_ledger_listing():
    """General Ledger Listing 总账明细表 - 按账户分组显示所有交易"""
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    # 默认日期范围（本月）
    if not start_date:
        start_date = date.today().replace(day=1).isoformat()
    if not end_date:
        end_date = date.today().isoformat()

    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    # 获取所有有交易的科目
    accounts_with_transactions = db.session.query(
        ChartOfAccount.id
    ).join(
        JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id
    ).join(
        JournalEntry, JournalEntryLine.entry_id == JournalEntry.id
    ).filter(
        ChartOfAccount.is_active == True,
        JournalEntry.status == 'posted'
    ).distinct().all()

    account_ids = [a.id for a in accounts_with_transactions]

    # 构建总账数据
    ledger_data = []

    for account in ChartOfAccount.query.filter(
        ChartOfAccount.id.in_(account_ids)
    ).order_by(ChartOfAccount.code).all():
        # 计算期初余额
        opening_query = db.session.query(
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label('debit'),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label('credit')
        ).join(JournalEntry).filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.status == 'posted',
            JournalEntry.entry_date < start_dt
        )
        opening_result = opening_query.first()
        opening_debit = Decimal(str(opening_result.debit)) if opening_result else Decimal('0')
        opening_credit = Decimal(str(opening_result.credit)) if opening_result else Decimal('0')

        # 根据账户余额方向计算期初余额
        if account.balance_direction == 'debit':
            opening_balance = opening_debit - opening_credit
        else:
            opening_balance = opening_credit - opening_debit

        # 查询本期交易
        lines_query = JournalEntryLine.query.join(JournalEntry).filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.status == 'posted',
            JournalEntry.entry_date >= start_dt,
            JournalEntry.entry_date <= end_dt
        ).order_by(JournalEntry.entry_date, JournalEntry.id)

        lines = lines_query.all()

        if not lines and opening_balance == 0:
            continue  # 跳过无交易且期初为零的科目

        # 构建交易明细
        transactions = []
        running_balance = opening_balance
        period_debit = Decimal('0')
        period_credit = Decimal('0')

        for line in lines:
            debit = line.debit or Decimal('0')
            credit = line.credit or Decimal('0')
            period_debit += debit
            period_credit += credit

            # 计算余额
            if account.balance_direction == 'debit':
                running_balance += debit - credit
            else:
                running_balance += credit - debit

            # 获取关联信息
            entry = line.entry
            subsidiary_name = ''
            description1 = ''
            description2 = line.memo or ''

            # 根据来源类型获取更多信息
            if entry.source_type == 'invoice':
                from App_new.business.projects.models.invoice import ProjectInvoice
                invoice = ProjectInvoice.query.get(entry.source_id)
                if invoice:
                    # 优先使用 header.company，否则使用 customer_company
                    if invoice.header and invoice.header.company:
                        subsidiary_name = invoice.header.company.company_name
                    elif invoice.customer_company:
                        subsidiary_name = invoice.customer_company
                description1 = f'For Invoice No - {entry.source_number}'
            elif entry.source_type == 'receipt':
                from App_new.business.projects.models.receipt import ProjectReceipt
                receipt = ProjectReceipt.query.get(entry.source_id)
                if receipt:
                    # 优先使用 header.company，否则使用 payer_company
                    if receipt.header and receipt.header.company:
                        subsidiary_name = receipt.header.company.company_name
                    elif receipt.payer_company:
                        subsidiary_name = receipt.payer_company
                description1 = f'For Receipt No - {entry.source_number}'
            elif entry.source_type == 'eo':
                from App_new.business.projects.models.eo import ProjectEO
                eo = ProjectEO.query.get(entry.source_id)
                if eo and eo.ref and eo.ref.supplier:
                    subsidiary_name = getattr(eo.ref.supplier, 'name_en', None) or eo.ref.supplier.name
                description1 = f'For EO No - {entry.source_number}'
            else:
                description1 = entry.description or ''

            transactions.append({
                'date': entry.entry_date,
                'ref': entry.source_number or entry.entry_number,
                'jrnl_no': entry.entry_number,
                'entry_id': entry.id,  # 用于链接到日记账详情页
                'subsidiary_name': subsidiary_name,
                'description1': description1,
                'description2': description2,
                'fx_rate': 1.00,  # 暂时固定为1
                'debit': debit,
                'credit': credit,
                'balance': running_balance
            })

        # 计算期末余额
        ending_balance = running_balance

        # 计算本期变动
        if account.balance_direction == 'debit':
            period_change = period_debit - period_credit
        else:
            period_change = period_credit - period_debit

        ledger_data.append({
            'account': account,
            'opening_balance': opening_balance,
            'transactions': transactions,
            'trans_count': len(transactions),
            'period_debit': period_debit,
            'period_credit': period_credit,
            'period_change': period_change,
            'ending_balance': ending_balance
        })

    # 公司名称
    company_name = 'JOYFUL ESCAPES PTE LTD'

    return render_template('finance/ledger/report_general_ledger_listing.html',
                           ledger_data=ledger_data,
                           company_name=company_name,
                           start_date=start_date,
                           end_date=end_date)


@ledger_blue.route('/reports/journal-entries')
@login_required
@staff_only
def report_journal_entries():
    """Journal Entry 报表 - 简洁格式"""
    start_date = request.args.get('start_date', date.today().replace(day=1).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    source_type = request.args.get('source_type', '').strip()

    query = JournalEntry.query.filter_by(status='posted')

    if start_date:
        query = query.filter(JournalEntry.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(JournalEntry.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if source_type:
        query = query.filter_by(source_type=source_type)

    entries = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc()).all()

    # 计算总额
    total_debit = sum(entry.total_debit for entry in entries)
    total_credit = sum(entry.total_credit for entry in entries)

    return render_template('finance/ledger/report_journal_entries.html',
                           entries=entries,
                           total_debit=total_debit,
                           total_credit=total_credit,
                           start_date=start_date,
                           end_date=end_date,
                           current_source_type=source_type)


# ==================== 运营费用 Operating Expense ====================

@ledger_blue.route('/operating-expenses')
@login_required
@staff_only
def operating_expense_list():
    """运营费用列表"""
    from App_new.finance.models.operating_expense import OperatingExpense

    status = request.args.get('status', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    query = OperatingExpense.query

    if status:
        query = query.filter_by(status=status)
    if start_date:
        query = query.filter(OperatingExpense.expense_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(OperatingExpense.expense_date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    expenses = query.order_by(OperatingExpense.expense_date.desc(), OperatingExpense.id.desc()).all()

    # 统计
    stats = {
        'total': OperatingExpense.query.count(),
        'draft': OperatingExpense.query.filter_by(status='draft').count(),
        'confirmed': OperatingExpense.query.filter_by(status='confirmed').count(),
        'paid': OperatingExpense.query.filter_by(status='paid').count(),
    }

    # 获取费用科目列表（用于筛选）
    expense_accounts = ChartOfAccount.query.filter_by(
        account_type='expense', is_active=True
    ).order_by(ChartOfAccount.code).all()

    return render_template('finance/ledger/operating_expense_list.html',
                           expenses=expenses,
                           stats=stats,
                           expense_accounts=expense_accounts,
                           current_status=status,
                           start_date=start_date,
                           end_date=end_date)


@ledger_blue.route('/operating-expenses/add', methods=['GET', 'POST'])
@login_required
@staff_only
def operating_expense_add():
    """添加运营费用"""
    from App_new.finance.models.operating_expense import OperatingExpense

    if request.method == 'POST':
        data = request.get_json()

        try:
            # 生成编号
            expense_number = OperatingExpense.generate_expense_number()

            expense = OperatingExpense(
                expense_number=expense_number,
                expense_date=datetime.strptime(data['expense_date'], '%Y-%m-%d').date(),
                expense_account_id=int(data['expense_account_id']),
                amount=Decimal(str(data['amount'])),
                currency=data.get('currency', 'SGD'),
                payment_method=data.get('payment_method', 'bank_transfer'),
                bank_account_id=int(data['bank_account_id']) if data.get('bank_account_id') else None,
                payment_reference=data.get('payment_reference', ''),
                payee_name=data.get('payee_name', ''),
                payee_account=data.get('payee_account', ''),
                description=data['description'],
                remarks=data.get('remarks', ''),
                status='draft',
                created_by=current_user.email if current_user else 'system'
            )

            db.session.add(expense)
            db.session.commit()

            return jsonify({'success': True, 'message': '费用单创建成功', 'expense_id': expense.id})

        except Exception as e:
            db.session.rollback()
            logger.error(f"创建运营费用失败: {e}")
            return jsonify({'success': False, 'message': str(e)})

    # GET 请求 - 显示表单
    # 获取费用科目
    expense_accounts = ChartOfAccount.query.filter_by(
        account_type='expense', is_active=True
    ).order_by(ChartOfAccount.code).all()

    # 获取银行/现金科目
    bank_accounts = ChartOfAccount.query.filter(
        ChartOfAccount.account_type == 'asset',
        ChartOfAccount.is_active == True,
        ChartOfAccount.code.like('1%')  # 资产类
    ).order_by(ChartOfAccount.code).all()

    return render_template('finance/ledger/operating_expense_form.html',
                           expense=None,
                           expense_accounts=expense_accounts,
                           bank_accounts=bank_accounts,
                           form_title='Add Operating Expense 添加运营费用',
                           today=date.today().isoformat())


@ledger_blue.route('/operating-expenses/<int:expense_id>')
@login_required
@staff_only
def operating_expense_detail(expense_id):
    """运营费用详情"""
    from App_new.finance.models.operating_expense import OperatingExpense

    expense = OperatingExpense.query.get_or_404(expense_id)
    return render_template('finance/ledger/operating_expense_detail.html', expense=expense)


@ledger_blue.route('/operating-expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def operating_expense_edit(expense_id):
    """编辑运营费用"""
    from App_new.finance.models.operating_expense import OperatingExpense

    expense = OperatingExpense.query.get_or_404(expense_id)

    if expense.status not in ['draft']:
        flash('只能编辑草稿状态的费用单', 'warning')
        return redirect(url_for('ledger_routes.operating_expense_detail', expense_id=expense_id))

    if request.method == 'POST':
        data = request.get_json()

        try:
            expense.expense_date = datetime.strptime(data['expense_date'], '%Y-%m-%d').date()
            expense.expense_account_id = int(data['expense_account_id'])
            expense.amount = Decimal(str(data['amount']))
            expense.currency = data.get('currency', 'SGD')
            expense.payment_method = data.get('payment_method', 'bank_transfer')
            expense.bank_account_id = int(data['bank_account_id']) if data.get('bank_account_id') else None
            expense.payment_reference = data.get('payment_reference', '')
            expense.payee_name = data.get('payee_name', '')
            expense.payee_account = data.get('payee_account', '')
            expense.description = data['description']
            expense.remarks = data.get('remarks', '')

            db.session.commit()
            return jsonify({'success': True, 'message': '费用单更新成功'})

        except Exception as e:
            db.session.rollback()
            logger.error(f"更新运营费用失败: {e}")
            return jsonify({'success': False, 'message': str(e)})

    # GET 请求
    expense_accounts = ChartOfAccount.query.filter_by(
        account_type='expense', is_active=True
    ).order_by(ChartOfAccount.code).all()

    bank_accounts = ChartOfAccount.query.filter(
        ChartOfAccount.account_type == 'asset',
        ChartOfAccount.is_active == True,
        ChartOfAccount.code.like('1%')
    ).order_by(ChartOfAccount.code).all()

    return render_template('finance/ledger/operating_expense_form.html',
                           expense=expense,
                           expense_accounts=expense_accounts,
                           bank_accounts=bank_accounts,
                           form_title='Edit Operating Expense 编辑运营费用',
                           today=date.today().isoformat())


@ledger_blue.route('/operating-expenses/<int:expense_id>/confirm', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def operating_expense_confirm(expense_id):
    """确认运营费用（生成日记账分录）"""
    from App_new.finance.models.operating_expense import OperatingExpense

    expense = OperatingExpense.query.get_or_404(expense_id)

    if expense.status != 'draft':
        return jsonify({'success': False, 'message': '只能确认草稿状态的费用单'})

    try:
        # 生成日记账分录
        entry_number = JournalEntry.generate_entry_number()

        journal_entry = JournalEntry(
            entry_number=entry_number,
            entry_date=expense.expense_date,
            source_type='operating_expense',
            source_id=expense.id,
            source_number=expense.expense_number,
            description=f'Operating Expense - {expense.description}',
            currency=expense.currency,
            status='posted',
            posted_at=datetime.utcnow(),
            posted_by=current_user.email if current_user else 'system',
            created_by=current_user.email if current_user else 'system'
        )

        # 借：费用科目
        debit_line = JournalEntryLine(
            line_no=1,
            account_id=expense.expense_account_id,
            debit=expense.amount,
            credit=Decimal('0'),
            memo=expense.description
        )
        journal_entry.lines.append(debit_line)

        # 贷：银行/现金科目
        if expense.bank_account_id:
            credit_account_id = expense.bank_account_id
        else:
            # 默认使用银行科目 1002
            default_bank = ChartOfAccount.query.filter_by(code='1002').first()
            credit_account_id = default_bank.id if default_bank else expense.bank_account_id

        credit_line = JournalEntryLine(
            line_no=2,
            account_id=credit_account_id,
            debit=Decimal('0'),
            credit=expense.amount,
            memo=f'Payment for {expense.description}'
        )
        journal_entry.lines.append(credit_line)

        journal_entry.total_amount = expense.amount

        db.session.add(journal_entry)

        # 更新费用单状态
        expense.status = 'paid'
        expense.journal_entry_id = journal_entry.id

        db.session.commit()

        return jsonify({'success': True, 'message': '费用单已确认并生成日记账分录'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"确认运营费用失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@ledger_blue.route('/operating-expenses/<int:expense_id>/cancel', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def operating_expense_cancel(expense_id):
    """取消运营费用"""
    from App_new.finance.models.operating_expense import OperatingExpense

    expense = OperatingExpense.query.get_or_404(expense_id)

    if expense.status == 'cancelled':
        return jsonify({'success': False, 'message': '费用单已取消'})

    try:
        expense.status = 'cancelled'
        db.session.commit()
        return jsonify({'success': True, 'message': '费用单已取消'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
