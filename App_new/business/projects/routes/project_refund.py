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
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.refund import ProjectRefund, ProjectRefundItem
from App_new.exts import db, csrf
from App_new.utils.decorators import staff_only

project_refund = Blueprint('project_refund', __name__)


def _prefill_flight_info(ref):
    """机票 REF 时，尝试预填原票号和航班信息"""
    ticket_no = ''
    flight_info = ''
    try:
        passengers = ref.flight_passengers
        if passengers:
            tickets = [p.ticket_number for p in passengers if getattr(p, 'ticket_number', None)]
            ticket_no = ', '.join(tickets)
        segments = ref.flight_segments
        if segments:
            seg = segments[0]
            parts = [seg.flight_number, seg.departure_airport, seg.arrival_airport]
            flight_info = ' '.join(p for p in parts if p)
    except Exception:
        pass
    return ticket_no, flight_info


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


@project_refund.route('/create/<int:header_id>', methods=['GET', 'POST'])
@login_required
@staff_only
def create_refund(header_id):
    """创建项目级退款记录（勾选多个 REF），提交后跳转到打印页"""
    header = ProjectHeader.query.get_or_404(header_id)

    if request.method == 'POST':
        try:
            # 被勾选的 REF id 列表
            selected_ref_ids = request.form.getlist('ref_ids')
            if not selected_ref_ids:
                flash('请至少勾选一个需要退款的 REF', 'warning')
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
            for rid in selected_ref_ids:
                ref = ProjectRef.query.get(int(rid))
                # 安全检查：REF 必须属于本项目
                if not ref or ref.header_id != header.id:
                    continue
                amount_str = (request.form.get(f'amount_{rid}') or '').strip()
                try:
                    amount = float(amount_str) if amount_str else 0.0
                except ValueError:
                    amount = 0.0
                total += amount
                item = ProjectRefundItem(
                    refund_id=refund.id,
                    ref_id=ref.id,
                    amount=amount,
                    original_ticket_no=(request.form.get(f'ticket_{rid}') or '').strip() or None,
                    flight_info=(request.form.get(f'flight_{rid}') or '').strip() or None,
                )
                db.session.add(item)

            if not refund.items:
                db.session.rollback()
                flash('未能识别任何有效的 REF 明细', 'warning')
                return redirect(url_for('business_projects.project_refund.create_refund', header_id=header_id))

            refund.amount = total
            db.session.commit()

            return redirect(url_for('business_projects.project_refund.print_refund', refund_id=refund.id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建退款记录失败：{str(e)}', 'error')

    # GET：构建可选 REF 列表并预填默认值
    refs = ProjectRef.query.filter_by(header_id=header_id).all()
    ref_rows = []
    for ref in refs:
        ticket_no, flight_info = _prefill_flight_info(ref)
        ref_rows.append({
            'id': ref.id,
            'ref_number': ref.ref_number,
            'description': ref.description or ref.detailed_description or '',
            'type_name': ref.ref_type.name if ref.ref_type else '',
            'selling_price': float(ref.selling_price) if ref.selling_price else 0,
            'currency': ref.currency or header.currency or 'SGD',
            'ticket_no': ticket_no,
            'flight_info': flight_info,
        })

    defaults = {
        'refund_number': ProjectRefund.generate_refund_number(),
        'currency': header.currency or 'SGD',
        'refund_date': datetime.now().date().strftime('%Y-%m-%d'),
        'payee_name': header.contact or '',
    }

    return render_template('business/projects/project_refund/create_refund.html',
                           header=header, ref_rows=ref_rows, defaults=defaults)


@project_refund.route('/<int:refund_id>/print')
@login_required
@staff_only
def print_refund(refund_id):
    """打印英文退款确认单（Refund Confirmation），含多条明细"""
    refund = ProjectRefund.query.get_or_404(refund_id)
    header = refund.header
    return render_template('business/projects/project_refund/print_refund.html',
                           refund=refund, header=header)


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
