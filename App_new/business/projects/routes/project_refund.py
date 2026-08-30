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


def _ref_suppliers(header):
    """本项目 REF 上出现过的供应商（去重）

    退款要跟的供应商基本就是 REF 上那家（航司/地接/酒店），
    从这里带出来免得手输错名字——supplier_name 是自由文本，
    敲错了跟踪状态就对不上。附带 REF 编号方便一眼认出是哪一单。
    """
    from App_new.business.projects.models.ref import ProjectRef

    grouped = {}
    refs = ProjectRef.query.filter_by(header_id=header.id).order_by(ProjectRef.id).all()
    for r in refs:
        supplier = r.supplier
        if not supplier or not supplier.company_name:
            continue
        grouped.setdefault(supplier.company_name, []).append(r.ref_number or '')
    return [
        {'name': name, 'refs': ', '.join(x for x in nums if x)}
        for name, nums in sorted(grouped.items())
    ]

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


def _parse_date(value):
    """解析 YYYY-MM-DD 字符串，无效返回 None"""
    value = (value or '').strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_amount(value):
    """解析金额，无效或负数返回 0"""
    try:
        amount = float((value or '').strip() or 0)
    except (ValueError, AttributeError):
        return 0.0
    return amount if amount > 0 else 0.0


def _apply_tracking_fields(refund, form):
    """从表单写入两条跟踪线（供应商是否已退款给我们 / 是否已退给客户）"""
    supplier_status = (form.get('supplier_refund_status') or 'pending').strip()
    if supplier_status not in ('pending', 'partial', 'received', 'na'):
        supplier_status = 'pending'
    customer_status = (form.get('customer_refund_status') or 'pending').strip()
    if customer_status not in ('pending', 'partial', 'paid'):
        customer_status = 'pending'

    refund.supplier_name = (form.get('supplier_name') or '').strip() or None
    refund.supplier_refund_status = supplier_status
    # 预计金额由发票明细汇总（见 _collect_refund_items），这里只处理实收
    refund.supplier_refund_amount = _parse_amount(form.get('supplier_refund_amount'))
    refund.supplier_refund_date = _parse_date(form.get('supplier_refund_date'))
    refund.supplier_refund_remarks = (form.get('supplier_refund_remarks') or '').strip() or None

    # 「扣款」两个字段已从表单去掉：我方扣款必然等于「预计退回 − 预计退客户」，
    # 手填只会和自动算出来的手续费对不上。列暂时保留（旧数据还在），但不再写入。
    refund.customer_refund_status = customer_status
    refund.customer_refund_amount = _parse_amount(form.get('customer_refund_amount'))
    refund.customer_refund_date = _parse_date(form.get('customer_refund_date'))
    refund.customer_refund_remarks = (form.get('customer_refund_remarks') or '').strip() or None



def _collect_refund_items(header, form, refund_id):
    """按勾选的发票解析两侧金额，返回 (items, 客户侧合计, 供应商侧合计)

    每张发票两个金额：
    - amount_<id>           本次预计退回客户（决定该发票的已退款/可退余额）
    - supplier_amount_<id>  本次预计供应商退回

    跟踪区的「预计退回 / 预计退客户」由这里汇总得出，不再让人手填两遍。
    """
    def _num(key):
        raw = (form.get(key) or '').strip()
        try:
            value = float(raw) if raw else 0.0
        except ValueError:
            value = 0.0
        # 允许 0（该发票不可退但仍列示在凭证上）；不接受负数
        return value if value > 0 else 0.0

    items, customer_total, supplier_total = [], 0.0, 0.0
    for iid in form.getlist('invoice_ids'):
        invoice = ProjectInvoice.query.get(int(iid))
        # 安全检查：发票必须属于本项目
        if not invoice or invoice.header_id != header.id:
            continue
        amount = _num(f'amount_{iid}')
        supplier_amount = _num(f'supplier_amount_{iid}')
        customer_total += amount
        supplier_total += supplier_amount
        items.append(ProjectRefundItem(
            refund_id=refund_id,
            invoice_id=invoice.id,
            amount=amount,
            supplier_expected_amount=supplier_amount,
        ))
    return items, customer_total, supplier_total


def _build_invoice_rows(header, current_refund=None):
    """构建退款表单的发票行：原金额、已退（可排除当前退款）、可退余额，以及当前退款已选信息。

    编辑场景传入 current_refund：
    - 已退款统计排除本笔退款，避免重复计算
    - 标记该发票是否被本笔退款选中及其金额
    """
    exclude_id = current_refund.id if current_refund else None
    # 本笔退款各发票已选金额
    selected_map = {}
    selected_supplier_map = {}
    if current_refund:
        for it in current_refund.items:
            selected_map[it.invoice_id] = float(it.amount or 0)
            selected_supplier_map[it.invoice_id] = float(it.supplier_expected_amount or 0)

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
            'selected_supplier_amount': selected_supplier_map.get(inv.id, 0.0),
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
    supplier_status = (request.args.get('supplier_status') or '').strip()
    customer_status = (request.args.get('customer_status') or '').strip()

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
    if supplier_status:
        filters.append(ProjectRefund.supplier_refund_status == supplier_status)
    if customer_status:
        filters.append(ProjectRefund.customer_refund_status == customer_status)
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

    def _pending_stat(*extra_filters):
        """当前筛选条件下某种待办的笔数与金额（仅统计已确认退款）"""
        q = db.session.query(
            func.count(ProjectRefund.id), func.sum(ProjectRefund.amount)
        ).join(
            ProjectHeader, ProjectRefund.header_id == ProjectHeader.id, isouter=True
        ).join(
            CustomerCompany, ProjectHeader.company_id == CustomerCompany.id, isouter=True
        ).filter(and_(*(filters + [ProjectRefund.status == 'confirmed'] + list(extra_filters))))
        cnt, amt = q.one()
        return {'count': int(cnt or 0), 'amount': float(amt or 0)}

    # 待办统计：供应商还没退给我们的 / 还没退给客户的
    stats = {
        'supplier_pending': _pending_stat(
            ProjectRefund.supplier_refund_status.in_(['pending', 'partial'])),
        'customer_pending': _pending_stat(
            ProjectRefund.customer_refund_status.in_(['pending', 'partial'])),
    }

    # 货币下拉选项（去重）
    currencies = [c[0] for c in db.session.query(ProjectRefund.currency)
                  .filter(ProjectRefund.currency.isnot(None))
                  .distinct().order_by(ProjectRefund.currency).all()]

    return render_template('business/projects/project_refund/refund_list.html',
                           refunds=refunds, pagination=pagination, totals=totals,
                           currencies=currencies, stats=stats,
                           filters={'status': status, 'currency': currency,
                                    'start_date': start_date, 'end_date': end_date,
                                    'keyword': keyword,
                                    'supplier_status': supplier_status,
                                    'customer_status': customer_status})


@project_refund.route('/create/<int:header_id>', methods=['GET', 'POST'])
@login_required
@staff_only
def create_refund(header_id):
    """创建项目级退款记录（勾选多张发票退款），提交后跳转到打印页"""
    header = ProjectHeader.query.get_or_404(header_id)

    # 已结算的项目不能再开退款单（会改变余额，与已发出的分成对不上）
    from App_new.utils.permissions import block_if_settled
    blocked = block_if_settled(header)
    if blocked:
        flash(blocked, 'warning')
        return redirect(url_for('business_projects.project_refund.header_refunds', header_id=header_id))

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
            # 两条跟踪线：供应商退款到账 / 已退给客户
            _apply_tracking_fields(refund, request.form)
            db.session.add(refund)
            db.session.flush()  # 获取 refund.id

            items, total, supplier_total = _collect_refund_items(header, request.form, refund.id)
            for item in items:
                db.session.add(item)
            db.session.flush()

            # 预计金额由明细汇总，不从表单读
            refund.customer_expected_amount = total
            refund.supplier_expected_amount = supplier_total

            if not refund.items:
                db.session.rollback()
                flash('未能识别任何有效的发票明细', 'warning')
                return redirect(url_for('business_projects.project_refund.create_refund', header_id=header_id))

            refund.amount = total
            db.session.commit()

            # 保存后回退款管理页，打印在那边按行操作（表单上不再重复提供打印入口）
            flash(f'退款记录 {refund.refund_number} 已保存', 'success')
            return redirect(url_for('business_projects.project_refund.header_refunds', header_id=header.id))

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
                           refund=None, ref_suppliers=_ref_suppliers(header),
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
            # 两条跟踪线：供应商退款到账 / 已退给客户
            _apply_tracking_fields(refund, request.form)

            # 重建明细：先删后增
            for it in list(refund.items):
                db.session.delete(it)
            db.session.flush()

            items, total, supplier_total = _collect_refund_items(header, request.form, refund.id)
            for item in items:
                db.session.add(item)

            db.session.flush()

            # 预计金额由明细汇总，不从表单读
            refund.customer_expected_amount = total
            refund.supplier_expected_amount = supplier_total

            if not refund.items:
                db.session.rollback()
                flash('未能识别任何有效的发票明细', 'warning')
                return redirect(url_for('business_projects.project_refund.edit_refund', refund_id=refund_id))

            refund.amount = total
            db.session.commit()

            # 保存后回退款管理页，打印在那边按行操作（表单上不再重复提供打印入口）
            flash(f'退款记录 {refund.refund_number} 已保存', 'success')
            return redirect(url_for('business_projects.project_refund.header_refunds', header_id=header.id))

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
                           refund=refund, ref_suppliers=_ref_suppliers(header),
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


@project_refund.route('/<int:refund_id>/tracking', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def update_tracking(refund_id):
    """快捷更新退款跟踪状态（供应商是否已退款给我们 / 是否已退给客户）

    接受 JSON 或表单，只更新传入的字段，便于列表页弹窗与 API 调用：
    supplier_name / supplier_refund_status / supplier_refund_amount /
    supplier_refund_date / supplier_refund_remarks，以及对应的 customer_* 字段。
    """
    try:
        refund = ProjectRefund.query.get_or_404(refund_id)
        data = request.get_json(silent=True) or request.form

        if 'supplier_name' in data:
            refund.supplier_name = (data.get('supplier_name') or '').strip() or None
        if 'supplier_refund_status' in data:
            value = (data.get('supplier_refund_status') or '').strip()
            if value not in ('pending', 'partial', 'received', 'na'):
                return jsonify({'success': False, 'message': '无效的供应商退款状态'}), 400
            refund.supplier_refund_status = value
        if 'supplier_refund_amount' in data:
            refund.supplier_refund_amount = _parse_amount(str(data.get('supplier_refund_amount') or ''))
        if 'supplier_refund_date' in data:
            refund.supplier_refund_date = _parse_date(str(data.get('supplier_refund_date') or ''))
        if 'supplier_refund_remarks' in data:
            refund.supplier_refund_remarks = (data.get('supplier_refund_remarks') or '').strip() or None

        if 'customer_refund_status' in data:
            value = (data.get('customer_refund_status') or '').strip()
            if value not in ('pending', 'partial', 'paid'):
                return jsonify({'success': False, 'message': '无效的退客户状态'}), 400
            refund.customer_refund_status = value
        if 'customer_refund_amount' in data:
            refund.customer_refund_amount = _parse_amount(str(data.get('customer_refund_amount') or ''))
        if 'customer_refund_date' in data:
            refund.customer_refund_date = _parse_date(str(data.get('customer_refund_date') or ''))
        if 'customer_refund_remarks' in data:
            refund.customer_refund_remarks = (data.get('customer_refund_remarks') or '').strip() or None

        db.session.commit()
        return jsonify({'success': True, 'message': '退款跟踪状态已更新', 'refund': refund.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


@project_refund.route('/<int:refund_id>/create-adjustment', methods=['POST'])
@login_required
@staff_only
def create_adjustment(refund_id):
    """由退款单生成「退款调整单」，把手续费做进项目利润

    退款单本身只是凭证，不进账。真正让「供应商退回 − 退给客户」这笔差额进到
    利润和分成里的，是一条 refund 类型的 REF：
        售价 = 供应商退回给我们的钱
        成本 = 我们退给客户的钱
        利润 = 两者之差 = 手续费收入

    原来这一串（判断结不结算 → 建单 → 建 REF 且类型必须选对 → 建 EO）全靠人记，
    漏一步就静默卡住结算，而且界面上根本选不到 refund 类型。

    金额口径：优先用实际发生额，实际为 0 时回落到预计额（钱还没到账时先占位）。
    """
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.shared.models.business_types import BusinessType

    refund = ProjectRefund.query.get_or_404(refund_id)
    header = refund.header

    if refund.adjustment_ref_id:
        existing = ProjectRef.query.get(refund.adjustment_ref_id)
        if existing:
            return jsonify({
                'success': False,
                'message': f'该退款单已生成调整单 {existing.ref_number}，不能重复生成',
                'adjustment_ref_id': existing.id,
                'adjustment_header_id': refund.adjustment_header_id,
            }), 400
        # 调整单被删过，允许重新生成
        refund.adjustment_ref_id = None
        refund.adjustment_header_id = None

    refund_type = BusinessType.query.filter_by(code='refund').first()
    if not refund_type:
        return jsonify({
            'success': False,
            'message': '缺少「退款调整」业务类型，请先执行 scripts/20260829_refund_settlement_support.py'
        }), 400

    # 金额：实际优先，回落到预计
    supplier_in = float(refund.supplier_refund_amount or 0) or float(refund.supplier_expected_amount or 0)
    customer_out = float(refund.customer_refund_amount or 0) or float(refund.customer_expected_amount or 0)
    basis = '实际' if float(refund.supplier_refund_amount or 0) or float(refund.customer_refund_amount or 0) else '预计'

    if supplier_in <= 0 and customer_out <= 0:
        return jsonify({
            'success': False,
            'message': '供应商退回和退给客户的金额都是 0，无法生成调整单。请先填写预计或实际金额。'
        }), 400

    try:
        # 已结算的项目不能再改，另开一张单并挂回主单；未结算的直接加在本项目上
        if header.is_settled:
            target = ProjectHeader(
                hid=ProjectHeader.generate_hid(),
                desc=f'退款调整 {refund.refund_number}（{header.hid}）',
                related_header_id=header.id,
                company_id=header.company_id,
                currency=header.currency or 'SGD',
                status='active',
                contact=header.contact,
                staff_id=header.staff_id,
                # 分成要分给原单的人，不是建单的人
                operator_ids=header.operator_ids,
                operator_names=header.operator_names,
                salesperson_ids=header.salesperson_ids,
                salesperson_names=header.salesperson_names,
                remarks=f'由退款单 {refund.refund_number} 自动生成；原单 {header.hid} 已结算，故另开调整单',
            )
            db.session.add(target)
            db.session.flush()
            created_header = True
        else:
            target = header
            created_header = False

        ref = ProjectRef(
            header_id=target.id,
            ref_number=ProjectRef.generate_ref_number(),
            ref_type_id=refund_type.id,
            description=f'退款调整 {refund.refund_number}',
            detailed_description=(
                f'退款单 {refund.refund_number}（{basis}金额）\n'
                f'供应商退回 {supplier_in:.2f} - 退给客户 {customer_out:.2f} '
                f'= 手续费 {supplier_in - customer_out:.2f}'
            ),
            selling_price=supplier_in,
            cost_price=customer_out,
            currency=refund.currency or target.currency or 'SGD',
        )
        db.session.add(ref)
        db.session.flush()

        # EO 骨架：复用 project_eo 里的生成逻辑，保证 EO 编号规则单一来源
        # （pay_amount 留空 = 未付款，结算前会被 settle_blockers 提示补上）
        eo = None
        if customer_out > 0:
            from App_new.business.projects.routes.project_eo import _create_or_reactivate_eo
            eo, _ = _create_or_reactivate_eo(ref)

        refund.adjustment_header_id = target.id
        refund.adjustment_ref_id = ref.id
        db.session.commit()

        parts = [f'已生成调整单 {ref.ref_number}（售价 {supplier_in:.2f} / 成本 {customer_out:.2f}，'
                 f'利润 {supplier_in - customer_out:.2f}）']
        if created_header:
            parts.append(f'原单已结算，已另开项目 {target.hid} 并关联回 {header.hid}')
        if eo:
            parts.append(f'已建 EO {eo.eo_number}，请在实际付款后填金额并标记已付')
        parts.append(f'还需记一笔 {supplier_in:.2f} 的收款挂到该 REF，项目才能结算')

        return jsonify({
            'success': True,
            'message': '；'.join(parts),
            'ref_id': ref.id,
            'ref_number': ref.ref_number,
            'header_id': target.id,
            'hid': target.hid,
            'created_header': created_header,
            'eo_number': eo.eo_number if eo else None,
            'basis': basis,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'生成失败：{str(e)}'}), 500


@project_refund.route('/<int:refund_id>/delete', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_refund(refund_id):
    """删除退款记录（连同明细）

    已发生实际收付（供应商已退给我们 / 已退给客户，含部分）的退款不允许删除，
    需先把对应跟踪状态改回「未收到 / 未退款」。
    """
    try:
        refund = ProjectRefund.query.get_or_404(refund_id)
        if not refund.can_delete:
            return jsonify({
                'success': False,
                'message': f'该退款已发生实际收付（{refund.delete_block_reason}），不能删除；'
                           f'如确需删除，请先把对应状态改回「未收到 / 未退款」。'
            }), 400
        header_id = refund.header_id
        db.session.delete(refund)
        db.session.commit()
        return jsonify({'success': True, 'message': '退款记录已删除', 'header_id': header_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500
