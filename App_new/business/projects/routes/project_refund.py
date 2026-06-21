# -*- coding: utf-8 -*-
"""项目退款凭证路由（项目级别，含多条 REF 明细）

提供退款记录的创建、打印（英文退款确认单）和删除。
一次退款可勾选多个 REF，生成一张包含多条明细的凭证。
仅生成面向客户的退款凭证，不自动冲减收款或影响结算状态。
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from datetime import datetime

from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.invoice import ProjectInvoice
from App_new.business.projects.models.refund import ProjectRefund, ProjectRefundItem
from App_new.exts import db, csrf
from App_new.utils.decorators import staff_only

project_refund = Blueprint('project_refund', __name__)

# 个人/现金类客户的公司名（这类客户退款退给个人，而非公司）
_INDIVIDUAL_COMPANY_NAMES = ('个人', 'cash', '现金', 'cash sales')


def customer_display_name(header):
    """退款收款方显示名：
    - 公司客户 → 退给公司名
    - 个人 / CASH / cash sales → 退给个人（项目联系人，其次领队）
    """
    if header and header.company:
        cname = (header.company.company_name or '').strip()
        if cname and cname.lower() not in _INDIVIDUAL_COMPANY_NAMES:
            return cname
    if header:
        return (header.contact or getattr(header, 'leader_name', None) or '个人')
    return ''


def _build_invoice_rows(header, current_refund=None):
    """构建退款表单的发票行：原金额、已退（可排除当前退款）、可退余额，以及当前退款已选信息。

    编辑场景传入 current_refund：
    - 已退款统计排除本笔退款，避免重复计算
    - 标记该发票是否被本笔退款选中及其金额
    """
    exclude_id = current_refund.id if current_refund else None
    # 本笔退款各发票已选金额
    selected_map = {}
    if current_refund:
        for it in current_refund.items:
            selected_map[it.invoice_id] = float(it.amount or 0)

    invoices = ProjectInvoice.query.filter_by(header_id=header.id).filter(
        ProjectInvoice.status != 'cancelled'
    ).order_by(ProjectInvoice.invoice_date.asc()).all()

    rows = []
    for inv in invoices:
        amount = float(inv.amount or 0)
        refunded = ProjectRefundItem.get_invoice_refunded(inv.id, exclude_refund_id=exclude_id)
        remaining = round(amount - refunded, 2)
        is_selected = inv.id in selected_map
        selected_amount = selected_map.get(inv.id, 0.0)
        rows.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'invoice_date': inv.invoice_date.strftime('%Y-%m-%d') if inv.invoice_date else '',
            'currency': inv.currency or header.currency or 'SGD',
            'amount': amount,
            'paid_amount': float(inv.paid_amount or 0),
            'refunded': refunded,
            # 编辑时该发票可退余额需把本笔已选金额加回（本笔金额不算"已退占用"）
            'remaining': max(0.0, round(remaining, 2)),
            'selected': is_selected,
            'selected_amount': selected_amount,
        })
    return rows


@project_refund.route('/header/<int:header_id>')
@login_required
@staff_only
def header_refunds(header_id):
    """项目级退款管理：列出本项目所有退款记录"""
    header = ProjectHeader.query.get_or_404(header_id)
    refunds = ProjectRefund.query.filter_by(header_id=header_id).order_by(ProjectRefund.created_at.desc()).all()
    total_refund = sum(float(r.amount or 0) for r in refunds if r.status == 'confirmed')
    return render_template('business/projects/project_refund/header_refunds.html',
                           header=header, refunds=refunds, total_refund=total_refund)


@project_refund.route('/list')
@login_required
@staff_only
def refund_list():
    """全部退款列表（跨项目）：支持关键词搜索、状态/货币/日期筛选与分页。"""
    from sqlalchemy import and_, or_, desc as sa_desc, func
    from App_new.business.projects.models.project import CustomerCompany

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    status = (request.args.get('status') or '').strip()
    currency = (request.args.get('currency') or '').strip()
    start_date = (request.args.get('start_date') or '').strip()
    end_date = (request.args.get('end_date') or '').strip()
    keyword = (request.args.get('keyword') or '').strip()

    base = db.session.query(
        ProjectRefund,
        ProjectHeader.hid.label('project_hid'),
        ProjectHeader.desc.label('project_name'),
        CustomerCompany.company_name.label('company_name'),
    ).join(
        ProjectHeader, ProjectRefund.header_id == ProjectHeader.id, isouter=True
    ).join(
        CustomerCompany, ProjectHeader.company_id == CustomerCompany.id, isouter=True
    )

    filters = []
    if status:
        filters.append(ProjectRefund.status == status)
    if currency:
        filters.append(ProjectRefund.currency == currency)
    if start_date:
        try:
            filters.append(ProjectRefund.refund_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        except ValueError:
            pass
    if end_date:
        try:
            filters.append(ProjectRefund.refund_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        except ValueError:
            pass
    if keyword:
        kw = f'%{keyword}%'
        filters.append(or_(
            ProjectRefund.refund_number.ilike(kw),
            ProjectRefund.payee_name.ilike(kw),
            ProjectRefund.reason.ilike(kw),
            ProjectHeader.hid.ilike(kw),
            ProjectHeader.desc.ilike(kw),
            CustomerCompany.company_name.ilike(kw),
        ))

    if filters:
        base = base.filter(and_(*filters))

    base = base.order_by(sa_desc(ProjectRefund.refund_date), sa_desc(ProjectRefund.id))
    pagination = base.paginate(page=page, per_page=per_page, error_out=False)

    refunds = [{
        'refund': r,
        'project_hid': project_hid,
        'project_name': project_name,
        'company_name': comp_name,
    } for r, project_hid, project_name, comp_name in pagination.items]

    # 当前筛选条件下「已确认」退款按货币汇总
    totals_q = db.session.query(
        ProjectRefund.currency, func.sum(ProjectRefund.amount)
    ).join(
        ProjectHeader, ProjectRefund.header_id == ProjectHeader.id, isouter=True
    ).join(
        CustomerCompany, ProjectHeader.company_id == CustomerCompany.id, isouter=True
    ).filter(and_(*(filters + [ProjectRefund.status == 'confirmed']))).group_by(ProjectRefund.currency)
    totals = [(cur or 'SGD', float(amt or 0)) for cur, amt in totals_q.all() if (amt or 0)]

    # 货币下拉选项（去重）
    currencies = [c[0] for c in db.session.query(ProjectRefund.currency)
                  .filter(ProjectRefund.currency.isnot(None))
                  .distinct().order_by(ProjectRefund.currency).all()]

    return render_template('business/projects/project_refund/refund_list.html',
                           refunds=refunds, pagination=pagination, totals=totals,
                           currencies=currencies,
                           filters={'status': status, 'currency': currency,
                                    'start_date': start_date, 'end_date': end_date,
                                    'keyword': keyword})


@project_refund.route('/create/<int:header_id>', methods=['GET', 'POST'])
@login_required
@staff_only
def create_refund(header_id):
    """创建项目级退款记录（勾选多张发票退款），提交后跳转到打印页"""
    header = ProjectHeader.query.get_or_404(header_id)

    if request.method == 'POST':
        try:
            # 被勾选的发票 id 列表
            selected_invoice_ids = request.form.getlist('invoice_ids')
            if not selected_invoice_ids:
                flash('请至少勾选一张需要退款的发票', 'warning')
                return redirect(url_for('business_projects.project_refund.create_refund', header_id=header_id))

            refund_date_str = (request.form.get('refund_date') or '').strip()
            refund_date = (datetime.strptime(refund_date_str, '%Y-%m-%d').date()
                           if refund_date_str else datetime.now().date())

            refund = ProjectRefund(
                refund_number=ProjectRefund.generate_refund_number(),
                header_id=header.id,
                amount=0,
                currency=(request.form.get('currency') or header.currency or 'SGD').strip(),
                refund_method=request.form.get('refund_method') or 'bank_transfer',
                refund_date=refund_date,
                payee_name=(request.form.get('payee_name') or '').strip() or None,
                payee_contact=(request.form.get('payee_contact') or '').strip() or None,
                reason=(request.form.get('reason') or '').strip() or None,
                remarks=(request.form.get('remarks') or '').strip() or None,
                status='confirmed',
                created_by=current_user.username if current_user.is_authenticated else None,
            )
            db.session.add(refund)
            db.session.flush()  # 获取 refund.id

            total = 0.0
            for iid in selected_invoice_ids:
                invoice = ProjectInvoice.query.get(int(iid))
                # 安全检查：发票必须属于本项目
                if not invoice or invoice.header_id != header.id:
                    continue
                amount_str = (request.form.get(f'amount_{iid}') or '').strip()
                try:
                    amount = float(amount_str) if amount_str else 0.0
                except ValueError:
                    amount = 0.0
                # 允许 0（表示该发票不可退款，仍需在凭证中列示）；不接受负数
                if amount < 0:
                    amount = 0.0
                total += amount
                item = ProjectRefundItem(
                    refund_id=refund.id,
                    invoice_id=invoice.id,
                    amount=amount,
                )
                db.session.add(item)

            if not refund.items:
                db.session.rollback()
                flash('未能识别任何有效的发票明细', 'warning')
                return redirect(url_for('business_projects.project_refund.create_refund', header_id=header_id))

            refund.amount = total
            db.session.commit()

            return redirect(url_for('business_projects.project_refund.print_refund', refund_id=refund.id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建退款记录失败：{str(e)}', 'error')

    # GET：构建可选发票列表（含原金额、已退、可退余额）
    invoice_rows = _build_invoice_rows(header)
    defaults = {
        'refund_number': ProjectRefund.generate_refund_number(),
        'currency': header.currency or 'SGD',
        'refund_date': datetime.now().date().strftime('%Y-%m-%d'),
        # 收款方按规则自动取值（公司→公司名；个人/现金→联系人），留空即用此默认值
        'payee_auto': customer_display_name(header),
    }

    return render_template('business/projects/project_refund/create_refund.html',
                           header=header, invoice_rows=invoice_rows, defaults=defaults,
                           refund=None,
                           form_action=url_for('business_projects.project_refund.create_refund', header_id=header.id))


@project_refund.route('/<int:refund_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_refund(refund_id):
    """编辑退款记录（项目级，按发票）"""
    refund = ProjectRefund.query.get_or_404(refund_id)
    header = refund.header

    if request.method == 'POST':
        try:
            selected_invoice_ids = request.form.getlist('invoice_ids')
            if not selected_invoice_ids:
                flash('请至少勾选一张需要退款的发票', 'warning')
                return redirect(url_for('business_projects.project_refund.edit_refund', refund_id=refund_id))

            refund_date_str = (request.form.get('refund_date') or '').strip()
            if refund_date_str:
                refund.refund_date = datetime.strptime(refund_date_str, '%Y-%m-%d').date()

            refund.currency = (request.form.get('currency') or header.currency or 'SGD').strip()
            refund.refund_method = request.form.get('refund_method') or 'bank_transfer'
            refund.payee_name = (request.form.get('payee_name') or '').strip() or None
            refund.payee_contact = (request.form.get('payee_contact') or '').strip() or None
            refund.reason = (request.form.get('reason') or '').strip() or None
            refund.remarks = (request.form.get('remarks') or '').strip() or None

            # 重建明细：先删后增
            for it in list(refund.items):
                db.session.delete(it)
            db.session.flush()

            total = 0.0
            for iid in selected_invoice_ids:
                invoice = ProjectInvoice.query.get(int(iid))
                if not invoice or invoice.header_id != header.id:
                    continue
                amount_str = (request.form.get(f'amount_{iid}') or '').strip()
                try:
                    amount = float(amount_str) if amount_str else 0.0
                except ValueError:
                    amount = 0.0
                # 允许 0（表示该发票不可退款，仍需在凭证中列示）；不接受负数
                if amount < 0:
                    amount = 0.0
                total += amount
                db.session.add(ProjectRefundItem(
                    refund_id=refund.id,
                    invoice_id=invoice.id,
                    amount=amount,
                ))

            db.session.flush()
            if not refund.items:
                db.session.rollback()
                flash('未能识别任何有效的发票明细', 'warning')
                return redirect(url_for('business_projects.project_refund.edit_refund', refund_id=refund_id))

            refund.amount = total
            db.session.commit()

            return redirect(url_for('business_projects.project_refund.print_refund', refund_id=refund.id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新退款记录失败：{str(e)}', 'error')

    # GET：回填
    invoice_rows = _build_invoice_rows(header, current_refund=refund)
    defaults = {
        'refund_number': refund.refund_number,
        'currency': refund.currency or header.currency or 'SGD',
        'refund_date': refund.refund_date.strftime('%Y-%m-%d') if refund.refund_date else '',
        'payee_auto': customer_display_name(header),
    }

    return render_template('business/projects/project_refund/create_refund.html',
                           header=header, invoice_rows=invoice_rows, defaults=defaults,
                           refund=refund,
                           form_action=url_for('business_projects.project_refund.edit_refund', refund_id=refund.id))


def _invoice_description(invoice):
    """构建发票描述：优先关联 REF 描述，其次 JSON 明细，再次发票明细表，最后备注"""
    if not invoice:
        return ''
    # 1) 关联 REF 的描述
    try:
        descs = [(r.description or r.detailed_description) for r in invoice.related_refs
                 if (r.description or r.detailed_description)]
        if descs:
            return ', '.join(descs)
    except Exception:
        pass
    # 2) JSON 明细 items_list（CSV 导入等）
    try:
        descs = [it.get('description') for it in invoice.items_list if it.get('description')]
        if descs:
            return ', '.join(descs)
    except Exception:
        pass
    # 3) 发票明细表 InvoiceItem
    try:
        descs = [((it.ref.description if it.ref else None) or it.description) for it in invoice.items]
        descs = [d for d in descs if d]
        if descs:
            return ', '.join(descs)
    except Exception:
        pass
    return invoice.remarks or ''


@project_refund.route('/<int:refund_id>/print')
@login_required
@staff_only
def print_refund(refund_id):
    """打印英文退款确认单（Refund Confirmation），含多条明细"""
    refund = ProjectRefund.query.get_or_404(refund_id)
    header = refund.header
    # 收款方按规则自动取值：公司客户→公司名；个人/现金/cash sales→联系人。
    # 仅当人工显式填写了与联系人不同的收款人时才用人工值（覆盖）。
    auto_name = customer_display_name(header)
    contact = (header.contact if header else '') or ''
    payee = (refund.payee_name or '').strip()
    payee_display = payee if (payee and payee != contact) else auto_name
    # 每条明细对应发票的描述
    descriptions = {item.id: _invoice_description(item.invoice) for item in refund.items}
    return render_template('business/projects/project_refund/print_refund.html',
                           refund=refund, header=header, payee_display=payee_display,
                           descriptions=descriptions)


@project_refund.route('/<int:refund_id>/delete', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_refund(refund_id):
    """删除退款记录（连同明细）"""
    try:
        refund = ProjectRefund.query.get_or_404(refund_id)
        header_id = refund.header_id
        db.session.delete(refund)
        db.session.commit()
        return jsonify({'success': True, 'message': '退款记录已删除', 'header_id': header_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500
