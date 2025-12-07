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
    import json
    from App_new.business.projects.models.project_member import ProjectMember
    
    invoice = ProjectInvoice.query.get_or_404(invoice_id)
    
    # 获取关联的REF信息
    related_refs = invoice.related_refs
    
    # 为每个REF解析extra_info并获取人员姓名
    for ref in related_refs:
        if ref.extra_info:
            try:
                extra_data = json.loads(ref.extra_info)
                # 检查是否已有pax_names_display（机票REF已预先生成）
                if not extra_data.get('pax_names_display'):
                    # 获取选中的人员姓名（其他REF使用ID列表）
                    pax_names_ids = extra_data.get('pax_names', [])
                    if pax_names_ids:
                        members = ProjectMember.query.filter(ProjectMember.id.in_(pax_names_ids)).all()
                        pax_names_list = [f"{m.title} {m.member_name}" if m.title else m.member_name for m in members]
                        extra_data['pax_names_display'] = ', '.join(pax_names_list)
                    else:
                        extra_data['pax_names_display'] = extra_data.get('pax_name', '')
                ref.extra_data = extra_data
            except (json.JSONDecodeError, TypeError):
                ref.extra_data = {}
        else:
            # 如果没有extra_info，尝试从flight_passengers获取乘客信息
            if hasattr(ref, 'flight_passengers') and ref.flight_passengers:
                pax_names = [p.name for p in ref.flight_passengers if p.name]
                ref.extra_data = {
                    'pax_names_display': ', '.join(pax_names),
                    'departure_date': ref.flight_segments[0].departure_time.strftime('%Y-%m-%d') if ref.flight_segments and ref.flight_segments[0].departure_time else ''
                }
            else:
                ref.extra_data = {}
    
    # 获取发票明细
    items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
    
    # 为每个item的ref也处理extra_info
    for item in items:
        if item.ref and item.ref.extra_info:
            try:
                extra_data = json.loads(item.ref.extra_info)
                # 检查是否已有pax_names_display（机票REF已预先生成）
                if not extra_data.get('pax_names_display'):
                    # 获取选中的人员姓名（其他REF使用ID列表）
                    pax_names_ids = extra_data.get('pax_names', [])
                    if pax_names_ids:
                        members = ProjectMember.query.filter(ProjectMember.id.in_(pax_names_ids)).all()
                        pax_names_list = [f"{m.title} {m.member_name}" if m.title else m.member_name for m in members]
                        extra_data['pax_names_display'] = ', '.join(pax_names_list)
                    else:
                        extra_data['pax_names_display'] = extra_data.get('pax_name', '')
                item.ref.extra_data = extra_data
            except (json.JSONDecodeError, TypeError):
                item.ref.extra_data = {}
        elif item.ref:
            # 如果没有extra_info，尝试从flight_passengers获取乘客信息
            if hasattr(item.ref, 'flight_passengers') and item.ref.flight_passengers:
                pax_names = [p.name for p in item.ref.flight_passengers if p.name]
                item.ref.extra_data = {
                    'pax_names_display': ', '.join(pax_names),
                    'departure_date': item.ref.flight_segments[0].departure_time.strftime('%Y-%m-%d') if item.ref.flight_segments and item.ref.flight_segments[0].departure_time else ''
                }
            else:
                item.ref.extra_data = {}
    
    # 获取项目header的最新公司信息
    header = invoice.header
    customer_company_display = None
    customer_company_address = None
    customer_company_phone = None
    if header and header.company:
        customer_company_display = header.company.company_name
        customer_company_address = header.company.address
        customer_company_phone = header.company.contact_phone
    
    # 解析付款记录 - 从两个来源获取
    payments = []
    
    # 来源1: invoice.extra_info['payments']（通过发票付款功能记录的）
    if invoice.extra_info:
        try:
            extra_info = json.loads(invoice.extra_info)
            payments = extra_info.get('payments', [])
        except (json.JSONDecodeError, TypeError):
            pass
    
    # 来源2: ProjectReceipt表中关联到发票对应ref的收款记录
    from App_new.business.projects.models.receipt import ProjectReceipt
    
    # 获取发票关联的ref IDs
    invoice_ref_ids = []
    if invoice.ref_ids:
        try:
            invoice_ref_ids = json.loads(invoice.ref_ids)
            # 确保是整数列表
            invoice_ref_ids = [int(rid) for rid in invoice_ref_ids if rid]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    
    # 如果发票没有关联ref，则使用整个header的receipt（向后兼容）
    if invoice_ref_ids:
        # 只获取与发票关联的ref的receipt
        # 1. 直接关联到这些ref的receipt（REF级别收款）
        ref_receipts = ProjectReceipt.query.filter(
            ProjectReceipt.ref_id.in_(invoice_ref_ids),
            ProjectReceipt.status == 'confirmed'
        ).order_by(ProjectReceipt.payment_date).all()
        
        for receipt in ref_receipts:
            # 检查是否已经在payments中（避免重复）
            receipt_exists = any(
                p.get('receipt_id') == receipt.id or 
                (p.get('date') == receipt.payment_date.strftime('%Y-%m-%d') and 
                 abs(float(p.get('amount', 0)) - float(receipt.amount)) < 0.01)
                for p in payments
            )
            if not receipt_exists:
                payments.append({
                    'receipt_id': receipt.id,
                    'date': receipt.payment_date.strftime('%d/%m/%Y') if receipt.payment_date else '',
                    'ref_number': receipt.receipt_number,
                    'method': receipt.payment_method_display,
                    'amount': float(receipt.amount),
                    'remarks': receipt.remarks
                })
        
        # 2. 项目级别收款记录中分配给这些ref的金额
        project_receipts = ProjectReceipt.query.filter(
            ProjectReceipt.header_id == invoice.header_id,
            ProjectReceipt.ref_id.is_(None),  # 项目级别收款
            ProjectReceipt.status == 'confirmed'
        ).order_by(ProjectReceipt.payment_date).all()
        
        for project_receipt in project_receipts:
            if project_receipt.extra_info:
                try:
                    distribution_info = json.loads(project_receipt.extra_info)
                    if 'distribution' in distribution_info:
                        # 计算分配给发票关联ref的金额总和
                        allocated_amount = 0
                        for dist in distribution_info['distribution']:
                            if dist.get('ref_id') in invoice_ref_ids:
                                allocated_amount += float(dist.get('amount', 0))
                        
                        if allocated_amount > 0:
                            # 检查是否已经在payments中（避免重复）
                            receipt_exists = any(
                                p.get('receipt_id') == project_receipt.id
                                for p in payments
                            )
                            if not receipt_exists:
                                payments.append({
                                    'receipt_id': project_receipt.id,
                                    'date': project_receipt.payment_date.strftime('%d/%m/%Y') if project_receipt.payment_date else '',
                                    'ref_number': project_receipt.receipt_number,
                                    'method': project_receipt.payment_method_display,
                                    'amount': allocated_amount,  # 只计算分配给这些ref的金额
                                    'remarks': project_receipt.remarks
                                })
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
    else:
        # 如果没有关联ref，使用整个header的receipt（向后兼容）
        project_receipts = ProjectReceipt.query.filter_by(
            header_id=invoice.header_id, 
            status='confirmed'
        ).order_by(ProjectReceipt.payment_date).all()
        
        for receipt in project_receipts:
            # 检查是否已经在payments中（避免重复）
            receipt_exists = any(
                p.get('receipt_id') == receipt.id or 
                (p.get('date') == receipt.payment_date.strftime('%Y-%m-%d') and 
                 abs(float(p.get('amount', 0)) - float(receipt.amount)) < 0.01)
                for p in payments
            )
            if not receipt_exists:
                payments.append({
                    'receipt_id': receipt.id,
                    'date': receipt.payment_date.strftime('%d/%m/%Y') if receipt.payment_date else '',
                    'ref_number': receipt.receipt_number,
                    'method': receipt.payment_method_display,
                    'amount': float(receipt.amount),
                    'remarks': receipt.remarks
                })
    
    # 计算实际已付总额和余额
    # Receipt总额 = 关联ref的receipt总和
    total_paid = sum(float(p.get('amount', 0)) for p in payments)
    
    # Balance = 发票金额 - Receipt总额
    # 发票金额是实际开票金额，receipt是实际收款
    balance = float(invoice.amount or 0) - total_paid
    
    # 获取项目联系人
    project_contact = header.contact if header else None
    
    return render_template('business/projects/project_invoice/invoice_detail.html',
                         invoice=invoice,
                         related_refs=related_refs,
                         items=items,
                         customer_company_display=customer_company_display,
                         customer_company_address=customer_company_address,
                         customer_company_phone=customer_company_phone,
                         project_contact=project_contact,
                         payments=payments,
                         balance=balance)


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


@project_invoice.route('/<int:invoice_id>/sync-ref-prices', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def sync_ref_prices(invoice_id):
    """同步REF价格到发票"""
    try:
        invoice = ProjectInvoice.query.get_or_404(invoice_id)
        
        # 获取关联的REF
        ref_ids = []
        if invoice.ref_ids:
            try:
                ref_ids = json.loads(invoice.ref_ids)
            except (json.JSONDecodeError, TypeError):
                pass
        
        if not ref_ids:
            return jsonify({'success': False, 'message': '发票没有关联的REF'})
        
        # 计算新的总金额
        new_total = 0
        updated_items = []
        
        for ref_id in ref_ids:
            ref = ProjectRef.query.get(ref_id)
            if ref and ref.selling_price:
                new_total += float(ref.selling_price)
                updated_items.append({
                    'ref_number': ref.ref_number,
                    'old_price': 0,  # 将在下面更新
                    'new_price': float(ref.selling_price)
                })
        
        old_amount = float(invoice.amount or 0)
        
        # 更新发票金额
        invoice.amount = new_total
        
        # 更新发票明细项
        items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        for item in items:
            if item.ref_id:
                ref = ProjectRef.query.get(item.ref_id)
                if ref:
                    # 记录旧价格
                    for ui in updated_items:
                        if ui['ref_number'] == ref.ref_number:
                            ui['old_price'] = float(item.total_price or 0)
                    # 更新价格
                    item.unit_price = ref.selling_price or 0
                    item.total_price = ref.selling_price or 0
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'价格同步成功！金额从 {old_amount:.2f} 更新为 {new_total:.2f}',
            'old_amount': old_amount,
            'new_amount': new_total,
            'updated_items': updated_items
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'同步失败：{str(e)}'})


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
            remarks=', '.join(filter(None, [
                f"Order: {data.get('order_no')}" if data.get('order_no') else None,
                f"TR: {data.get('tr_no')}" if data.get('tr_no') else None,
                f"Purpose: {data.get('purpose')}" if data.get('purpose') else None
            ])),
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


@project_invoice.route('/find_by_number', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def find_invoice_by_number():
    """通过发票号查找发票"""
    try:
        data = request.get_json()
        invoice_number = data.get('invoice_number')
        
        if not invoice_number:
            return jsonify({'success': False, 'message': '请输入发票号'})
        
        # 查找发票
        invoice = ProjectInvoice.query.filter_by(
            invoice_number=invoice_number.strip()
        ).first()
        
        if not invoice:
            return jsonify({'success': False, 'message': f'未找到发票号 {invoice_number}'})
        
        return jsonify({
            'success': True,
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number
        })
        
    except Exception as e:
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

