from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.exts import csrf, db
from App_new.business.projects.forms.receipt_forms import ProjectReceiptForm, ProjectLevelReceiptForm
from App_new.utils.decorators import staff_only, admin_only
import json

project_receipt = Blueprint('project_receipt', __name__)

@project_receipt.route('/create/<int:ref_id>', methods=['GET', 'POST'])
def create_receipt(ref_id):
    """创建REF级别收款记录"""
    ref = ProjectRef.query.get_or_404(ref_id)
    form = ProjectReceiptForm()
    
    # 预填充收款单号
    receipt_number = ProjectReceipt.generate_receipt_number()
    
    if form.validate_on_submit():
        try:
            # 创建收款记录
            receipt = ProjectReceipt(
                receipt_number=receipt_number,
                ref_id=ref.id,
                header_id=ref.header_id,
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
            
            # 先提交收款记录，然后更新REF的付款状态
            db.session.flush()  # 刷新session，获取receipt.id
            
            # 重新查询REF以获取最新的收款记录
            ref = ProjectRef.query.get(ref_id)
            
            # 更新REF的付款状态
            # 计算总收款金额（包括新创建的收款记录）
            total_received = sum(float(r.amount) for r in ref.receipts if r.status == 'confirmed')
            if total_received >= ref.selling_price:
                ref.payment_status = 'paid'
            elif total_received > 0:
                ref.payment_status = 'partial'
            else:
                ref.payment_status = 'unpaid'
            
            db.session.commit()
            
            return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    
    # 获取REF的未付款金额
    total_received = sum(float(r.amount) for r in ref.receipts if r.status == 'confirmed')
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
    
    if form.validate_on_submit():
        try:
            # 更新收款记录
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
            
            # 先提交收款记录更新
            db.session.flush()
            
            # 重新查询REF以获取最新的收款记录
            if receipt.ref_id:
                ref = ProjectRef.query.get(receipt.ref_id)
                
                # 更新REF的付款状态
                # 计算总收款金额（只计算已确认的收款记录）
                total_received = sum(float(r.amount) for r in ref.receipts if r.status == 'confirmed')
                if total_received >= ref.selling_price:
                    ref.payment_status = 'paid'
                elif total_received > 0:
                    ref.payment_status = 'partial'
                else:
                    ref.payment_status = 'unpaid'
            
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
    
    try:
        # 先删除收款记录
        db.session.delete(receipt)
        db.session.flush()
        
        # 重新查询REF以获取最新的收款记录
        if receipt.ref_id:
            ref = ProjectRef.query.get(receipt.ref_id)
            
            # 更新REF的付款状态
            # 计算总收款金额（只计算已确认的收款记录）
            total_received = sum(float(r.amount) for r in ref.receipts if r.status == 'confirmed')
            if total_received >= ref.selling_price:
                ref.payment_status = 'paid'
            elif total_received > 0:
                ref.payment_status = 'partial'
            else:
                ref.payment_status = 'unpaid'
        
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
    
    try:
        receipt.status = status
        
        # 先提交收款记录状态更新
        db.session.flush()
        
        # 重新查询REF以获取最新的收款记录
        if receipt.ref_id:
            ref = ProjectRef.query.get(receipt.ref_id)
            
            # 更新REF的付款状态
            # 计算总收款金额（只计算已确认的收款记录）
            total_received = sum(float(r.amount) for r in ref.receipts if r.status == 'confirmed')
            if total_received >= ref.selling_price:
                ref.payment_status = 'paid'
            elif total_received > 0:
                ref.payment_status = 'partial'
            else:
                ref.payment_status = 'unpaid'
        
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
    
    return jsonify({
        'success': True,
        'receipts': [receipt.to_dict() for receipt in receipts],
        'total_received': sum(float(r.amount) for r in receipts if r.status == 'confirmed'),
        'unpaid_amount': float(ref.selling_price or 0) - sum(float(r.amount) for r in receipts if r.status == 'confirmed')
    })

@project_receipt.route('/ref/<int:ref_id>/receipts')
def ref_receipts(ref_id):
    """查看REF的收款记录列表"""
    ref = ProjectRef.query.get_or_404(ref_id)
    receipts = ProjectReceipt.query.filter_by(ref_id=ref_id).order_by(ProjectReceipt.created_at.desc()).all()
    
    # 计算已收款和未收款金额
    total_received = sum(float(r.amount) for r in receipts if r.status == 'confirmed')
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
                                    'name': ref.name or ref.description,
                                    'amount': dist.get('amount', 0)
                                })
                receipt.distributed_refs = distributed_refs
            except (json.JSONDecodeError, KeyError, TypeError):
                receipt.distributed_refs = []
        else:
            receipt.distributed_refs = []
    
    # 统计所有REF的实际已收款金额（包括项目级别分配）
    total_received = 0
    for ref in header.refs:
        if ref.selling_price:
            total_received += ProjectReceipt.get_ref_total_received(ref.id, header_id)
    unpaid_amount = float(header.total_selling_amount or 0) - total_received
    
    return render_template('business/projects/project_receipt/header_receipts.html',
                         header=header,
                         all_receipts=all_receipts,
                         total_received=total_received,
                         unpaid_amount=unpaid_amount)

@project_receipt.route('/header/<int:header_id>/receipt/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_header_receipt(header_id):
    """创建项目级别收款记录"""
    header = ProjectHeader.query.get_or_404(header_id)
    form = ProjectLevelReceiptForm()
    
    # 动态生成REF选择选项
    unpaid_refs = []
    for ref in header.refs:
        if ref.selling_price:
            # 计算该REF的未收款金额
            total_received = ProjectReceipt.get_ref_total_received(ref.id, header_id)
            ref_unpaid = float(ref.selling_price) - total_received
            if ref_unpaid > 0:
                unpaid_refs.append((ref.id, f"{ref.ref_number} - {ref.name or ref.description} (未收款: {ref.currency or 'SGD'} {ref_unpaid:.2f})"))
    
    form.selected_refs.choices = unpaid_refs
    
    # 如果没有未付款的REF，添加一个提示选项
    if not unpaid_refs:
        form.selected_refs.choices = [(0, "暂无未付款的REF")]
    
    # 预填充收款单号
    receipt_number = ProjectReceipt.generate_receipt_number()
    
    if form.validate_on_submit():
        try:
            amount = float(form.amount.data)
            distribution_method = form.distribution_method.data
            
            # 验证收款金额不能超过未收款总额
            unpaid_amount = ProjectReceipt.get_project_unpaid_amount(header_id)
            if amount > unpaid_amount:
                flash(f'收款金额不能超过未收款总额：{header.currency or "SGD"} {unpaid_amount:.2f}', 'error')
                return render_template('business/projects/project_receipt/create_header_receipt.html',
                                     form=form,
                                     header=header,
                                     receipt_number=receipt_number,
                                     unpaid_amount=unpaid_amount)
            
            # 根据分配方式处理
            if distribution_method == 'manual':
                # 手动分配：只分配给选中的REF
                selected_ref_ids = form.selected_refs.data
                if not selected_ref_ids or (len(selected_ref_ids) == 1 and selected_ref_ids[0] == 0):
                    flash('请选择要分配的REF', 'error')
                    return render_template('business/projects/project_receipt/create_header_receipt.html',
                                         form=form,
                                         header=header,
                                         receipt_number=receipt_number,
                                         unpaid_amount=unpaid_amount)
                
                # 计算选中REF的总未收款金额
                selected_unpaid_total = 0
                for ref_id in selected_ref_ids:
                    ref = ProjectRef.query.get(ref_id)
                    if ref and ref.selling_price:
                        total_received = ProjectReceipt.get_ref_total_received(ref.id, header_id)
                        ref_unpaid = float(ref.selling_price) - total_received
                        if ref_unpaid > 0:
                            selected_unpaid_total += ref_unpaid
                
                if amount > selected_unpaid_total:
                    flash(f'收款金额不能超过选中REF的未收款总额：{header.currency or "SGD"} {selected_unpaid_total:.2f}', 'error')
                    return render_template('business/projects/project_receipt/create_header_receipt.html',
                                         form=form,
                                         header=header,
                                         receipt_number=receipt_number,
                                         unpaid_amount=unpaid_amount)
                
                # 按比例分配给选中的REF
                distribution = []
                remaining_amount = amount
                for ref_id in selected_ref_ids:
                    ref = ProjectRef.query.get(ref_id)
                    if ref and ref.selling_price:
                        total_received = ProjectReceipt.get_ref_total_received(ref.id, header_id)
                        ref_unpaid = float(ref.selling_price) - total_received
                        if ref_unpaid > 0:
                            # 按比例分配
                            allocated = min(ref_unpaid, remaining_amount * (ref_unpaid / selected_unpaid_total))
                            if allocated > 0:
                                distribution.append({
                                    'ref_id': ref.id,
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
                # 自动分配：分配给所有有未收款的REF
                distribution_result = ProjectReceipt.distribute_project_receipt(
                    header_id, amount, distribution_method
                )
            
            if not distribution_result['success']:
                flash(distribution_result['message'], 'error')
                return render_template('business/projects/project_receipt/create_header_receipt.html',
                                     form=form,
                                     header=header,
                                     receipt_number=receipt_number,
                                     unpaid_amount=unpaid_amount)
            
            # 创建项目级别收款记录
            project_receipt = ProjectReceipt(
                receipt_number=receipt_number,
                ref_id=None,  # 项目级别收款记录，ref_id为None
                header_id=header.id,
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
            
            # 在extra_info中存储分配信息
            distribution_info = {
                'distribution_method': distribution_method,
                'distribution': distribution_result['distribution'],
                'total_amount': amount,
                'remaining_amount': distribution_result['remaining_amount'],
                'selected_refs': form.selected_refs.data if distribution_method == 'manual' else None
            }
            project_receipt.extra_info = json.dumps(distribution_info)
            
            db.session.add(project_receipt)
            
            # 先提交收款记录
            db.session.flush()
            
            # 更新各个REF的付款状态
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
            
            db.session.commit()
            
            return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=header.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    
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
    
    if form.validate_on_submit():
        try:
            # 更新收款记录
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
            
            db.session.commit()
            
            return redirect(url_for('business_projects.project_receipt.header_receipts', header_id=header.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
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
    """删除项目级别收款记录"""
    receipt = ProjectReceipt.query.filter_by(
        id=receipt_id, 
        header_id=header_id, 
        ref_id=None
    ).first_or_404()
    
    try:
        # 删除项目级别收款记录
        db.session.delete(receipt)
        
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
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
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
        ref_id = request.args.get('ref_id', None, type=int)
        date_range = request.args.get('date_range', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        min_amount = request.args.get('min_amount', None, type=float)
        max_amount = request.args.get('max_amount', None, type=float)
        keyword = request.args.get('keyword', '').strip()
        sort_by = request.args.get('sort_by', 'payment_date').strip()
        sort_order = request.args.get('sort_order', 'desc').strip()

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
            items.append({
                'id': r.id,
                'receipt_number': r.receipt_number,
                'project_hid': project_hid,
                'project_name': project_name,
                'ref_number': ref_number,
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
                'created_at': r.created_at
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
                'header_id': header_id,
                'ref_id': ref_id,
                'date_range': date_range,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount,
                'keyword': keyword,
                'sort_by': sort_by,
                'sort_order': sort_order,
                'per_page': per_page
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
        if ref.selling_price:
            # 使用辅助方法计算该REF的已收款总额
            ref_received = ProjectReceipt.get_ref_total_received(ref.id, header_id)
            ref_unpaid = float(ref.selling_price) - ref_received
            
            if ref_unpaid > 0:
                unpaid_refs.append({
                    'ref_id': ref.id,
                    'ref_number': ref.ref_number,
                    'ref_name': ref.name or ref.description,
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
