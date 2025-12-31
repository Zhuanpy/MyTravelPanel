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
    """试算平衡表 (Trial Balance)"""
    as_of_date = request.args.get('as_of_date', date.today().isoformat())

    # 查询所有科目的借贷余额
    query = db.session.query(
        ChartOfAccount.id,
        ChartOfAccount.code,
        ChartOfAccount.name,
        ChartOfAccount.name_cn,
        ChartOfAccount.account_type,
        ChartOfAccount.balance_direction,
        func.coalesce(func.sum(JournalEntryLine.debit), 0).label('total_debit'),
        func.coalesce(func.sum(JournalEntryLine.credit), 0).label('total_credit')
    ).outerjoin(
        JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id
    ).outerjoin(
        JournalEntry, JournalEntryLine.entry_id == JournalEntry.id
    ).filter(
        ChartOfAccount.is_active == True
    )

    if as_of_date:
        query = query.filter(
            db.or_(
                JournalEntry.id.is_(None),
                db.and_(
                    JournalEntry.status == 'posted',
                    JournalEntry.entry_date <= datetime.strptime(as_of_date, '%Y-%m-%d').date()
                )
            )
        )

    query = query.group_by(ChartOfAccount.id).order_by(ChartOfAccount.code)

    results = query.all()

    # 构建试算平衡表数据
    trial_balance = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')

    for row in results:
        debit = Decimal(str(row.total_debit))
        credit = Decimal(str(row.total_credit))
        balance = debit - credit

        # 根据余额方向确定借贷栏
        if row.balance_direction == 'debit':
            debit_balance = balance if balance > 0 else Decimal('0')
            credit_balance = abs(balance) if balance < 0 else Decimal('0')
        else:
            debit_balance = abs(balance) if balance < 0 else Decimal('0')
            credit_balance = balance if balance > 0 else Decimal('0')

        # 只显示有余额的科目
        if debit_balance > 0 or credit_balance > 0:
            trial_balance.append({
                'code': row.code,
                'name': row.name,
                'name_cn': row.name_cn,
                'account_type': row.account_type,
                'debit': debit_balance,
                'credit': credit_balance
            })
            total_debit += debit_balance
            total_credit += credit_balance

    is_balanced = abs(total_debit - total_credit) < Decimal('0.01')

    return render_template('finance/ledger/report_trial_balance.html',
                           trial_balance=trial_balance,
                           total_debit=total_debit,
                           total_credit=total_credit,
                           is_balanced=is_balanced,
                           as_of_date=as_of_date)


@ledger_blue.route('/reports/profit-loss')
@login_required
@staff_only
def report_profit_loss():
    """损益表 (Profit and Loss)"""
    start_date = request.args.get('start_date', date.today().replace(month=1, day=1).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())

    # 查询收入类科目
    income_query = db.session.query(
        ChartOfAccount.code,
        ChartOfAccount.name,
        ChartOfAccount.name_cn,
        func.coalesce(func.sum(JournalEntryLine.credit), 0).label('credit'),
        func.coalesce(func.sum(JournalEntryLine.debit), 0).label('debit')
    ).outerjoin(
        JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id
    ).outerjoin(
        JournalEntry, JournalEntryLine.entry_id == JournalEntry.id
    ).filter(
        ChartOfAccount.is_active == True,
        ChartOfAccount.account_type == 'income'
    )

    if start_date and end_date:
        income_query = income_query.filter(
            db.or_(
                JournalEntry.id.is_(None),
                db.and_(
                    JournalEntry.status == 'posted',
                    JournalEntry.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
                    JournalEntry.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
                )
            )
        )

    income_data = income_query.group_by(ChartOfAccount.id).order_by(ChartOfAccount.code).all()

    # 查询费用类科目
    expense_query = db.session.query(
        ChartOfAccount.code,
        ChartOfAccount.name,
        ChartOfAccount.name_cn,
        func.coalesce(func.sum(JournalEntryLine.debit), 0).label('debit'),
        func.coalesce(func.sum(JournalEntryLine.credit), 0).label('credit')
    ).outerjoin(
        JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id
    ).outerjoin(
        JournalEntry, JournalEntryLine.entry_id == JournalEntry.id
    ).filter(
        ChartOfAccount.is_active == True,
        ChartOfAccount.account_type == 'expense'
    )

    if start_date and end_date:
        expense_query = expense_query.filter(
            db.or_(
                JournalEntry.id.is_(None),
                db.and_(
                    JournalEntry.status == 'posted',
                    JournalEntry.entry_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
                    JournalEntry.entry_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
                )
            )
        )

    expense_data = expense_query.group_by(ChartOfAccount.id).order_by(ChartOfAccount.code).all()

    # 计算收入总额
    income_items = []
    total_income = Decimal('0')
    for row in income_data:
        amount = Decimal(str(row.credit)) - Decimal(str(row.debit))
        if amount != 0:
            income_items.append({
                'code': row.code,
                'name': row.name,
                'name_cn': row.name_cn,
                'amount': amount
            })
            total_income += amount

    # 计算费用总额
    expense_items = []
    total_expense = Decimal('0')
    for row in expense_data:
        amount = Decimal(str(row.debit)) - Decimal(str(row.credit))
        if amount != 0:
            expense_items.append({
                'code': row.code,
                'name': row.name,
                'name_cn': row.name_cn,
                'amount': amount
            })
            total_expense += amount

    net_profit = total_income - total_expense

    return render_template('finance/ledger/report_profit_loss.html',
                           income_items=income_items,
                           expense_items=expense_items,
                           total_income=total_income,
                           total_expense=total_expense,
                           net_profit=net_profit,
                           start_date=start_date,
                           end_date=end_date)


@ledger_blue.route('/reports/balance-sheet')
@login_required
@staff_only
def report_balance_sheet():
    """资产负债表 (Balance Sheet)"""
    as_of_date = request.args.get('as_of_date', date.today().isoformat())

    def get_account_balances(account_type):
        query = db.session.query(
            ChartOfAccount.code,
            ChartOfAccount.name,
            ChartOfAccount.name_cn,
            ChartOfAccount.balance_direction,
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

        if as_of_date:
            query = query.filter(
                db.or_(
                    JournalEntry.id.is_(None),
                    db.and_(
                        JournalEntry.status == 'posted',
                        JournalEntry.entry_date <= datetime.strptime(as_of_date, '%Y-%m-%d').date()
                    )
                )
            )

        return query.group_by(ChartOfAccount.id).order_by(ChartOfAccount.code).all()

    # 资产
    asset_data = get_account_balances('asset')
    asset_items = []
    total_assets = Decimal('0')
    for row in asset_data:
        balance = Decimal(str(row.debit)) - Decimal(str(row.credit))
        if balance != 0:
            asset_items.append({
                'code': row.code,
                'name': row.name,
                'name_cn': row.name_cn,
                'amount': balance
            })
            total_assets += balance

    # 负债
    liability_data = get_account_balances('liability')
    liability_items = []
    total_liabilities = Decimal('0')
    for row in liability_data:
        balance = Decimal(str(row.credit)) - Decimal(str(row.debit))
        if balance != 0:
            liability_items.append({
                'code': row.code,
                'name': row.name,
                'name_cn': row.name_cn,
                'amount': balance
            })
            total_liabilities += balance

    # 权益
    equity_data = get_account_balances('equity')
    equity_items = []
    total_equity = Decimal('0')
    for row in equity_data:
        balance = Decimal(str(row.credit)) - Decimal(str(row.debit))
        if balance != 0:
            equity_items.append({
                'code': row.code,
                'name': row.name,
                'name_cn': row.name_cn,
                'amount': balance
            })
            total_equity += balance

    # 计算本期利润（收入-费用）
    income_query = db.session.query(
        func.coalesce(func.sum(JournalEntryLine.credit - JournalEntryLine.debit), 0)
    ).join(JournalEntry).join(ChartOfAccount).filter(
        JournalEntry.status == 'posted',
        ChartOfAccount.account_type == 'income'
    )

    expense_query = db.session.query(
        func.coalesce(func.sum(JournalEntryLine.debit - JournalEntryLine.credit), 0)
    ).join(JournalEntry).join(ChartOfAccount).filter(
        JournalEntry.status == 'posted',
        ChartOfAccount.account_type == 'expense'
    )

    if as_of_date:
        income_query = income_query.filter(JournalEntry.entry_date <= datetime.strptime(as_of_date, '%Y-%m-%d').date())
        expense_query = expense_query.filter(JournalEntry.entry_date <= datetime.strptime(as_of_date, '%Y-%m-%d').date())

    total_income = Decimal(str(income_query.scalar() or 0))
    total_expense = Decimal(str(expense_query.scalar() or 0))
    retained_earnings = total_income - total_expense

    if retained_earnings != 0:
        equity_items.append({
            'code': 'RE',
            'name': 'Retained Earnings (Current)',
            'name_cn': '本期留存收益',
            'amount': retained_earnings
        })
        total_equity += retained_earnings

    is_balanced = abs(total_assets - (total_liabilities + total_equity)) < Decimal('0.01')

    return render_template('finance/ledger/report_balance_sheet.html',
                           asset_items=asset_items,
                           liability_items=liability_items,
                           equity_items=equity_items,
                           total_assets=total_assets,
                           total_liabilities=total_liabilities,
                           total_equity=total_equity,
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
