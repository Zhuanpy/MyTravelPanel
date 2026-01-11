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
    # 获取筛选参数
    supplier_id = request.args.get('supplier_id', type=int)
    payment_source = request.args.get('payment_source', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    keyword = request.args.get('keyword', '')

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 构建查询
    query = SupplierPayment.query

    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)
    if payment_source:
        query = query.filter_by(payment_source=payment_source)
    if start_date:
        query = query.filter(SupplierPayment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(SupplierPayment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if keyword:
        query = query.filter(SupplierPayment.payment_no.ilike(f'%{keyword}%'))

    # 排序并分页
    query = query.order_by(SupplierPayment.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    payments = pagination.items

    # 获取供应商列表（用于筛选）
    suppliers = CustomerCompany.query.filter(
        CustomerCompany.is_supplier == True,
        CustomerCompany.status == 'active'
    ).order_by(CustomerCompany.company_name).all()

    # 计算汇总
    total_amount = sum(float(p.total_amount) for p in payments)
    total_prepayment = sum(float(p.prepayment_amount or 0) for p in payments)

    return render_template('business/projects/payment/list.html',
                           payments=payments,
                           pagination=pagination,
                           suppliers=suppliers,
                           total_amount=total_amount,
                           total_prepayment=total_prepayment,
                           current_filters={
                               'supplier_id': supplier_id,
                               'payment_source': payment_source,
                               'start_date': start_date,
                               'end_date': end_date,
                               'keyword': keyword
                           })


@project_payment.route('/<int:payment_id>')
@login_required
@staff_only
def payment_detail(payment_id):
    """付款记录详情"""
    payment = SupplierPayment.query.get_or_404(payment_id)

    # 获取关联的 EO 列表
    eos = ProjectEO.query.filter_by(payment_record_id=payment_id).order_by(ProjectEO.id).all()

    return render_template('business/projects/payment/detail.html',
                           payment=payment,
                           eos=eos)


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
