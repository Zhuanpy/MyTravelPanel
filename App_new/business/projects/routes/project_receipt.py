from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
from App_new.business.projects.models.invoice import ProjectInvoice
from App_new.exts import csrf, db
from App_new.business.projects.forms.receipt_forms import ProjectReceiptForm, ProjectLevelReceiptForm
from App_new.utils.decorators import staff_only, admin_only
from App_new.shared.error_logging import log_error
import json


def get_invoice_choices(header_id):
    """获取项目的发票选择列表（用于表单下拉框）"""
    invoices = ProjectInvoice.query.filter(
        ProjectInvoice.header_id == header_id,
        ProjectInvoice.status != 'cancelled'
    ).order_by(ProjectInvoice.created_at.desc()).all()

    choices = [(0, '-- 不关联发票 --')]
    for inv in invoices:
        unpaid = float(inv.amount or 0) - float(inv.paid_amount or 0)
        status_text = inv.status_display
        choices.append((
            inv.id,
            f"{inv.invoice_number} - {inv.currency} {float(inv.amount):.2f} ({status_text}, 未付: {unpaid:.2f})"
        ))
    return choices

project_receipt = Blueprint('project_receipt', __name__)

@project_receipt.route('/create/<int:ref_id>', methods=['GET', 'POST'])
def create_receipt(ref_id):
    """创建REF级别收款记录"""
    ref = ProjectRef.query.get_or_404(ref_id)

    # 检查是否有发票（必须先生成发票才能收款）
    from App_new.business.projects.models.invoice import ProjectInvoice
    invoice_count = ProjectInvoice.query.filter_by(header_id=ref.header_id).filter(
        ProjectInvoice.status != 'cancelled'
    ).count()
    if invoice_count == 0:
        flash('请先生成发票后再创建收款记录', 'warning')
        return redirect(url_for('business_projects.project_receipt.ref_receipts', ref_id=ref_id))

    form = ProjectReceiptForm()

    # 动态填充发票选择
    form.invoice_id.choices = get_invoice_choices(ref.header_id)

    # 预填充收款单号
    receipt_number = ProjectReceipt.generate_receipt_number()

    if form.validate_on_submit():
        try:
            # 处理发票ID（0表示不关联）
            invoice_id = form.invoice_id.data if form.invoice_id.data and form.invoice_id.data != 0 else None

            # 创建收款记录（不再直接设置 invoice_id）
            receipt = ProjectReceipt(
                receipt_number=receipt_number,
                ref_id=ref.id,
                header_id=ref.header_id,
                invoice_id=None,  # 不再使用此字段
                amount=form.amount.data,
                currency=form.currency.data,
                payment_method=form.payment_method.data,
                payment_date=form.payment_date.data,
                payer_name=form.payer_name.data,
                payer_contact=form.payer_contact.data,
                payer_company=form.payer_company.data,
                bank_name=form.bank_name.data,
                account_number=form.account_number.data,
                transaction_id=form.transaction_id.data,
                remarks=form.remarks.data,
                status='confirmed'  # 默认已确认
            )

            db.session.add(receipt)
            db.session.flush()  # 获取 receipt.id

            # 如果选择了发票，创建分配记录
            if invoice_id:
                allocation = ReceiptInvoiceAllocation(
                    receipt_id=receipt.id,
                    invoice_id=invoice_id,
                    allocated_amount=form.amount.data
                )
                db.session.add(allocation)
                db.session.flush()

            # 自动创建日记账分录（借：银行存款，贷：应收账款）
            try:
                from App_new.finance.models.journal_entry import JournalEntry
                from flask_login import current_user
                journal_entry = JournalEntry.create_from_receipt(
                    receipt,
                    user=current_user.username if current_user else None
                )
                if journal_entry and journal_entry.lines:
                    db.session.add(journal_entry)
                    # 自动过账
                    journal_entry.post(user=current_user.username if current_user else None)
            except Exception as je_error:
                # 日记账创建失败不影响收款记录
                import logging
                logging.getLogger(__name__).warning(f"创建收款日记账失败: {str(je_error)}")

            # 重新查询REF以获取最新的收款记录
            ref = ProjectRef.query.get(ref_id)

            # 更新REF的付款状态
            total_received = ProjectReceipt.get_ref_total_received(ref.id, ref.header_id)
            if total_received >= float(ref.selling_price or 0):
                ref.payment_status = 'paid'
            elif total_received > 0:
                ref.payment_status = 'partial'
            else:
                ref.payment_status = 'unpaid'

            # 更新关联发票的已付金额（通过分配表计算）
            if invoice_id:
                ProjectReceipt.update_invoice_paid_amount(invoice_id)

            db.session.commit()

            return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')

    # 获取REF的未付款金额（使用辅助方法，包括项目级别分配）
    total_received = ProjectReceipt.get_ref_total_received(ref.id, ref.header_id)
    unpaid_amount = float(ref.selling_price or 0) - total_received

    return render_template('business/projects/project_receipt/create_receipt.html',
                          form=form,
                          ref=ref,
                          receipt_number=receipt_number,
                          unpaid_amount=unpaid_amount)

@project_receipt.route('/<int:receipt_id>')
def receipt_detail(receipt_id):
    """收款记录详情"""
    receipt = ProjectReceipt.query.get_or_404(receipt_id)
    return render_template('business/projects/project_receipt/receipt_detail.html', receipt=receipt)

@project_receipt.route('/<int:receipt_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_receipt(receipt_id):
    """编辑收款记录"""
    receipt = ProjectReceipt.query.get_or_404(receipt_id)
    form = ProjectReceiptForm(obj=receipt)

    # 动态填充发票选择
    form.invoice_id.choices = get_invoice_choices(receipt.header_id)

    if form.validate_on_submit():
        try:
            # 获取旧的分配记录的发票ID列表
            old_allocation_invoice_ids = [a.invoice_id for a in receipt.invoice_allocations]

            # 处理发票ID（0表示不关联）
            new_invoice_id = form.invoice_id.data if form.invoice_id.data and form.invoice_id.data != 0 else None

            # 更新收款记录（不设置 invoice_id）
            receipt.amount = form.amount.data
            receipt.currency = form.currency.data
            receipt.payment_method = form.payment_method.data
            receipt.payment_date = form.payment_date.data
            receipt.payer_name = form.payer_name.data
            receipt.payer_contact = form.payer_contact.data
            receipt.payer_company = form.payer_company.data
            receipt.bank_name = form.bank_name.data
            receipt.account_number = form.account_number.data
            receipt.transaction_id = form.transaction_id.data
            receipt.remarks = form.remarks.data

            # 如果这是一个REF级别收款（有 ref_id），更新分配记录
            if receipt.ref_id:
                # 删除旧的分配记录
                ReceiptInvoiceAllocation.query.filter_by(receipt_id=receipt.id).delete()

                # 如果选择了新发票，创建新的分配记录
                if new_invoice_id:
                    allocation = ReceiptInvoiceAllocation(
                        receipt_id=receipt.id,
                        invoice_id=new_invoice_id,
                        allocated_amount=form.amount.data
                    )
                    db.session.add(allocation)

            db.session.flush()

            # 重新查询REF以获取最新的收款记录
            if receipt.ref_id:
                ref = ProjectRef.query.get(receipt.ref_id)

                # 更新REF的付款状态
                total_received = ProjectReceipt.get_ref_total_received(ref.id, ref.header_id)
                if total_received >= float(ref.selling_price or 0):
                    ref.payment_status = 'paid'
                elif total_received > 0:
                    ref.payment_status = 'partial'
                else:
                    ref.payment_status = 'unpaid'

            # 更新所有受影响发票的已付金额
            affected_invoice_ids = set(old_allocation_invoice_ids)
            if new_invoice_id:
                affected_invoice_ids.add(new_invoice_id)
            for inv_id in affected_invoice_ids:
                ProjectReceipt.update_invoice_paid_amount(inv_id)

            db.session.commit()

            return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=receipt.header_id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')

    return render_template('business/projects/project_receipt/edit_receipt.html',
                         form=form,
                         receipt=receipt)

@project_receipt.route('/<int:receipt_id>/delete', methods=['POST'])
@csrf.exempt
def delete_receipt(receipt_id):
    """删除收款记录"""
    receipt = ProjectReceipt.query.get_or_404(receipt_id)
    header_id = receipt.header_id
    ref_id = receipt.ref_id

    # 获取所有分配记录的发票ID（用于删除后更新）
    affected_invoice_ids = [a.invoice_id for a in receipt.invoice_allocations]

    try:
        # 冲销对应的日记账分录
        from App_new.finance.models.journal_entry import JournalEntry
        from flask_login import current_user

        print(f"[DEBUG] 删除收款 - receipt.id={receipt.id}, receipt_number={receipt.receipt_number}")

        journal_entry = JournalEntry.query.filter(
            JournalEntry.source_type == 'receipt',
            JournalEntry.source_id == receipt.id,
            JournalEntry.status == 'posted'
        ).first()

        print(f"[DEBUG] 查找日记账分录 - 找到: {journal_entry.entry_number if journal_entry else 'None'}")

        if journal_entry:
            try:
                reversal = journal_entry.reverse(user=current_user.username if current_user else None)
                if reversal:
                    db.session.add(reversal)
                    print(f"[DEBUG] 冲销成功 - 原分录状态: {journal_entry.status}, 冲销分录: {reversal.entry_number}")
            except Exception as je_err:
                log_error(f'冲销收款日记账失败 receipt_id={receipt_id}', je_err)
                print(f"[DEBUG] 冲销失败: {str(je_err)}")
        else:
            print(f"[DEBUG] 未找到对应的日记账分录")

        # 删除分配记录（级联删除或手动删除）
        ReceiptInvoiceAllocation.query.filter_by(receipt_id=receipt.id).delete()

        # 删除收款记录
        db.session.delete(receipt)
        db.session.flush()

        # 更新REF的付款状态
        if ref_id:
            ref = ProjectRef.query.get(ref_id)
            if ref:
                # 使用辅助方法计算总收款金额
                total_received = ProjectReceipt.get_ref_total_received(ref.id, ref.header_id)
                if total_received >= float(ref.selling_price or 0):
                    ref.payment_status = 'paid'
                elif total_received > 0:
                    ref.payment_status = 'partial'
                else:
                    ref.payment_status = 'unpaid'

        # 更新所有受影响发票的已付金额
        for inv_id in affected_invoice_ids:
            ProjectReceipt.update_invoice_paid_amount(inv_id)

        db.session.commit()
        flash('收款记录删除成功！', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')

    return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=header_id))

@project_receipt.route('/<int:receipt_id>/status', methods=['POST'])
@csrf.exempt
def update_receipt_status(receipt_id):
    """更新收款记录状态"""
    data = request.get_json()
    status = data.get('status')

    if status not in ['pending', 'confirmed', 'cancelled']:
        return jsonify({'success': False, 'message': '无效的状态'})

    receipt = ProjectReceipt.query.get_or_404(receipt_id)
    old_status = receipt.status

    try:
        receipt.status = status

        # 如果状态变更为 cancelled，冲销对应的日记账分录并删除发票分配
        if status == 'cancelled' and old_status != 'cancelled':
            from App_new.finance.models.journal_entry import JournalEntry
            from flask_login import current_user

            # 冲销日记账分录
            journal_entry = JournalEntry.query.filter(
                JournalEntry.source_type == 'receipt',
                JournalEntry.source_id == receipt.id,
                JournalEntry.status == 'posted'
            ).first()

            if journal_entry:
                try:
                    reversal = journal_entry.reverse(user=current_user.username if current_user else None)
                    if reversal:
                        db.session.add(reversal)
                except Exception as je_err:
                    import logging
                    logging.getLogger(__name__).warning(f"冲销收款日记账失败: {str(je_err)}")

            # 获取受影响的发票ID（在删除分配前）
            affected_invoice_ids = [a.invoice_id for a in receipt.invoice_allocations]

            # 删除发票分配记录
            ReceiptInvoiceAllocation.query.filter_by(receipt_id=receipt.id).delete()

            # 更新受影响发票的已付金额
            for inv_id in affected_invoice_ids:
                ProjectReceipt.update_invoice_paid_amount(inv_id)

        # 先提交收款记录状态更新
        db.session.flush()

        # 更新REF的付款状态
        if receipt.ref_id:
            ref = ProjectRef.query.get(receipt.ref_id)
            if ref:
                # 使用辅助方法计算总收款金额
                total_received = ProjectReceipt.get_ref_total_received(ref.id, ref.header_id)
                if total_received >= float(ref.selling_price or 0):
                    ref.payment_status = 'paid'
                elif total_received > 0:
                    ref.payment_status = 'partial'
                else:
                    ref.payment_status = 'unpaid'

        # 更新所有分配发票的已付金额（非取消状态时，取消状态已在上面处理）
        if status != 'cancelled':
            for allocation in receipt.invoice_allocations:
                ProjectReceipt.update_invoice_paid_amount(allocation.invoice_id)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'收款状态已更新为 {receipt.status_display}'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})

@project_receipt.route('/api/ref/<int:ref_id>/receipts')
def get_ref_receipts(ref_id):
    """获取REF的收款记录列表 - API接口"""
    ref = ProjectRef.query.get_or_404(ref_id)
    receipts = ProjectReceipt.query.filter_by(ref_id=ref_id).order_by(ProjectReceipt.created_at.desc()).all()
    
    # 使用辅助方法计算总收款（包括项目级别分配）
    total_received = ProjectReceipt.get_ref_total_received(ref_id, ref.header_id)
    unpaid_amount = float(ref.selling_price or 0) - total_received
    
    return jsonify({
        'success': True,
        'receipts': [receipt.to_dict() for receipt in receipts],
        'total_received': total_received,
        'unpaid_amount': unpaid_amount
    })

@project_receipt.route('/ref/<int:ref_id>/receipts')
def ref_receipts(ref_id):
    """查看REF的收款记录列表"""
    ref = ProjectRef.query.get_or_404(ref_id)
    receipts = ProjectReceipt.query.filter_by(ref_id=ref_id).order_by(ProjectReceipt.created_at.desc()).all()
    
    # 计算已收款和未收款金额（使用辅助方法，包括项目级别分配）
    total_received = ProjectReceipt.get_ref_total_received(ref_id, ref.header_id)
    unpaid_amount = float(ref.selling_price or 0) - total_received
    
    return render_template('business/projects/project_receipt/ref_receipts.html',
                          ref=ref,
                          receipts=receipts,
                          total_received=total_received,
                          unpaid_amount=unpaid_amount)

@project_receipt.route('/header/<int:header_id>/receipts')
@login_required
@staff_only
def header_receipts(header_id):
    """查看项目的收款记录列表"""
    header = ProjectHeader.query.get_or_404(header_id)
    
    # 获取所有收款记录（项目级别和REF级别）
    all_receipts = ProjectReceipt.query.filter(
        ProjectReceipt.header_id == header_id
    ).order_by(ProjectReceipt.created_at.desc()).all()
    
    # 为每条收款记录添加分配到的REF信息
    for receipt in all_receipts:
        if receipt.ref_id is None and receipt.extra_info:
            # 项目级别收款，解析分配信息
            try:
                distribution_info = json.loads(receipt.extra_info)
                distributed_refs = []
                if 'distribution' in distribution_info:
                    for dist in distribution_info['distribution']:
                        ref_id = dist.get('ref_id')
                        if ref_id:
                            ref = ProjectRef.query.get(ref_id)
                            if ref:
                                distributed_refs.append({
                                    'id': ref.id,
                                    'ref_number': ref.ref_number,
                                    'name': ref.description or ref.detailed_description,
                                    'amount': dist.get('amount', 0)
                                })
                receipt.distributed_refs = distributed_refs
            except (json.JSONDecodeError, KeyError, TypeError):
                receipt.distributed_refs = []
        else:
            receipt.distributed_refs = []

    # 附加每条收款对应的发票号（用于打印收据显示）
    for receipt in all_receipts:
        inv_numbers = []
        for alloc in (receipt.invoice_allocations or []):
            if alloc.invoice and alloc.invoice.invoice_number:
                inv_numbers.append(alloc.invoice.invoice_number)
        # 兼容旧数据的直接关联
        if not inv_numbers and receipt.invoice and receipt.invoice.invoice_number:
            inv_numbers.append(receipt.invoice.invoice_number)
        # 去重保序
        seen = set()
        receipt.invoice_no_str = ', '.join(x for x in inv_numbers if not (x in seen or seen.add(x)))

    # 付款历史（用于打印收据的台账：逐笔显示日期、扣款金额、余额），按付款日期升序
    payment_history = [
        {
            'id': r.id,
            'date': r.payment_date.strftime('%d/%m/%Y') if r.payment_date else '',
            'amount': float(r.amount or 0),
            'currency': r.currency or 'SGD',
            'payer': (r.payer_company or r.payer_name or '').strip(),
            'method': r.payment_method_display_en,
            'number': r.receipt_number or ''
        }
        for r in sorted(
            [x for x in all_receipts if x.status != 'cancelled'],
            key=lambda x: (x.payment_date or x.created_at)
        )
    ]

    # 统计所有REF的实际已收款金额（包括项目级别分配）
    total_received = 0
    for ref in header.refs:
        if ref.selling_price:
            total_received += ProjectReceipt.get_ref_total_received(ref.id, header_id)
    # 未收款金额：只统计已开票的REF（未开票不形成应收款）
    unpaid_amount = header.total_unpaid_amount

    # 准备新增收款弹窗的表单数据
    form = ProjectLevelReceiptForm()
    receipt_number = ProjectReceipt.generate_receipt_number()

    # 检查是否有发票
    from App_new.business.projects.models.invoice import ProjectInvoice
    invoice_count = ProjectInvoice.query.filter_by(header_id=header_id).filter(
        ProjectInvoice.status != 'cancelled'
    ).count()

    # 获取未付款发票列表
    unpaid_invoices = []
    if invoice_count > 0:
        invoices = ProjectInvoice.query.filter_by(header_id=header_id).filter(
            ProjectInvoice.status.in_(['confirmed', 'partial'])
        ).order_by(ProjectInvoice.invoice_date).all()
        for invoice in invoices:
            inv_unpaid = invoice.unpaid_amount
            if inv_unpaid > 0:
                unpaid_invoices.append((
                    invoice.id,
                    f"{invoice.invoice_number} - {invoice.customer_name or '客户'} (未收款: {invoice.currency or 'SGD'} {inv_unpaid:.2f})"
                ))
    form.selected_invoices.choices = unpaid_invoices if unpaid_invoices else [(0, "暂无未付款的发票")]

    # 是否可以创建收款
    can_create_receipt = invoice_count > 0 and unpaid_amount > 0

    return render_template('business/projects/project_receipt/header_receipts.html',
                         header=header,
                         all_receipts=all_receipts,
                         payment_history=payment_history,
                         total_received=total_received,
                         unpaid_amount=unpaid_amount,
                         form=form,
                         receipt_number=receipt_number,
                         invoice_count=invoice_count,
                         can_create_receipt=can_create_receipt)

@project_receipt.route('/header/<int:header_id>/receipt/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_header_receipt(header_id):
    """创建项目级别收款记录"""
    header = ProjectHeader.query.get_or_404(header_id)

    # 检查是否有发票（必须先生成发票才能收款）
    from App_new.business.projects.models.invoice import ProjectInvoice
    invoice_count = ProjectInvoice.query.filter_by(header_id=header_id).filter(
        ProjectInvoice.status != 'cancelled'
    ).count()
    if invoice_count == 0:
        flash('请先生成发票后再创建收款记录', 'warning')
        log_error(f'项目收款被拦（无可用发票）H{header.hid}(id={header_id})')
        return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=header_id))

    # 检查是否还有未收款金额
    unpaid_amount = ProjectReceipt.get_project_unpaid_amount(header_id)
    if unpaid_amount <= 0:
        flash('该项目已无未收款金额，无法创建新收款记录', 'warning')
        # 这两条 warning 会直接 redirect，页面上看起来只是"闪了一下"，必须留痕
        log_error(f'项目收款被拦（发票未收合计为0）H{header.hid}(id={header_id})：'
                  f'发票口径未收={unpaid_amount:.2f}，页面口径未收={header.total_unpaid_amount:.2f}')
        return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=header_id))

    form = ProjectLevelReceiptForm()

    # 动态生成未付款发票选择选项
    unpaid_invoices = []
    from App_new.business.projects.models.invoice import ProjectInvoice
    invoices = ProjectInvoice.query.filter_by(header_id=header_id).filter(
        ProjectInvoice.status.in_(['confirmed', 'partial'])
    ).order_by(ProjectInvoice.invoice_date).all()

    for invoice in invoices:
        inv_unpaid = invoice.unpaid_amount
        if inv_unpaid > 0:
            unpaid_invoices.append((
                invoice.id,
                f"{invoice.invoice_number} - {invoice.customer_name or '客户'} (未收款: {invoice.currency or 'SGD'} {inv_unpaid:.2f})"
            ))

    form.selected_invoices.choices = unpaid_invoices

    # 如果没有未付款的发票，添加一个提示选项
    if not unpaid_invoices:
        form.selected_invoices.choices = [(0, "暂无未付款的发票")]
    
    # 预填充收款单号
    receipt_number = ProjectReceipt.generate_receipt_number()
    
    if form.validate_on_submit():
        try:
            amount = float(form.amount.data)
            distribution_method = form.distribution_method.data
            
            # 验证收款金额不能超过未收款总额（严格验证）
            unpaid_amount = ProjectReceipt.get_project_unpaid_amount(header_id)
            if amount > unpaid_amount + 0.01:  # 允许0.01的浮点数误差
                flash(f'收款金额({amount:.2f})不能超过未收款总额({unpaid_amount:.2f})', 'error')
                log_error(f'项目收款被拒 H{header.hid}(id={header_id})：收款金额 {amount:.2f} > 未收款总额 {unpaid_amount:.2f}')
                return render_template('business/projects/project_receipt/create_header_receipt.html',
                                     form=form,
                                     header=header,
                                     receipt_number=receipt_number,
                                     unpaid_amount=unpaid_amount)
            
            # 根据分配方式处理 - 按发票分配
            from App_new.business.projects.models.invoice import ProjectInvoice

            if distribution_method == 'manual':
                # 手动分配：只分配给选中的发票
                selected_invoice_ids = form.selected_invoices.data
                if not selected_invoice_ids or (len(selected_invoice_ids) == 1 and selected_invoice_ids[0] == 0):
                    flash('请选择要分配的发票', 'error')
                    log_error(f'项目收款被拒 H{header.hid}(id={header_id})：手动分配但未选择发票')
                    return render_template('business/projects/project_receipt/create_header_receipt.html',
                                         form=form,
                                         header=header,
                                         receipt_number=receipt_number,
                                         unpaid_amount=unpaid_amount)

                # 计算选中发票的总未收款金额
                selected_unpaid_total = 0
                selected_invoices_data = []
                for inv_id in selected_invoice_ids:
                    invoice = ProjectInvoice.query.get(inv_id)
                    if invoice:
                        inv_unpaid = invoice.unpaid_amount
                        if inv_unpaid > 0:
                            selected_unpaid_total += inv_unpaid
                            selected_invoices_data.append({'invoice': invoice, 'unpaid': inv_unpaid})

                if amount > selected_unpaid_total + 0.01:
                    flash(f'收款金额不能超过选中发票的未收款总额：{header.currency or "SGD"} {selected_unpaid_total:.2f}', 'error')
                    log_error(f'项目收款被拒 H{header.hid}(id={header_id})：收款金额 {amount:.2f} > 选中发票未收款合计 {selected_unpaid_total:.2f}，选中发票 {selected_invoice_ids}')
                    return render_template('business/projects/project_receipt/create_header_receipt.html',
                                         form=form,
                                         header=header,
                                         receipt_number=receipt_number,
                                         unpaid_amount=unpaid_amount)

                # 按比例分配给选中的发票
                distribution = []
                remaining_amount = amount
                for i, inv_data in enumerate(selected_invoices_data):
                    invoice = inv_data['invoice']
                    inv_unpaid = inv_data['unpaid']
                    if inv_unpaid > 0 and selected_unpaid_total > 0:
                        # 最后一张发票：分配所有剩余金额（避免浮点误差丢失）
                        if i == len(selected_invoices_data) - 1:
                            allocated = min(inv_unpaid, remaining_amount)
                        else:
                            # 按比例分配（用原始金额计算比例，而非递减的remaining）
                            allocated = min(inv_unpaid, round(amount * (inv_unpaid / selected_unpaid_total), 2))
                        if allocated > 0:
                            distribution.append({
                                'invoice_id': invoice.id,
                                'invoice_number': invoice.invoice_number,
                                'amount': allocated,
                                'method': 'manual'
                            })
                            remaining_amount -= allocated

                distribution_result = {
                    'success': True,
                    'distribution': distribution,
                    'remaining_amount': remaining_amount,
                    'total_unpaid': selected_unpaid_total
                }
            else:
                # 顺序分配：按发票日期顺序依次结算
                invoices = ProjectInvoice.query.filter_by(header_id=header_id).filter(
                    ProjectInvoice.status.in_(['confirmed', 'partial'])
                ).order_by(ProjectInvoice.invoice_date).all()

                distribution = []
                remaining_amount = amount
                total_unpaid = 0

                for invoice in invoices:
                    inv_unpaid = invoice.unpaid_amount
                    if inv_unpaid > 0:
                        total_unpaid += inv_unpaid
                        allocated = min(inv_unpaid, remaining_amount)
                        if allocated > 0:
                            distribution.append({
                                'invoice_id': invoice.id,
                                'invoice_number': invoice.invoice_number,
                                'amount': allocated,
                                'method': 'sequential'
                            })
                            remaining_amount -= allocated
                        if remaining_amount <= 0:
                            break

                distribution_result = {
                    'success': True,
                    'distribution': distribution,
                    'remaining_amount': remaining_amount,
                    'total_unpaid': total_unpaid
                }
            
            if not distribution_result.get('success', True) and distribution_result.get('message'):
                flash(distribution_result['message'], 'error')
                return render_template('business/projects/project_receipt/create_header_receipt.html',
                                     form=form,
                                     header=header,
                                     receipt_number=receipt_number,
                                     unpaid_amount=unpaid_amount)

            # 将 distribution 数组转换为 allocations 字典格式
            distribution_list = distribution_result.get('distribution', [])
            allocations = {}
            for dist_item in distribution_list:
                inv_id = dist_item.get('invoice_id')
                alloc_amount = dist_item.get('amount', 0)
                if inv_id and alloc_amount > 0:
                    allocations[inv_id] = alloc_amount

            # 一分钱都分配不出去时不能建记录：这种"孤儿收款"没有任何分配明细，
            # 各REF的已收算不到它头上（页面照旧显示未收款），却会被按原始金额计入
            # 项目已收，把后续收款全部挡在门外。
            if not allocations:
                flash('没有可分配的发票（发票可能已作废或已收满），收款记录未创建', 'error')
                log_error(f'项目收款被拒 H{header.hid}(id={header_id})：分配结果为空，'
                          f'金额={amount:.2f}，分配方式={distribution_method}')
                return render_template('business/projects/project_receipt/create_header_receipt.html',
                                     form=form,
                                     header=header,
                                     receipt_number=receipt_number,
                                     unpaid_amount=unpaid_amount)

            # 创建项目级别收款记录（不再设置 invoice_id）
            project_receipt = ProjectReceipt(
                receipt_number=receipt_number,
                ref_id=None,  # 项目级别收款记录，ref_id为None
                header_id=header.id,
                invoice_id=None,  # 不再使用直接关联，改用分配表
                amount=amount,
                currency=form.currency.data,
                payment_method=form.payment_method.data,
                payment_date=form.payment_date.data,
                payer_name=form.payer_name.data,
                payer_contact=form.payer_contact.data,
                payer_company=form.payer_company.data,
                bank_name=form.bank_name.data,
                account_number=form.account_number.data,
                transaction_id=form.transaction_id.data,
                remarks=form.remarks.data,
                status='confirmed'
            )

            # 在extra_info中存储分配信息（仅供显示参考）
            distribution_info = {
                'distribution_method': distribution_method,
                'allocations': allocations,
                'total_amount': amount,
                'remaining_amount': distribution_result.get('remaining_amount', 0),
                'selected_invoices': form.selected_invoices.data if distribution_method == 'manual' else None
            }
            project_receipt.extra_info = json.dumps(distribution_info)

            db.session.add(project_receipt)
            db.session.flush()

            # 创建分配记录
            for inv_id, alloc_amount in allocations.items():
                allocation = ReceiptInvoiceAllocation(
                    receipt_id=project_receipt.id,
                    invoice_id=inv_id,
                    allocated_amount=alloc_amount
                )
                db.session.add(allocation)
            db.session.flush()

            # 自动创建日记账分录（借：银行存款，贷：应收账款）
            # 用 SAVEPOINT 隔离：日记账失败只回滚这一小段，不会让整笔收款在最后 commit 时炸掉
            try:
                from App_new.finance.models.journal_entry import JournalEntry
                with db.session.begin_nested():
                    journal_entry = JournalEntry.create_from_receipt(
                        project_receipt,
                        user=current_user.username if current_user else None
                    )
                    if journal_entry and journal_entry.lines:
                        db.session.add(journal_entry)
                        # create_from_receipt 已置为 posted，只有还是草稿时才需要过账
                        # （原来无条件调用 post()，必定抛 "Only draft entries can be posted"）
                        if journal_entry.status == 'draft':
                            journal_entry.post(user=current_user.username if current_user else None)
            except Exception as je_error:
                # 日记账创建失败不影响收款记录，但必须留痕
                log_error(f'创建项目收款日记账失败 {receipt_number} H{header.hid}(id={header_id})', je_error)

            # 更新分配到的每张发票的已付金额
            for inv_id in allocations.keys():
                ProjectReceipt.update_invoice_paid_amount(inv_id)

            # 更新各个REF的付款状态（基于发票付款情况）
            for ref in header.refs:
                if ref.selling_price:
                    total_received = ProjectReceipt.get_ref_total_received(ref.id, header.id)
                    if total_received >= ref.selling_price:
                        ref.payment_status = 'paid'
                    elif total_received > 0:
                        ref.payment_status = 'partial'
                    else:
                        ref.payment_status = 'unpaid'

            db.session.commit()

            flash(f'收款记录 {receipt_number} 创建成功：{form.currency.data} {amount:.2f}', 'success')
            return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=header.id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
            log_error(f'创建项目收款失败 {receipt_number} H{header.hid}(id={header_id})', e)

    elif request.method == 'POST':
        # 表单校验没过：原来这里什么都不提示，页面静默重新渲染，用户以为"点了没反应"
        error_items = []
        for field_name, messages in form.errors.items():
            field = getattr(form, field_name, None)
            label = field.label.text if field is not None and field.label else field_name
            error_items.append(f'{label}: {"; ".join(messages)}')
        detail = ' | '.join(error_items) if error_items else '未知校验错误'
        flash(f'表单校验未通过 —— {detail}', 'error')
        log_error(f'项目收款表单校验未通过 H{header.hid}(id={header_id})：{detail}')

    # 获取项目的未付款金额
    unpaid_amount = ProjectReceipt.get_project_unpaid_amount(header_id)

    return render_template('business/projects/project_receipt/create_header_receipt.html',
                          form=form,
                          header=header,
                          receipt_number=receipt_number,
                          unpaid_amount=unpaid_amount)

@project_receipt.route('/header/<int:header_id>/receipt/<int:receipt_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@staff_only
def edit_header_receipt(header_id, receipt_id):
    """编辑项目级别收款记录"""
    header = ProjectHeader.query.get_or_404(header_id)
    receipt = ProjectReceipt.query.filter_by(
        id=receipt_id,
        header_id=header_id,
        ref_id=None
    ).first_or_404()

    form = ProjectLevelReceiptForm(obj=receipt)

    # 动态填充发票选择
    form.invoice_id.choices = get_invoice_choices(header_id)

    if form.validate_on_submit():
        try:
            # 获取旧的分配记录的发票ID列表
            old_allocation_invoice_ids = [a.invoice_id for a in receipt.invoice_allocations]

            # 处理发票ID（0表示不关联）
            new_invoice_id = form.invoice_id.data if form.invoice_id.data and form.invoice_id.data != 0 else None

            # 更新收款记录（不设置 invoice_id）
            receipt.amount = form.amount.data
            receipt.currency = form.currency.data
            receipt.payment_method = form.payment_method.data
            receipt.payment_date = form.payment_date.data
            receipt.payer_name = form.payer_name.data
            receipt.payer_contact = form.payer_contact.data
            receipt.payer_company = form.payer_company.data
            receipt.bank_name = form.bank_name.data
            receipt.account_number = form.account_number.data
            receipt.transaction_id = form.transaction_id.data
            receipt.remarks = form.remarks.data

            # 删除旧的分配记录
            ReceiptInvoiceAllocation.query.filter_by(receipt_id=receipt.id).delete()

            # 如果选择了新发票，创建新的分配记录
            if new_invoice_id:
                allocation = ReceiptInvoiceAllocation(
                    receipt_id=receipt.id,
                    invoice_id=new_invoice_id,
                    allocated_amount=form.amount.data
                )
                db.session.add(allocation)

            db.session.flush()

            # 更新所有受影响发票的已付金额
            affected_invoice_ids = set(old_allocation_invoice_ids)
            if new_invoice_id:
                affected_invoice_ids.add(new_invoice_id)
            for inv_id in affected_invoice_ids:
                ProjectReceipt.update_invoice_paid_amount(inv_id)

            db.session.commit()

            return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=header.id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            log_error(f'更新项目收款失败 {receipt.receipt_number}(id={receipt_id}) H{header.hid}(id={header_id})', e)

    # 获取项目的未付款金额
    unpaid_amount = ProjectReceipt.get_project_unpaid_amount(header_id)

    return render_template('business/projects/project_receipt/edit_header_receipt.html',
                         form=form,
                         header=header,
                         receipt=receipt,
                         unpaid_amount=unpaid_amount)

@project_receipt.route('/header/<int:header_id>/receipt/<int:receipt_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_header_receipt(header_id, receipt_id):
    """删除收款记录（支持项目级别和REF级别）"""
    receipt = ProjectReceipt.query.filter_by(
        id=receipt_id,
        header_id=header_id
    ).first_or_404()

    # 获取重定向目标（支持从收据列表页删除后返回列表页）
    next_url = request.args.get('next') or request.form.get('next')

    # 获取所有分配记录的发票ID（用于删除后更新）
    affected_invoice_ids = [a.invoice_id for a in receipt.invoice_allocations]
    ref_id = receipt.ref_id  # 保存REF ID

    try:
        # 冲销对应的日记账分录
        from App_new.finance.models.journal_entry import JournalEntry
        from flask_login import current_user

        journal_entry = JournalEntry.query.filter(
            JournalEntry.source_type == 'receipt',
            JournalEntry.source_id == receipt.id,
            JournalEntry.status == 'posted'
        ).first()

        if journal_entry:
            try:
                reversal = journal_entry.reverse(user=current_user.username if current_user else None)
                if reversal:
                    db.session.add(reversal)
            except Exception as je_err:
                log_error(f'冲销收款日记账失败 receipt_id={receipt_id}', je_err)

        # 删除分配记录
        ReceiptInvoiceAllocation.query.filter_by(receipt_id=receipt.id).delete()

        # 删除收款记录
        db.session.delete(receipt)
        db.session.flush()

        # 更新各个REF的付款状态
        header = ProjectHeader.query.get(header_id)
        for ref in header.refs:
            if ref.selling_price:
                # 使用辅助方法计算该REF的实际已收款总额
                total_received = ProjectReceipt.get_ref_total_received(ref.id, header.id)
                if total_received >= ref.selling_price:
                    ref.payment_status = 'paid'
                elif total_received > 0:
                    ref.payment_status = 'partial'
                else:
                    ref.payment_status = 'unpaid'

        # 更新所有受影响发票的已付金额
        for inv_id in affected_invoice_ids:
            ProjectReceipt.update_invoice_paid_amount(inv_id)

        db.session.commit()
        flash('收款记录删除成功！', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
        log_error(f'删除项目收款失败 receipt_id={receipt_id} header_id={header_id}', e)

    # 如果指定了next参数，跳转到指定页面；否则返回项目收款列表
    if next_url:
        return redirect(next_url)
    return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=header_id))


@project_receipt.route('/list', methods=['GET'])
@login_required
@staff_only
def receipt_list():
    """收据列表 - 参考 REF 列表，实现筛选、搜索与分页"""
    try:
        from sqlalchemy import and_, or_, desc, asc
        from datetime import datetime, timedelta, date

        # 筛选参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status = request.args.get('status', '').strip()
        payment_method = request.args.get('payment_method', '').strip()
        currency = request.args.get('currency', '').strip()
        header_id = request.args.get('header_id', None, type=int)
        ref_id_str = request.args.get('ref_id', '').strip()
        ref_id = int(ref_id_str) if ref_id_str and ref_id_str.isdigit() else None
        date_range = request.args.get('date_range', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        min_amount = request.args.get('min_amount', None, type=float)
        max_amount = request.args.get('max_amount', None, type=float)
        keyword = request.args.get('keyword', '').strip()
        sort_by = request.args.get('sort_by', 'payment_date').strip()
        sort_order = request.args.get('sort_order', 'desc').strip()
        match_status = request.args.get('match_status', '').strip()  # reconciled/matched/unmatched

        # 构建查询
        query = db.session.query(
            ProjectReceipt,
            ProjectHeader.hid.label('project_hid'),
            ProjectHeader.desc.label('project_name'),
            ProjectRef.ref_number.label('ref_number')
        ).join(
            ProjectHeader, ProjectReceipt.header_id == ProjectHeader.id, isouter=True
        ).join(
            ProjectRef, ProjectReceipt.ref_id == ProjectRef.id, isouter=True
        )

        filters = []
        if status:
            filters.append(ProjectReceipt.status == status)
        if payment_method:
            filters.append(ProjectReceipt.payment_method == payment_method)
        if currency:
            filters.append(ProjectReceipt.currency == currency)
        if header_id:
            filters.append(ProjectReceipt.header_id == header_id)
        if ref_id:
            filters.append(ProjectReceipt.ref_id == ref_id)

        # 日期区间（优先精确起止，其次快捷范围）
        if start_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                filters.append(ProjectReceipt.payment_date >= sd)
            except Exception:
                pass
        if end_date:
            try:
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
                filters.append(ProjectReceipt.payment_date <= ed)
            except Exception:
                pass
        if (not start_date and not end_date) and date_range:
            today = date.today()
            if date_range == 'today':
                filters.append(and_(ProjectReceipt.payment_date >= today, ProjectReceipt.payment_date < today + timedelta(days=1)))
            elif date_range == 'week':
                start = today - timedelta(days=today.weekday())
                end = start + timedelta(days=7)
                filters.append(and_(ProjectReceipt.payment_date >= start, ProjectReceipt.payment_date < end))
            elif date_range == 'month':
                start = today.replace(day=1)
                end = start.replace(year=start.year + 1, month=1, day=1) if start.month == 12 else start.replace(month=start.month + 1, day=1)
                filters.append(and_(ProjectReceipt.payment_date >= start, ProjectReceipt.payment_date < end))
            elif date_range == 'quarter':
                q = (today.month - 1) // 3
                start = today.replace(month=q * 3 + 1, day=1)
                end = start.replace(year=start.year + 1, month=1, day=1) if q == 3 else start.replace(month=q * 3 + 4, day=1)
                filters.append(and_(ProjectReceipt.payment_date >= start, ProjectReceipt.payment_date < end))
            elif date_range == 'year':
                start = today.replace(month=1, day=1)
                end = start.replace(year=start.year + 1)
                filters.append(and_(ProjectReceipt.payment_date >= start, ProjectReceipt.payment_date < end))

        if min_amount is not None and min_amount > 0:
            filters.append(ProjectReceipt.amount >= float(min_amount))
        if max_amount is not None and max_amount > 0:
            filters.append(ProjectReceipt.amount <= float(max_amount))

        if keyword:
            kw = f"%{keyword}%"
            filters.append(or_(
                ProjectReceipt.receipt_number.ilike(kw),
                ProjectReceipt.payer_name.ilike(kw),
                ProjectReceipt.payer_company.ilike(kw),
                ProjectReceipt.bank_name.ilike(kw),
                ProjectReceipt.account_number.ilike(kw),
                ProjectReceipt.transaction_id.ilike(kw),
                ProjectReceipt.remarks.ilike(kw),
                ProjectHeader.hid.ilike(kw),
                ProjectHeader.desc.ilike(kw),
                ProjectRef.ref_number.ilike(kw)
            ))

        # 匹配状态筛选
        if match_status:
            from App_new.finance.models.bank_transaction import BankTransaction
            if match_status == 'reconciled':
                # 已核对：is_reconciled = True
                filters.append(ProjectReceipt.is_reconciled == True)
            elif match_status == 'matched':
                # 已匹配但未核对：有关联银行流水但 is_reconciled = False
                matched_receipt_ids = db.session.query(BankTransaction.matched_receipt_id).filter(
                    BankTransaction.matched_receipt_id.isnot(None)
                ).distinct().subquery()
                filters.append(and_(
                    or_(ProjectReceipt.is_reconciled == False, ProjectReceipt.is_reconciled.is_(None)),
                    ProjectReceipt.id.in_(matched_receipt_ids)
                ))
            elif match_status == 'unmatched':
                # 待匹配：无关联银行流水且未核对
                matched_receipt_ids = db.session.query(BankTransaction.matched_receipt_id).filter(
                    BankTransaction.matched_receipt_id.isnot(None)
                ).distinct().subquery()
                filters.append(and_(
                    or_(ProjectReceipt.is_reconciled == False, ProjectReceipt.is_reconciled.is_(None)),
                    ~ProjectReceipt.id.in_(matched_receipt_ids)
                ))

        if filters:
            query = query.filter(and_(*filters))

        # 排序
        if sort_by == 'payment_date':
            order_col = ProjectReceipt.payment_date
        elif sort_by == 'amount':
            order_col = ProjectReceipt.amount
        elif sort_by == 'created_at':
            order_col = ProjectReceipt.created_at
        else:
            order_col = ProjectReceipt.payment_date
        query = query.order_by(asc(order_col) if sort_order == 'asc' else desc(order_col))

        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # 组织数据
        items = []
        for r, project_hid, project_name, ref_number in pagination.items:
            # 处理REF显示：如果是项目级别收据，从extra_info中提取分配的REF
            display_ref_number = ref_number
            if not ref_number and r.ref_id is None and r.extra_info:
                try:
                    distribution_info = json.loads(r.extra_info)
                    if 'distribution' in distribution_info:
                        ref_numbers = []
                        for dist in distribution_info['distribution']:
                            ref_id = dist.get('ref_id')
                            if ref_id:
                                ref = ProjectRef.query.get(ref_id)
                                if ref and ref.ref_number:
                                    ref_numbers.append(ref.ref_number)
                        if ref_numbers:
                            display_ref_number = ', '.join(ref_numbers[:3])  # 最多显示3个REF
                            if len(ref_numbers) > 3:
                                display_ref_number += f' ... (+{len(ref_numbers) - 3})'
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
            
            # 获取匹配状态和匹配详情
            matched_transactions = r.bank_transactions if hasattr(r, 'bank_transactions') else []
            is_matched = len(matched_transactions) > 0
            matched_tx_count = len(matched_transactions)
            # 获取匹配的银行流水信息（日期、金额、对方）
            matched_tx_info = []
            for tx in matched_transactions[:3]:  # 最多显示3条
                matched_tx_info.append({
                    'date': tx.transaction_date.strftime('%m-%d') if tx.transaction_date else '',
                    'amount': float(tx.amount) if tx.amount else 0,
                    'counterparty': tx.counterparty_name or (tx.description[:20] if tx.description else '')
                })

            items.append({
                'id': r.id,
                'receipt_number': r.receipt_number,
                'header_id': r.header_id,  # 添加项目ID，用于生成跳转链接
                'ref_id': r.ref_id,  # 添加REF ID，用于生成编辑链接
                'project_hid': project_hid,
                'project_name': project_name,
                'ref_number': display_ref_number,  # 使用处理后的REF显示
                'amount': float(r.amount) if r.amount is not None else 0,
                'currency': r.currency,
                'payment_method': r.payment_method,
                'payment_method_display': r.payment_method_display,
                'payment_date': r.payment_date,
                'payer_name': r.payer_name,
                'payer_company': r.payer_company,
                'status': r.status,
                'status_display': r.status_display,
                'transaction_id': r.transaction_id,
                'remarks': r.remarks,
                'created_at': r.created_at,
                'is_reconciled': r.is_reconciled,
                'is_matched': is_matched,
                'matched_tx_count': matched_tx_count,
                'matched_tx_info': matched_tx_info
            })

        payment_methods = [
            ('', '全部'),
            ('cash', '现金'),
            ('bank_transfer', '银行转账'),
            ('credit_card', '信用卡'),
            ('cheque', '支票'),
            ('other', '其他')
        ]
        statuses = [
            ('', '全部'),
            ('pending', '待确认'),
            ('confirmed', '已确认'),
            ('cancelled', '已取消')
        ]

        return render_template(
            'business/projects/project_receipt/receipt_list.html',
            receipts=items,
            pagination=pagination,
            payment_methods=payment_methods,
            statuses=statuses,
            current_filters={
                'status': status,
                'payment_method': payment_method,
                'currency': currency,
                'header_id': str(header_id) if header_id else '',
                'ref_id': ref_id_str if ref_id_str else '',
                'date_range': date_range,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount,
                'keyword': keyword,
                'sort_by': sort_by,
                'sort_order': sort_order,
                'per_page': per_page,
                'match_status': match_status
            }
        )
    except Exception as e:
        db.session.rollback()
        flash(f'收据列表加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))

@project_receipt.route('/api/header/<int:header_id>/unpaid_refs')
@login_required
@staff_only
def get_header_unpaid_refs(header_id):
    """获取项目下各REF的未收款详情 - API接口"""
    header = ProjectHeader.query.get_or_404(header_id)
    
    unpaid_refs = []
    total_unpaid = 0
    
    for ref in header.refs:
        # 未开票的REF不产生应收款，不列入未收款清单
        if ref.selling_price and ref.is_invoiced:
            # 使用辅助方法计算该REF的已收款总额
            ref_received = ProjectReceipt.get_ref_total_received(ref.id, header_id)
            ref_unpaid = float(ref.selling_price) - ref_received
            
            if ref_unpaid > 0:
                unpaid_refs.append({
                    'ref_id': ref.id,
                    'ref_number': ref.ref_number,
                    'ref_name': ref.description or ref.detailed_description or '其他服务',
                    'ref_type': ref.ref_type.name if ref.ref_type else '未分类',
                    'selling_price': float(ref.selling_price),
                    'received_amount': ref_received,
                    'unpaid_amount': ref_unpaid,
                    'unpaid_percentage': (ref_unpaid / float(ref.selling_price)) * 100
                })
                total_unpaid += ref_unpaid
    
    return jsonify({
        'success': True,
        'header_id': header_id,
        'header_hid': header.hid,
        'total_unpaid': total_unpaid,
        'unpaid_refs': unpaid_refs
    })


# === 按公司收款流程 ===

@project_receipt.route('/by-company', methods=['GET', 'POST'])
@login_required
@staff_only
def receipt_by_company():
    """按公司收款页面 - 搜索公司和发票，创建收款"""
    from App_new.business.projects.models.project import CustomerCompany
    from App_new.business.projects.forms.receipt_forms import CompanyReceiptForm
    from datetime import datetime

    # 获取所有活跃公司（用于下拉选择）
    companies = CustomerCompany.query.filter_by(status='active').order_by(
        CustomerCompany.company_name
    ).all()

    form = CompanyReceiptForm()
    # 设置空的 choices 避免验证错误
    form.selected_invoices.choices = []
    receipt_number = ProjectReceipt.generate_receipt_number()

    # 搜索参数
    selected_company_id = request.args.get('company_id', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    payment_status = request.args.get('payment_status', 'all')  # 付款状态筛选

    # 搜索结果
    unpaid_invoices = []
    selected_company = None
    total_unpaid = 0

    if selected_company_id:
        selected_company = CustomerCompany.query.get(selected_company_id)
        if selected_company:
            # 查询未付发票（已确认且未全额付款）
            query = ProjectInvoice.query.join(ProjectHeader).filter(
                ProjectHeader.company_id == selected_company_id,
                ProjectInvoice.status == 'confirmed'
            )

            # 付款状态筛选
            if payment_status == 'unpaid':
                query = query.filter(ProjectInvoice.payment_status == 'unpaid')
            elif payment_status == 'partial_paid':
                query = query.filter(ProjectInvoice.payment_status == 'partial_paid')
            else:  # 'all' - 显示所有未付和部分付款
                query = query.filter(ProjectInvoice.payment_status.in_(['unpaid', 'partial_paid']))

            # 日期筛选
            if date_from:
                try:
                    df = datetime.strptime(date_from, '%Y-%m-%d').date()
                    query = query.filter(ProjectInvoice.invoice_date >= df)
                except ValueError:
                    pass
            if date_to:
                try:
                    dt = datetime.strptime(date_to, '%Y-%m-%d').date()
                    query = query.filter(ProjectInvoice.invoice_date <= dt)
                except ValueError:
                    pass

            unpaid_invoices = query.order_by(ProjectInvoice.invoice_date.asc()).all()
            total_unpaid = sum(inv.unpaid_amount for inv in unpaid_invoices)

    # 处理表单提交
    if request.method == 'POST':
        try:
            # 从 request.form 获取数据（绕过 SelectMultipleField 验证）
            amount = float(request.form.get('amount', 0))
            selected_invoice_ids = request.form.getlist('selected_invoices', type=int)
            allocation_amounts = request.form.getlist('allocation_amounts', type=float)
            distribution_method = request.form.get('distribution_method', 'sequential')

            if not selected_invoice_ids:
                flash('请选择至少一张发票', 'error')
            else:
                # 如果有手动分配金额，使用手动分配
                if allocation_amounts and len(allocation_amounts) == len(selected_invoice_ids):
                    # 手动分配模式 - 添加验证
                    allocations = {}
                    validation_error = None
                    for inv_id, alloc_amount in zip(selected_invoice_ids, allocation_amounts):
                        if alloc_amount > 0:
                            # 验证分配金额不超过发票未付金额
                            invoice = ProjectInvoice.query.get(inv_id)
                            if invoice:
                                unpaid = float(invoice.unpaid_amount or 0)
                                if alloc_amount > unpaid + 0.01:
                                    validation_error = f'发票 {invoice.invoice_number} 分配金额({alloc_amount:.2f})超过未付金额({unpaid:.2f})'
                                    break
                            allocations[inv_id] = alloc_amount

                    if validation_error:
                        flash(validation_error, 'error')
                        distribution_result = {'success': False}
                    else:
                        distribution_result = {
                            'success': True,
                            'allocations': allocations,
                            'total_allocated': sum(allocations.values())
                        }
                        # 更新实际收款金额
                        amount = distribution_result['total_allocated']
                else:
                    # 自动分配模式
                    distribution_result = ProjectReceipt.distribute_to_invoices(
                        amount, selected_invoice_ids, distribution_method
                    )

                if not distribution_result['success']:
                    flash(distribution_result['message'], 'error')
                else:
                    # 获取第一张发票的header_id
                    first_invoice = ProjectInvoice.query.get(selected_invoice_ids[0])

                    # 从 request.form 获取表单数据
                    from datetime import datetime
                    payment_date_str = request.form.get('payment_date', '')
                    payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else None

                    # 创建收款记录
                    receipt = ProjectReceipt(
                        receipt_number=receipt_number,
                        ref_id=None,
                        header_id=first_invoice.header_id,
                        invoice_id=None,
                        amount=amount,
                        currency=request.form.get('currency', 'SGD'),
                        payment_method=request.form.get('payment_method', 'bank_transfer'),
                        payment_date=payment_date,
                        payer_name=request.form.get('payer_name', ''),
                        payer_contact=request.form.get('payer_contact', ''),
                        payer_company=selected_company.company_name if selected_company else '',
                        bank_name=request.form.get('bank_name', ''),
                        account_number=request.form.get('account_number', ''),
                        transaction_id=request.form.get('transaction_id', ''),
                        remarks=request.form.get('remarks', ''),
                        status='confirmed'
                    )

                    # 存储分配信息
                    allocation_info = {
                        'allocation_type': 'company_invoices',
                        'company_id': selected_company_id,
                        'company_name': selected_company.company_name if selected_company else '',
                        'distribution_method': distribution_method,
                        'invoice_allocations': [
                            {'invoice_id': inv_id, 'amount': alloc_amount}
                            for inv_id, alloc_amount in distribution_result['allocations'].items()
                        ]
                    }
                    receipt.extra_info = json.dumps(allocation_info)

                    db.session.add(receipt)
                    db.session.flush()

                    # 自动创建日记账分录（借：银行存款，贷：应收账款）
                    try:
                        from App_new.finance.models.journal_entry import JournalEntry
                        journal_entry = JournalEntry.create_from_receipt(
                            receipt,
                            user=current_user.username if current_user else None
                        )
                        if journal_entry and journal_entry.lines:
                            db.session.add(journal_entry)
                            # 自动过账
                            journal_entry.post(user=current_user.username if current_user else None)
                    except Exception as je_error:
                        # 日记账创建失败不影响收款记录
                        import logging
                        logging.getLogger(__name__).warning(f"创建公司收款日记账失败: {str(je_error)}")

                    # 创建分配记录
                    for invoice_id, allocated_amount in distribution_result['allocations'].items():
                        allocation = ReceiptInvoiceAllocation(
                            receipt_id=receipt.id,
                            invoice_id=invoice_id,
                            allocated_amount=allocated_amount
                        )
                        db.session.add(allocation)

                    db.session.flush()

                    # 更新发票已付金额
                    for invoice_id in distribution_result['allocations'].keys():
                        ProjectReceipt.update_invoice_paid_amount_from_allocations(invoice_id)

                    # 更新涉及项目的REF payment_status
                    header_ids = set()
                    for invoice_id in distribution_result['allocations'].keys():
                        inv = ProjectInvoice.query.get(invoice_id)
                        if inv:
                            header_ids.add(inv.header_id)
                    for header_id in header_ids:
                        ProjectReceipt.update_header_refs_payment_status(header_id)

                    db.session.commit()

                    # 跳转回按公司收款页面，保留公司ID
                    return redirect(url_for('business_projects.project_receipt.receipt_by_company', company_id=selected_company_id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')

    from datetime import date
    return render_template('business/projects/project_receipt/receipt_by_company.html',
                          companies=companies,
                          form=form,
                          receipt_number=receipt_number,
                          selected_company_id=selected_company_id,
                          selected_company=selected_company,
                          date_from=date_from,
                          date_to=date_to,
                          payment_status=payment_status,
                          unpaid_invoices=unpaid_invoices,
                          total_unpaid=total_unpaid,
                          today=date.today().strftime('%Y-%m-%d'))


@project_receipt.route('/api/company/<int:company_id>/unpaid_invoices', methods=['GET'])
@login_required
@staff_only
def get_company_unpaid_invoices(company_id):
    """获取公司的未付发票列表 - API接口"""
    from App_new.business.projects.models.project import CustomerCompany

    company = CustomerCompany.query.get_or_404(company_id)
    invoices = ProjectInvoice.get_company_unpaid_invoices(company_id)

    invoice_list = []
    total_unpaid = 0

    for inv in invoices:
        unpaid = inv.unpaid_amount
        total_unpaid += unpaid
        invoice_list.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'invoice_date': inv.invoice_date.strftime('%Y-%m-%d') if inv.invoice_date else '',
            'due_date': inv.due_date.strftime('%Y-%m-%d') if inv.due_date else '',
            'amount': float(inv.amount),
            'paid_amount': float(inv.paid_amount or 0),
            'unpaid_amount': unpaid,
            'currency': inv.currency,
            'status': inv.status,
            'status_display': inv.status_display,
            'is_overdue': inv.is_overdue,
            'header_id': inv.header_id,
            'project_hid': inv.header.hid if inv.header else '',
            'project_desc': inv.header.desc if inv.header else ''
        })

    return jsonify({
        'success': True,
        'company_id': company_id,
        'company_name': company.company_name,
        'invoices': invoice_list,
        'total_unpaid': total_unpaid,
        'invoice_count': len(invoice_list)
    })


@project_receipt.route('/company/<int:company_id>/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_company_receipt(company_id):
    """按公司创建收款 - 选择发票并分配"""
    from App_new.business.projects.models.project import CustomerCompany
    from App_new.business.projects.forms.receipt_forms import CompanyReceiptForm

    company = CustomerCompany.query.get_or_404(company_id)

    # 获取公司未付发票
    unpaid_invoices = ProjectInvoice.get_company_unpaid_invoices(company_id)

    # 检查是否有未付发票
    if not unpaid_invoices:
        flash('该公司没有未付款的发票，无法创建收款记录', 'warning')
        return redirect(url_for('business_projects.project_receipt.receipt_list'))

    form = CompanyReceiptForm()

    # 动态生成发票选择选项
    invoice_choices = [(inv.id, f"{inv.invoice_number} - {inv.currency} {float(inv.amount):.2f} (未付: {inv.unpaid_amount:.2f})")
                       for inv in unpaid_invoices]
    form.selected_invoices.choices = invoice_choices if invoice_choices else [(0, "暂无未付发票")]

    receipt_number = ProjectReceipt.generate_receipt_number()

    if form.validate_on_submit():
        try:
            amount = float(form.amount.data)
            # 从请求中获取选中的发票ID
            selected_invoice_ids = request.form.getlist('selected_invoices', type=int)
            distribution_method = form.distribution_method.data

            # 验证选择
            if not selected_invoice_ids or (len(selected_invoice_ids) == 1 and selected_invoice_ids[0] == 0):
                flash('请选择至少一张发票', 'error')
                return render_template('business/projects/project_receipt/create_company_receipt.html',
                                     form=form, company=company, receipt_number=receipt_number,
                                     unpaid_invoices=unpaid_invoices,
                                     total_unpaid=sum(inv.unpaid_amount for inv in unpaid_invoices))

            # 计算分配
            distribution_result = ProjectReceipt.distribute_to_invoices(
                amount, selected_invoice_ids, distribution_method
            )

            if not distribution_result['success']:
                flash(distribution_result['message'], 'error')
                return render_template('business/projects/project_receipt/create_company_receipt.html',
                                     form=form, company=company, receipt_number=receipt_number,
                                     unpaid_invoices=unpaid_invoices,
                                     total_unpaid=sum(inv.unpaid_amount for inv in unpaid_invoices))

            # 创建收款记录（使用第一张发票的header_id）
            first_invoice = ProjectInvoice.query.get(selected_invoice_ids[0])

            receipt = ProjectReceipt(
                receipt_number=receipt_number,
                ref_id=None,
                header_id=first_invoice.header_id,
                invoice_id=None,  # 不使用直接关联，改用分配表
                amount=amount,
                currency=form.currency.data,
                payment_method=form.payment_method.data,
                payment_date=form.payment_date.data,
                payer_name=form.payer_name.data or company.contact_person,
                payer_contact=form.payer_contact.data,
                payer_company=company.company_name,
                bank_name=form.bank_name.data,
                account_number=form.account_number.data,
                transaction_id=form.transaction_id.data,
                remarks=form.remarks.data,
                status='confirmed'
            )

            # 存储分配信息到 extra_info
            allocation_info = {
                'allocation_type': 'company_invoices',
                'company_id': company_id,
                'company_name': company.company_name,
                'distribution_method': distribution_method,
                'invoice_allocations': [
                    {'invoice_id': inv_id, 'amount': alloc_amount}
                    for inv_id, alloc_amount in distribution_result['allocations'].items()
                ]
            }
            receipt.extra_info = json.dumps(allocation_info)

            db.session.add(receipt)
            db.session.flush()

            # 自动创建日记账分录（借：银行存款，贷：应收账款）
            try:
                from App_new.finance.models.journal_entry import JournalEntry
                journal_entry = JournalEntry.create_from_receipt(
                    receipt,
                    user=current_user.username if current_user else None
                )
                if journal_entry and journal_entry.lines:
                    db.session.add(journal_entry)
                    # 自动过账
                    journal_entry.post(user=current_user.username if current_user else None)
            except Exception as je_error:
                # 日记账创建失败不影响收款记录
                import logging
                logging.getLogger(__name__).warning(f"创建公司收款日记账失败: {str(je_error)}")

            # 创建分配记录
            for invoice_id, allocated_amount in distribution_result['allocations'].items():
                allocation = ReceiptInvoiceAllocation(
                    receipt_id=receipt.id,
                    invoice_id=invoice_id,
                    allocated_amount=allocated_amount
                )
                db.session.add(allocation)

            db.session.flush()

            # 更新各发票的已付金额和状态
            for invoice_id in distribution_result['allocations'].keys():
                ProjectReceipt.update_invoice_paid_amount_from_allocations(invoice_id)

            # 更新涉及项目的REF payment_status
            header_ids = set()
            for invoice_id in distribution_result['allocations'].keys():
                inv = ProjectInvoice.query.get(invoice_id)
                if inv:
                    header_ids.add(inv.header_id)
            for header_id in header_ids:
                ProjectReceipt.update_header_refs_payment_status(header_id)

            db.session.commit()

            # 跳转回按公司收款页面
            return redirect(url_for('business_projects.project_receipt.receipt_by_company', company_id=company_id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')

    # 计算总未付金额
    total_unpaid = sum(inv.unpaid_amount for inv in unpaid_invoices)

    return render_template('business/projects/project_receipt/create_company_receipt.html',
                          form=form,
                          company=company,
                          receipt_number=receipt_number,
                          unpaid_invoices=unpaid_invoices,
                          total_unpaid=total_unpaid)


@project_receipt.route('/api/preview-allocation', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def preview_allocation():
    """预览收款分配结果 - API接口"""
    data = request.get_json()
    amount = float(data.get('amount', 0))
    invoice_ids = data.get('invoice_ids', [])
    distribution_method = data.get('distribution_method', 'sequential')

    if not invoice_ids or amount <= 0:
        return jsonify({'success': False, 'message': '请输入金额并选择发票'})

    result = ProjectReceipt.distribute_to_invoices(amount, invoice_ids, distribution_method)

    if result['success']:
        # 添加发票详情（按invoice_id索引）
        allocation_details = {}
        for inv_id, alloc_amount in result['allocations'].items():
            invoice = ProjectInvoice.query.get(inv_id)
            if invoice:
                allocation_details[inv_id] = {
                    'invoice_id': inv_id,
                    'invoice_number': invoice.invoice_number,
                    'invoice_amount': float(invoice.amount),
                    'unpaid_amount': invoice.unpaid_amount,
                    'allocated_amount': alloc_amount,
                    'unpaid_after': invoice.unpaid_amount - alloc_amount
                }
        result['allocation_details'] = allocation_details

    return jsonify(result)


@project_receipt.route('/api/batch-invoice-init', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def batch_invoice_init():
    """批量收款初始化数据 - API接口（供弹窗使用）"""
    from datetime import date
    data = request.get_json()
    invoice_ids = data.get('invoice_ids', [])

    if not invoice_ids:
        return jsonify({'success': False, 'message': '请选择要收款的发票'})

    invoices = ProjectInvoice.query.filter(
        ProjectInvoice.id.in_(invoice_ids),
        ProjectInvoice.payment_status != 'paid'
    ).all()

    if not invoices:
        return jsonify({'success': False, 'message': '没有找到可收款的发票'})

    invoice_data = []
    total_unpaid = 0
    currencies = set()

    for inv in invoices:
        unpaid = float(inv.amount or 0) - float(inv.paid_amount or 0)
        total_unpaid += unpaid
        currencies.add(inv.currency)
        header = ProjectHeader.query.get(inv.header_id)
        invoice_data.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'project_hid': header.hid if header else '',
            'customer_name': inv.customer_name,
            'amount': float(inv.amount or 0),
            'paid_amount': float(inv.paid_amount or 0),
            'unpaid_amount': unpaid,
            'currency': inv.currency,
            'payment_status_display': inv.payment_status_display
        })

    receipt_number = ProjectReceipt.generate_receipt_number()
    multi_currency = len(currencies) > 1
    default_currency = list(currencies)[0] if len(currencies) == 1 else 'SGD'

    return jsonify({
        'success': True,
        'invoices': invoice_data,
        'total_unpaid': round(total_unpaid, 2),
        'receipt_number': receipt_number,
        'multi_currency': multi_currency,
        'default_currency': default_currency,
        'today': date.today().isoformat()
    })


@project_receipt.route('/batch-invoice-receipt', methods=['GET'])
@login_required
@staff_only
def batch_invoice_receipt():
    """批量发票收款页面"""
    from datetime import date

    # 获取选中的发票ID列表
    invoice_ids_str = request.args.get('invoice_ids', '')
    if not invoice_ids_str:
        flash('请选择要收款的发票', 'error')
        return redirect(url_for('business_projects.project_invoice.invoice_list'))

    try:
        invoice_ids = [int(id) for id in invoice_ids_str.split(',') if id.strip()]
    except ValueError:
        flash('发票ID格式错误', 'error')
        return redirect(url_for('business_projects.project_invoice.invoice_list'))

    if not invoice_ids:
        flash('请选择要收款的发票', 'error')
        return redirect(url_for('business_projects.project_invoice.invoice_list'))

    # 查询选中的发票
    invoices = ProjectInvoice.query.filter(
        ProjectInvoice.id.in_(invoice_ids),
        ProjectInvoice.payment_status != 'paid'
    ).all()

    if not invoices:
        flash('没有找到可收款的发票', 'error')
        return redirect(url_for('business_projects.project_invoice.invoice_list'))

    # 组织发票数据
    invoice_data = []
    total_unpaid = 0
    currencies = set()

    for inv in invoices:
        unpaid = float(inv.amount or 0) - float(inv.paid_amount or 0)
        total_unpaid += unpaid
        currencies.add(inv.currency)

        # 获取项目信息
        header = ProjectHeader.query.get(inv.header_id)

        invoice_data.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'header_id': inv.header_id,
            'project_hid': header.hid if header else '',
            'project_name': header.desc if header else '',
            'customer_name': inv.customer_name,
            'customer_company': inv.customer_company,
            'amount': float(inv.amount or 0),
            'paid_amount': float(inv.paid_amount or 0),
            'unpaid_amount': unpaid,
            'currency': inv.currency,
            'invoice_date': inv.invoice_date,
            'payment_status': inv.payment_status,
            'payment_status_display': inv.payment_status_display
        })

    # 生成收款单号
    receipt_number = ProjectReceipt.generate_receipt_number()

    # 检查货币是否一致
    multi_currency = len(currencies) > 1
    default_currency = list(currencies)[0] if len(currencies) == 1 else 'SGD'

    return render_template('business/projects/project_receipt/batch_invoice_receipt.html',
                         invoices=invoice_data,
                         total_unpaid=total_unpaid,
                         receipt_number=receipt_number,
                         multi_currency=multi_currency,
                         default_currency=default_currency,
                         today=date.today().isoformat())


@project_receipt.route('/batch-invoice-receipt/submit', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def batch_invoice_receipt_submit():
    """批量发票收款提交"""
    try:
        from datetime import datetime

        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])
        amount = float(data.get('amount', 0))
        currency = data.get('currency', 'SGD')
        payment_method = data.get('payment_method', 'bank_transfer')
        payment_date_str = data.get('payment_date')
        payer_name = data.get('payer_name', '')
        payer_contact = data.get('payer_contact', '')
        payer_company = data.get('payer_company', '')
        bank_name = data.get('bank_name', '')
        account_number = data.get('account_number', '')
        transaction_id = data.get('transaction_id', '')
        remarks = data.get('remarks', '')
        distribution_method = data.get('distribution_method', 'sequential')

        if not invoice_ids:
            return jsonify({'success': False, 'message': '请选择要收款的发票'}), 400

        if amount <= 0:
            return jsonify({'success': False, 'message': '收款金额必须大于0'}), 400

        if not payment_date_str:
            return jsonify({'success': False, 'message': '请选择收款日期'}), 400

        if not bank_name:
            return jsonify({'success': False, 'message': '请填写银行名称'}), 400

        # 解析日期
        payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()

        # 查询发票
        invoices = ProjectInvoice.query.filter(
            ProjectInvoice.id.in_(invoice_ids),
            ProjectInvoice.payment_status != 'paid'
        ).order_by(ProjectInvoice.invoice_date.asc()).all()

        if not invoices:
            return jsonify({'success': False, 'message': '没有找到可收款的发票'}), 400

        # 使用分配方法分配金额
        result = ProjectReceipt.distribute_to_invoices(amount, invoice_ids, distribution_method)

        if not result['success']:
            return jsonify({'success': False, 'message': result.get('message', '分配失败')}), 400

        allocations = result['allocations']

        # 获取第一张发票的header_id作为收款记录的项目ID
        first_invoice = invoices[0]

        # 生成收款单号（只生成一个）
        receipt_number = ProjectReceipt.generate_receipt_number()

        # 存储分配信息
        allocation_info = {
            'allocation_type': 'batch_invoices',
            'distribution_method': distribution_method,
            'invoice_allocations': [
                {'invoice_id': inv_id, 'amount': alloc_amount}
                for inv_id, alloc_amount in allocations.items()
            ]
        }

        # 创建一个收款记录（多个发票共用一个收款单号）
        receipt = ProjectReceipt(
            receipt_number=receipt_number,
            header_id=first_invoice.header_id,
            invoice_id=None,  # 不再使用直接关联，改用分配表
            amount=amount,  # 总金额
            currency=currency,
            payment_method=payment_method,
            payment_date=payment_date,
            payer_name=payer_name,
            payer_contact=payer_contact,
            payer_company=payer_company,
            bank_name=bank_name,
            account_number=account_number,
            transaction_id=transaction_id,
            remarks=remarks,
            status='confirmed',
            extra_info=json.dumps(allocation_info)
        )
        db.session.add(receipt)
        db.session.flush()

        # 为每个发票创建分配记录
        allocated_invoices = []
        for inv in invoices:
            alloc_amount = allocations.get(inv.id, 0)
            if alloc_amount <= 0:
                continue

            # 创建分配记录
            allocation = ReceiptInvoiceAllocation(
                receipt_id=receipt.id,
                invoice_id=inv.id,
                allocated_amount=alloc_amount
            )
            db.session.add(allocation)

            allocated_invoices.append({
                'invoice_number': inv.invoice_number,
                'amount': alloc_amount,
                'header_id': inv.header_id
            })

        db.session.flush()

        # 更新发票已付金额
        for inv in invoices:
            if allocations.get(inv.id, 0) > 0:
                ProjectReceipt.update_invoice_paid_amount(inv.id)

        # 创建日记账分录
        try:
            from App_new.finance.models.journal_entry import JournalEntry
            journal_entry = JournalEntry.create_from_receipt(
                receipt,
                user=current_user.username if current_user else None
            )
            if journal_entry and journal_entry.lines:
                db.session.add(journal_entry)
                journal_entry.post(user=current_user.username if current_user else None)
        except Exception as je_error:
            import logging
            logging.getLogger(__name__).warning(f"创建收款日记账失败: {str(je_error)}")

        # 更新所有涉及项目的REF payment_status
        header_ids = set(inv['header_id'] for inv in allocated_invoices)
        for header_id in header_ids:
            ProjectReceipt.update_header_refs_payment_status(header_id)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功创建收款记录 {receipt_number}，分配到 {len(allocated_invoices)} 张发票',
            'receipt_number': receipt_number,
            'allocated_invoices': allocated_invoices
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'收款失败：{str(e)}'}), 500
