# -*- coding: utf-8 -*-
"""
项目管理Invoice路由模块
包含发票/账单的创建、编辑、查看、删除等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
from App_new.exts import csrf, db
from App_new.business.projects.forms.invoice_forms import ProjectInvoiceForm, InvoicePaymentForm
from App_new.utils.decorators import staff_only, admin_only
from datetime import datetime
import json
import traceback

project_invoice = Blueprint('project_invoice', __name__)


@project_invoice.route('/header/<int:header_id>/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_invoice(header_id):
    """创建发票"""
    header = ProjectHeader.query.get_or_404(header_id)
    form = ProjectInvoiceForm()
    
    # 动态生成REF选择选项
    ref_choices = []
    for ref in header.refs:
        if ref.selling_price and float(ref.selling_price) > 0:
            ref_choices.append((ref.id, f"{ref.ref_number} - {ref.description or ref.detailed_description or '服务'} ({ref.currency or 'SGD'} {float(ref.selling_price):.2f})"))
    
    form.selected_refs.choices = ref_choices if ref_choices else [(0, "暂无可选REF")]
    
    # 预填充发票编号
    invoice_number = ProjectInvoice.generate_invoice_number()
    
    # 预填充客户信息（从项目header获取）
    if request.method == 'GET':
        form.customer_name.data = header.leader_name
        if header.company:
            form.customer_company.data = header.company.company_name
    
    if form.validate_on_submit():
        try:
            # 获取选中的REF
            selected_ref_ids = form.selected_refs.data
            if selected_ref_ids and (len(selected_ref_ids) == 1 and selected_ref_ids[0] == 0):
                selected_ref_ids = []
            
            # 如果是手动选择REF，计算总金额
            if selected_ref_ids:
                total_amount = 0
                for ref_id in selected_ref_ids:
                    ref = ProjectRef.query.get(ref_id)
                    if ref and ref.selling_price:
                        total_amount += float(ref.selling_price)
                # 如果表单没有填写金额，使用计算的总金额
                if not form.amount.data:
                    form.amount.data = total_amount
            
            # 创建发票
            invoice = ProjectInvoice(
                invoice_number=invoice_number,
                header_id=header.id,
                invoice_date=form.invoice_date.data,
                due_date=form.due_date.data,
                amount=form.amount.data,
                currency=form.currency.data,
                invoice_type=form.invoice_type.data,
                customer_name=form.customer_name.data,
                customer_company=form.customer_company.data,
                customer_email=form.customer_email.data,
                customer_phone=form.customer_phone.data,
                customer_address=form.customer_address.data,
                ref_ids=json.dumps(selected_ref_ids) if selected_ref_ids else None,
                remarks=form.remarks.data,
                terms=form.terms.data,
                status='draft',
                created_by=current_user.username if current_user else None
            )
            
            db.session.add(invoice)
            db.session.flush()
            
            # 如果选择了REF，创建发票明细项
            if selected_ref_ids:
                for ref_id in selected_ref_ids:
                    ref = ProjectRef.query.get(ref_id)
                    if ref:
                        item = InvoiceItem(
                            invoice_id=invoice.id,
                            ref_id=ref.id,
                            description=ref.description or ref.detailed_description or '服务',
                            quantity=1,
                            unit_price=ref.selling_price or 0,
                            total_price=ref.selling_price or 0
                        )
                        db.session.add(item)
            
            db.session.commit()
            flash('发票创建成功', 'success')
            return redirect(url_for('business_projects.project_invoice.header_invoices', header_id=header.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    
    # 计算项目总金额（用于参考）
    total_selling = sum(float(ref.selling_price or 0) for ref in header.refs)
    
    return render_template('business/projects/project_invoice/create_invoice.html',
                          form=form,
                          header=header,
                          invoice_number=invoice_number,
                          total_selling=total_selling)


@project_invoice.route('/header/<int:header_id>/invoices')
@login_required
@staff_only
def header_invoices(header_id):
    """查看项目的发票列表"""
    header = ProjectHeader.query.get_or_404(header_id)
    
    # 获取所有发票
    invoices = ProjectInvoice.query.filter_by(header_id=header_id).order_by(ProjectInvoice.created_at.desc()).all()
    
    # 计算统计数据
    total_invoiced = ProjectInvoice.get_header_total_invoiced(header_id)
    total_paid = ProjectInvoice.get_header_total_paid(header_id)
    total_unpaid = total_invoiced - total_paid
    
    # 计算项目总售价（从REF）
    total_selling = sum(float(ref.selling_price or 0) for ref in header.refs)
    
    return render_template('business/projects/project_invoice/header_invoices.html',
                         header=header,
                         invoices=invoices,
                         total_invoiced=total_invoiced,
                         total_paid=total_paid,
                         total_unpaid=total_unpaid,
                         total_selling=total_selling)


@project_invoice.route('/<int:invoice_id>')
@login_required
@staff_only
def invoice_detail(invoice_id):
    """发票详情"""
    invoice = ProjectInvoice.query.get_or_404(invoice_id)
    
    # 获取关联的REF信息
    related_refs = invoice.related_refs
    
    # 获取发票明细
    items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
    
    return render_template('business/projects/project_invoice/invoice_detail.html',
                         invoice=invoice,
                         related_refs=related_refs,
                         items=items)


@project_invoice.route('/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def edit_invoice(invoice_id):
    """编辑发票"""
    invoice = ProjectInvoice.query.get_or_404(invoice_id)
    header = ProjectHeader.query.get_or_404(invoice.header_id)
    form = ProjectInvoiceForm(obj=invoice)
    
    # 动态生成REF选择选项
    ref_choices = []
    for ref in header.refs:
        if ref.selling_price and float(ref.selling_price) > 0:
            ref_choices.append((ref.id, f"{ref.ref_number} - {ref.description or ref.detailed_description or '服务'} ({ref.currency or 'SGD'} {float(ref.selling_price):.2f})"))
    
    form.selected_refs.choices = ref_choices if ref_choices else [(0, "暂无可选REF")]
    
    # 预填充选中的REF
    if request.method == 'GET' and invoice.ref_ids:
        try:
            form.selected_refs.data = json.loads(invoice.ref_ids)
        except (json.JSONDecodeError, TypeError):
            pass
    
    if form.validate_on_submit():
        try:
            # 更新发票信息
            invoice.invoice_date = form.invoice_date.data
            invoice.due_date = form.due_date.data
            invoice.amount = form.amount.data
            invoice.currency = form.currency.data
            invoice.invoice_type = form.invoice_type.data
            invoice.customer_name = form.customer_name.data
            invoice.customer_company = form.customer_company.data
            invoice.customer_email = form.customer_email.data
            invoice.customer_phone = form.customer_phone.data
            invoice.customer_address = form.customer_address.data
            invoice.remarks = form.remarks.data
            invoice.terms = form.terms.data
            
            # 更新关联REF
            selected_ref_ids = form.selected_refs.data
            if selected_ref_ids and (len(selected_ref_ids) == 1 and selected_ref_ids[0] == 0):
                selected_ref_ids = []
            invoice.ref_ids = json.dumps(selected_ref_ids) if selected_ref_ids else None
            
            # 删除旧的发票明细，重新创建
            InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
            
            if selected_ref_ids:
                for ref_id in selected_ref_ids:
                    ref = ProjectRef.query.get(ref_id)
                    if ref:
                        item = InvoiceItem(
                            invoice_id=invoice.id,
                            ref_id=ref.id,
                            description=ref.description or ref.detailed_description or '服务',
                            quantity=1,
                            unit_price=ref.selling_price or 0,
                            total_price=ref.selling_price or 0
                        )
                        db.session.add(item)
            
            db.session.commit()
            flash('发票更新成功', 'success')
            return redirect(url_for('business_projects.project_invoice.invoice_detail', invoice_id=invoice.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    return render_template('business/projects/project_invoice/edit_invoice.html',
                         form=form,
                         invoice=invoice,
                         header=header)


@project_invoice.route('/<int:invoice_id>/delete', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_invoice(invoice_id):
    """删除发票"""
    invoice = ProjectInvoice.query.get_or_404(invoice_id)
    header_id = invoice.header_id
    
    try:
        # 删除发票明细
        InvoiceItem.query.filter_by(invoice_id=invoice_id).delete()
        
        # 删除发票
        db.session.delete(invoice)
        db.session.commit()
        flash('发票删除成功', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
    return redirect(url_for('business_projects.project_invoice.header_invoices', header_id=header_id))


@project_invoice.route('/header/<int:header_id>/quick-create', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def quick_create_invoice(header_id):
    """快速生成发票 - 从模态框提交"""
    try:
        data = request.get_json()
        header = ProjectHeader.query.get_or_404(header_id)
        
        # 获取选中的REF
        refs_data = data.get('refs', [])
        if not refs_data:
            return jsonify({'success': False, 'message': '请至少选择一个REF'})
        
        # 计算总金额
        total_amount = sum(ref.get('total', 0) for ref in refs_data)
        
        # 生成发票编号
        invoice_number = ProjectInvoice.generate_invoice_number()
        
        # 解析发票日期
        invoice_date_str = data.get('invoice_date')
        if invoice_date_str:
            from datetime import datetime
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
        else:
            from datetime import date
            invoice_date = date.today()
        
        # 创建发票
        invoice = ProjectInvoice(
            invoice_number=invoice_number,
            header_id=header_id,
            invoice_date=invoice_date,
            amount=total_amount,
            currency=header.currency or 'SGD',
            invoice_type='full',
            customer_name=header.leader_name or header.contact,
            customer_company=header.company.company_name if header.company else None,
            ref_ids=json.dumps([ref.get('ref_id') for ref in refs_data]),
            remarks=f"Order: {data.get('order_no', '')}, TR: {data.get('tr_no', '')}, Purpose: {data.get('purpose', '')}".strip(', '),
            status='draft',
            created_by=current_user.username if current_user else None
        )
        
        db.session.add(invoice)
        db.session.flush()
        
        # 创建发票明细
        for ref_data in refs_data:
            ref_id = ref_data.get('ref_id')
            if ref_id:
                ref = ProjectRef.query.get(ref_id)
                if ref and ref_data.get('show_on_invoice', True):
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        ref_id=ref.id,
                        description=ref.description or ref.detailed_description or '服务',
                        quantity=1,
                        unit_price=ref_data.get('total', 0),
                        total_price=ref_data.get('total', 0),
                        remarks=f"Gross: {ref_data.get('gross', 0)}, Disc: {ref_data.get('discount', 0)}, Tax: {ref_data.get('tax', 0)}"
                    )
                    db.session.add(item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '发票生成成功',
            'invoice_id': invoice.id,
            'invoice_number': invoice_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@project_invoice.route('/void', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def void_invoice():
    """取消/作废发票"""
    try:
        data = request.get_json()
        header_id = data.get('header_id')
        invoice_number = data.get('invoice_number')
        
        if not invoice_number:
            return jsonify({'success': False, 'message': '请输入发票号'})
        
        # 查找发票
        invoice = ProjectInvoice.query.filter_by(
            invoice_number=invoice_number.strip()
        ).first()
        
        if not invoice:
            return jsonify({'success': False, 'message': f'未找到发票号 {invoice_number}'})
        
        # 检查发票是否属于当前项目（如果指定了header_id）
        if header_id and invoice.header_id != int(header_id):
            return jsonify({'success': False, 'message': '该发票不属于当前项目'})
        
        # 检查发票状态
        if invoice.status == 'cancelled':
            return jsonify({'success': False, 'message': '该发票已经被取消'})
        
        if invoice.status == 'paid':
            return jsonify({'success': False, 'message': '已付款的发票不能取消，请先处理退款'})
        
        # 更新状态为已取消
        invoice.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'发票 {invoice_number} 已取消'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@project_invoice.route('/<int:invoice_id>/send', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def send_invoice(invoice_id):
    """发送发票（更新状态为已发送）"""
    invoice = ProjectInvoice.query.get_or_404(invoice_id)
    
    try:
        invoice.status = 'sent'
        invoice.sent_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '发票已标记为已发送'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'操作失败：{str(e)}'
        }), 500


@project_invoice.route('/<int:invoice_id>/record_payment', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def record_payment(invoice_id):
    """记录发票付款"""
    invoice = ProjectInvoice.query.get_or_404(invoice_id)
    form = InvoicePaymentForm()
    
    if form.validate_on_submit():
        try:
            payment_amount = float(form.payment_amount.data)
            
            # 验证付款金额不能超过未付金额
            if payment_amount > invoice.unpaid_amount:
                flash(f'付款金额不能超过未付金额：{invoice.currency} {invoice.unpaid_amount:.2f}', 'error')
                return render_template('business/projects/project_invoice/record_payment.html',
                                     form=form,
                                     invoice=invoice)
            
            # 更新已付金额
            invoice.paid_amount = float(invoice.paid_amount or 0) + payment_amount
            
            # 记录付款信息到extra_info
            payment_record = {
                'amount': payment_amount,
                'date': form.payment_date.data.isoformat(),
                'method': form.payment_method.data,
                'transaction_id': form.transaction_id.data,
                'remarks': form.remarks.data,
                'recorded_at': datetime.utcnow().isoformat(),
                'recorded_by': current_user.username if current_user else None
            }
            
            extra_info = json.loads(invoice.extra_info) if invoice.extra_info else {}
            if 'payments' not in extra_info:
                extra_info['payments'] = []
            extra_info['payments'].append(payment_record)
            invoice.extra_info = json.dumps(extra_info)
            
            # 更新发票状态
            invoice.update_payment_status()
            
            db.session.commit()
            flash('付款记录成功', 'success')
            return redirect(url_for('business_projects.project_invoice.invoice_detail', invoice_id=invoice.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'记录失败：{str(e)}', 'error')
    
    return render_template('business/projects/project_invoice/record_payment.html',
                         form=form,
                         invoice=invoice)


@project_invoice.route('/<int:invoice_id>/cancel', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def cancel_invoice(invoice_id):
    """取消发票"""
    invoice = ProjectInvoice.query.get_or_404(invoice_id)
    
    try:
        invoice.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '发票已取消'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'操作失败：{str(e)}'
        }), 500


@project_invoice.route('/list', methods=['GET'])
@login_required
@staff_only
def invoice_list():
    """发票列表 - 支持筛选、搜索和分页"""
    try:
        from sqlalchemy import and_, or_, desc, asc
        from datetime import timedelta, date
        
        # 获取筛选参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status = request.args.get('status', '').strip()
        invoice_type = request.args.get('invoice_type', '').strip()
        currency = request.args.get('currency', '').strip()
        date_range = request.args.get('date_range', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        min_amount = request.args.get('min_amount', None, type=float)
        max_amount = request.args.get('max_amount', None, type=float)
        keyword = request.args.get('keyword', '').strip()
        sort_by = request.args.get('sort_by', 'invoice_date').strip()
        sort_order = request.args.get('sort_order', 'desc').strip()
        
        # 构建查询
        query = db.session.query(
            ProjectInvoice,
            ProjectHeader.hid.label('project_hid'),
            ProjectHeader.desc.label('project_name')
        ).join(
            ProjectHeader, ProjectInvoice.header_id == ProjectHeader.id, isouter=True
        )
        
        filters = []
        
        if status:
            filters.append(ProjectInvoice.status == status)
        if invoice_type:
            filters.append(ProjectInvoice.invoice_type == invoice_type)
        if currency:
            filters.append(ProjectInvoice.currency == currency)
        
        # 日期筛选
        if start_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                filters.append(ProjectInvoice.invoice_date >= sd)
            except ValueError:
                pass
        if end_date:
            try:
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
                filters.append(ProjectInvoice.invoice_date <= ed)
            except ValueError:
                pass
        
        if (not start_date and not end_date) and date_range:
            today = date.today()
            if date_range == 'today':
                filters.append(ProjectInvoice.invoice_date == today)
            elif date_range == 'week':
                start = today - timedelta(days=today.weekday())
                end = start + timedelta(days=6)
                filters.append(and_(ProjectInvoice.invoice_date >= start, ProjectInvoice.invoice_date <= end))
            elif date_range == 'month':
                start = today.replace(day=1)
                if today.month == 12:
                    end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
                filters.append(and_(ProjectInvoice.invoice_date >= start, ProjectInvoice.invoice_date <= end))
            elif date_range == 'year':
                start = today.replace(month=1, day=1)
                end = today.replace(month=12, day=31)
                filters.append(and_(ProjectInvoice.invoice_date >= start, ProjectInvoice.invoice_date <= end))
        
        if min_amount is not None and min_amount > 0:
            filters.append(ProjectInvoice.amount >= float(min_amount))
        if max_amount is not None and max_amount > 0:
            filters.append(ProjectInvoice.amount <= float(max_amount))
        
        if keyword:
            kw = f"%{keyword}%"
            filters.append(or_(
                ProjectInvoice.invoice_number.ilike(kw),
                ProjectInvoice.customer_name.ilike(kw),
                ProjectInvoice.customer_company.ilike(kw),
                ProjectInvoice.remarks.ilike(kw),
                ProjectHeader.hid.ilike(kw),
                ProjectHeader.desc.ilike(kw)
            ))
        
        if filters:
            query = query.filter(and_(*filters))
        
        # 排序
        if sort_by == 'invoice_date':
            order_col = ProjectInvoice.invoice_date
        elif sort_by == 'amount':
            order_col = ProjectInvoice.amount
        elif sort_by == 'due_date':
            order_col = ProjectInvoice.due_date
        elif sort_by == 'created_at':
            order_col = ProjectInvoice.created_at
        else:
            order_col = ProjectInvoice.invoice_date
        
        query = query.order_by(asc(order_col) if sort_order == 'asc' else desc(order_col))
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # 组织数据
        items = []
        for inv, project_hid, project_name in pagination.items:
            items.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'project_hid': project_hid,
                'project_name': project_name,
                'header_id': inv.header_id,
                'invoice_date': inv.invoice_date,
                'due_date': inv.due_date,
                'amount': float(inv.amount) if inv.amount else 0,
                'paid_amount': float(inv.paid_amount) if inv.paid_amount else 0,
                'unpaid_amount': inv.unpaid_amount,
                'currency': inv.currency,
                'invoice_type': inv.invoice_type,
                'invoice_type_display': inv.invoice_type_display,
                'customer_name': inv.customer_name,
                'customer_company': inv.customer_company,
                'status': inv.status,
                'status_display': inv.status_display,
                'is_overdue': inv.is_overdue,
                'created_at': inv.created_at
            })
        
        # 状态选项
        statuses = [
            ('', '全部'),
            ('draft', '草稿'),
            ('sent', '已发送'),
            ('paid', '已付款'),
            ('partial_paid', '部分付款'),
            ('overdue', '已逾期'),
            ('cancelled', '已取消')
        ]
        
        # 发票类型选项
        invoice_types = [
            ('', '全部'),
            ('full', '全额发票'),
            ('partial', '分期发票'),
            ('deposit', '定金发票'),
            ('final', '尾款发票')
        ]
        
        return render_template('business/projects/project_invoice/invoice_list.html',
                             invoices=items,
                             pagination=pagination,
                             statuses=statuses,
                             invoice_types=invoice_types,
                             current_filters={
                                 'status': status,
                                 'invoice_type': invoice_type,
                                 'currency': currency,
                                 'date_range': date_range,
                                 'start_date': start_date,
                                 'end_date': end_date,
                                 'min_amount': min_amount,
                                 'max_amount': max_amount,
                                 'keyword': keyword,
                                 'sort_by': sort_by,
                                 'sort_order': sort_order,
                                 'per_page': per_page
                             })
                             
    except Exception as e:
        db.session.rollback()
        flash(f'发票列表加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_invoice.route('/api/header/<int:header_id>/summary')
@login_required
@staff_only
def get_invoice_summary(header_id):
    """获取项目发票汇总信息 - API接口"""
    header = ProjectHeader.query.get_or_404(header_id)
    
    total_invoiced = ProjectInvoice.get_header_total_invoiced(header_id)
    total_paid = ProjectInvoice.get_header_total_paid(header_id)
    total_unpaid = total_invoiced - total_paid
    total_selling = sum(float(ref.selling_price or 0) for ref in header.refs)
    
    # 获取各状态发票数量
    from sqlalchemy import func
    status_counts = db.session.query(
        ProjectInvoice.status,
        func.count(ProjectInvoice.id)
    ).filter(
        ProjectInvoice.header_id == header_id
    ).group_by(ProjectInvoice.status).all()
    
    return jsonify({
        'success': True,
        'header_id': header_id,
        'total_selling': total_selling,
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
        'invoice_coverage': (total_invoiced / total_selling * 100) if total_selling > 0 else 0,
        'status_counts': {status: count for status, count in status_counts}
    })

