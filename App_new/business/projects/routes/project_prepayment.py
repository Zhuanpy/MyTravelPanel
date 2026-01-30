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
    """预付账款列表页面"""
    from sqlalchemy import func

    # 获取筛选参数
    supplier_id = request.args.get('supplier_id', type=int)
    status = request.args.get('status', '')

    # 获取供应商列表（用于筛选）
    suppliers = CustomerCompany.query.filter(
        CustomerCompany.is_supplier == True,
        CustomerCompany.status == 'active'
    ).order_by(CustomerCompany.company_name).all()

    # 如果没有选择供应商，显示所有账户汇总
    if not supplier_id:
        # 按供应商汇总预付款数据
        summary_data = db.session.query(
            CustomerCompany.id.label('supplier_id'),
            CustomerCompany.company_name,
            func.sum(SupplierPrepayment.amount).label('total_amount'),
            func.sum(SupplierPrepayment.balance_amount).label('total_balance'),
            func.count(SupplierPrepayment.id).label('prepayment_count')
        ).join(
            SupplierPrepayment, CustomerCompany.id == SupplierPrepayment.supplier_id
        ).filter(
            SupplierPrepayment.status.in_(['confirmed', 'partial_used', 'consumed'])
        ).group_by(
            CustomerCompany.id, CustomerCompany.company_name
        ).order_by(func.sum(SupplierPrepayment.balance_amount).desc()).all()

        # 转换为列表
        account_summary = []
        grand_total_amount = 0
        grand_total_balance = 0
        for item in summary_data:
            total_amount = float(item.total_amount or 0)
            total_balance = float(item.total_balance or 0)
            total_used = total_amount - total_balance
            account_summary.append({
                'supplier_id': item.supplier_id,
                'supplier_name': item.company_name,
                'total_amount': total_amount,
                'total_balance': total_balance,
                'total_used': total_used,
                'prepayment_count': item.prepayment_count
            })
            grand_total_amount += total_amount
            grand_total_balance += total_balance

        return render_template('business/projects/prepayment/list.html',
                               prepayments=[],
                               suppliers=suppliers,
                               selected_supplier_id=None,
                               selected_status=status,
                               total_amount=0,
                               total_balance=0,
                               total_used=0,
                               no_supplier_selected=True,
                               pending_eos=[],
                               pending_eo_total=0,
                               account_summary=account_summary,
                               grand_total_amount=grand_total_amount,
                               grand_total_balance=grand_total_balance)

    # 构建查询
    query = SupplierPrepayment.query.filter_by(supplier_id=supplier_id)

    if status:
        query = query.filter_by(status=status)

    # 按编号倒序（最新的显示在最上面）
    prepayments = query.order_by(SupplierPrepayment.prepayment_number.desc()).all()

    # 计算汇总（used_amount 只计算 confirmed 状态的使用记录）
    total_amount = sum(float(p.amount or 0) for p in prepayments)
    total_balance = sum(float(p.balance_amount or 0) for p in prepayments)
    total_used = sum(float(p.used_amount or 0) for p in prepayments)

    # 查询待付款的EO（已创建但尚未付款的EO）
    try:
        # 获取已确认扣减的EO ID（只排除confirmed状态的，pending状态的还需显示）
        confirmed_used_eo_ids = db.session.query(PrepaymentUsage.eo_id).join(
            SupplierPrepayment, PrepaymentUsage.prepayment_id == SupplierPrepayment.id
        ).filter(
            SupplierPrepayment.supplier_id == supplier_id,
            PrepaymentUsage.eo_id.isnot(None),
            PrepaymentUsage.status == 'confirmed'
        ).distinct().all()
        confirmed_used_eo_ids = [eo_id for (eo_id,) in confirmed_used_eo_ids]

        # 查询待付款EO列表：未付款且未确认扣减
        query = db.session.query(ProjectEO).join(
            ProjectRef, ProjectEO.ref_id == ProjectRef.id
        ).filter(
            ProjectRef.supplier_id == supplier_id,
            ProjectEO.status == 'confirmed',
            ProjectEO.is_paid == False
        )
        if confirmed_used_eo_ids:
            query = query.filter(~ProjectEO.id.in_(confirmed_used_eo_ids))
        pending_eos = query.order_by(ProjectEO.created_at.desc()).all()
    except Exception as e:
        print(f"查询待付款EO出错: {e}")
        pending_eos = []

    # 计算待付款总金额（所有显示的EO成本之和）
    pending_eo_total = sum(
        float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else 0
        for eo in pending_eos
    )

    return render_template('business/projects/prepayment/list.html',
                           prepayments=prepayments,
                           suppliers=suppliers,
                           selected_supplier_id=supplier_id,
                           selected_status=status,
                           total_amount=total_amount,
                           total_balance=total_balance,
                           total_used=total_used,
                           no_supplier_selected=False,
                           pending_eos=pending_eos,
                           pending_eo_total=pending_eo_total)


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

        return render_template('business/projects/prepayment/create.html',
                               suppliers=suppliers,
                               bank_accounts=bank_accounts,
                               prepayment_accounts=prepayment_accounts)

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

        flash(f'预付账款 {prepayment_number} 创建成功', 'success')
        return redirect(url_for('business_projects.project_prepayment.prepayment_detail', prepayment_id=prepayment.id))

    except Exception as e:
        db.session.rollback()
        flash(f'创建失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.project_prepayment.create_prepayment'))


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

    return render_template('business/projects/prepayment/detail.html',
                           prepayment=prepayment,
                           usages=usages)


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
@admin_only
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
    prepayments = SupplierPrepayment.query.filter(
        SupplierPrepayment.supplier_id == supplier_id,
        SupplierPrepayment.status.in_(['confirmed', 'partial_used']),
        SupplierPrepayment.balance_amount > 0
    ).order_by(SupplierPrepayment.payment_date.asc()).all()

    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in prepayments],
        'total_balance': sum(float(p.balance_amount) for p in prepayments)
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
