from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app
from flask_login import login_required, current_user
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.eo import ProjectEO
from App_new.exts import csrf, db
from App_new.business.projects.forms.eo_forms import ProjectEOForm
from App_new.utils.decorators import staff_only, admin_only
import json

project_eo = Blueprint('project_eo', __name__)

@project_eo.route('/create/<int:ref_id>', methods=['GET', 'POST'])
@login_required
@staff_only
def create_eo(ref_id):
    """创建EO"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 员工等级权限检查
    if current_user.role and current_user.role.name == 'staff':
        # 获取关联的项目信息
        from App_new.business.projects.models.project import ProjectHeader
        header = ProjectHeader.query.get(ref.header_id)
        if header:
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能操作自己创建的项目
                if header.staff_name != current_user.username:
                    flash('您没有权限访问此项目', 'error')
                    return redirect(url_for('business_projects.list.list_projects'))
    form = ProjectEOForm()
    form.ref_id.data = ref_id
    
    if form.validate_on_submit():
        try:
            eo_number = ProjectEO.generate_eo_number()
            eo = ProjectEO(
                ref_id=ref.id,
                eo_number=eo_number,
                external_system=form.external_system.data,
                external_status=form.external_status.data,
                external_reference=form.external_reference.data,
                status=form.status.data
            )
            db.session.add(eo)
            db.session.commit()
            flash('EO子明细创建成功！', 'success')
            return redirect(url_for('project_ref.ref_detail', ref_id=ref.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充EO编号
    eo_number = ProjectEO.generate_eo_number()
    form.eo_number.data = eo_number
    
    # 从REF中自动获取和预填充数据
    if request.method == 'GET':
        # 预填充状态（默认为已确认）
        if not form.status.data:
            form.status.data = 'confirmed'
    
    return render_template('business/projects/project_eo/create_eo.html',
                           form=form, ref=ref, eo_number=eo_number)

@project_eo.route('/<int:eo_id>')
@login_required
@staff_only
def eo_detail(eo_id):
    """EO详情页面"""
    eo = ProjectEO.query.get_or_404(eo_id)
    
    # 员工等级权限检查
    if current_user.role and current_user.role.name == 'staff':
        # 获取关联的项目信息
        from App_new.business.projects.models.project import ProjectHeader
        header = ProjectHeader.query.get(eo.ref.header_id)
        if header:
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能操作自己创建的项目
                if header.staff_name != current_user.username:
                    flash('您没有权限访问此项目', 'error')
                    return redirect(url_for('business_projects.project_eo.eo_list'))
    return render_template('business/projects/project_eo/eo_detail.html', eo=eo)


@project_eo.route('/<int:eo_id>/update', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def update_eo(eo_id):
    """更新EO信息"""
    try:
        eo = ProjectEO.query.get_or_404(eo_id)
        
        # 员工等级权限检查
        if current_user.role and current_user.role.name == 'staff':
            from App_new.business.projects.models.project import ProjectHeader
            header = ProjectHeader.query.get(eo.ref.header_id)
            if header:
                staff_level = 1
                if current_user.profile:
                    staff_level = current_user.profile.staff_level or 1
                
                if staff_level == 1:
                    if header.staff_name != current_user.username:
                        return jsonify({'success': False, 'message': '您没有权限操作此EO'}), 403
        
        # 获取JSON数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        # 更新字段
        from datetime import datetime
        
        # EO日期使用创建日期，不需要更新
        # if 'eo_date' in data:
        #     eo.eo_date = datetime.strptime(data['eo_date'], '%Y-%m-%d').date() if data['eo_date'] else None
        
        if 'conf_code' in data:
            eo.conf_code = data['conf_code'] if data['conf_code'] else None
        
        if 'discount' in data:
            eo.discount = float(data['discount']) if data['discount'] else 0
        
        if 'tax' in data:
            eo.tax = float(data['tax']) if data['tax'] else 0
        
        if 'payment_no' in data:
            eo.payment_no = data['payment_no'] if data['payment_no'] else None
        
        if 'paid_date' in data:
            eo.paid_date = datetime.strptime(data['paid_date'], '%Y-%m-%d').date() if data['paid_date'] else None
        
        if 'pay_amount' in data:
            eo.pay_amount = float(data['pay_amount']) if data['pay_amount'] else None
        
        if 'external_system' in data:
            eo.external_system = data['external_system'] if data['external_system'] else None
        
        if 'external_status' in data:
            eo.external_status = data['external_status'] if data['external_status'] else None
        
        if 'external_reference' in data:
            eo.external_reference = data['external_reference'] if data['external_reference'] else None
        
        if 'status' in data:
            eo.status = data['status']
        
        eo.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'EO更新成功'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新EO失败: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


@project_eo.route('/exchange-order')
@login_required
@staff_only
def exchange_order():
    """Exchange Order 付款页面 - 类似旧系统的付款管理界面"""
    try:
        from sqlalchemy import and_, or_, desc
        from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
        from App_new.shared.models.Suppliers import Supplier
        from App_new.shared.models.business_types import BusinessType
        from datetime import date
        
        # 获取筛选参数
        supplier_id = request.args.get('supplier', None, type=int)
        date_filter_by = request.args.get('date_filter_by', 'eo_date')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # 构建查询 - 查询未付款的EO（confirmed状态）
        query = db.session.query(
            ProjectEO,
            Supplier.name.label('supplier_name'),
            BusinessType.name.label('ref_type_name'),
            ProjectRef.ref_number.label('ref_number'),
            ProjectRef.description.label('description'),
            ProjectRef.header_id.label('project_id'),
            ProjectHeader.hid.label('project_hid'),
            CustomerCompany.company_name.label('company_name')
        ).join(
            ProjectRef, ProjectEO.ref_id == ProjectRef.id, isouter=True
        ).join(
            BusinessType, ProjectRef.ref_type_id == BusinessType.id, isouter=True
        ).join(
            Supplier, ProjectRef.supplier_id == Supplier.supplier_id, isouter=True
        ).join(
            ProjectHeader, ProjectRef.header_id == ProjectHeader.id, isouter=True
        ).join(
            CustomerCompany, ProjectHeader.company_id == CustomerCompany.id, isouter=True
        ).filter(
            ProjectEO.status == 'confirmed'
        )
        
        # 应用供应商筛选
        if supplier_id:
            query = query.filter(ProjectRef.supplier_id == supplier_id)
        
        # 应用日期筛选
        if date_from:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_filter_by == 'eo_date':
                query = query.filter(ProjectEO.created_at >= date_from_obj)
        
        if date_to:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            if date_filter_by == 'eo_date':
                query = query.filter(ProjectEO.created_at <= date_to_obj)
        
        # 排序
        query = query.order_by(desc(ProjectEO.created_at))
        
        # 获取结果
        results = query.all()
        
        # 处理数据
        eos = []
        for eo, supplier_name, ref_type_name, ref_number, description, project_id, project_hid, company_name in results:
            # 获取乘客姓名
            pax_names = ''
            if eo.ref:
                from App_new.business.flight.models.flight import ProjectFlightPassenger
                passengers = ProjectFlightPassenger.query.filter_by(ref_id=eo.ref_id).all()
                if passengers:
                    pax_names = ', '.join([p.name for p in passengers if p.name])
            
            cost_price = float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else 0
            paid_amount = float(eo.pay_amount) if eo.pay_amount else 0
            balance = cost_price - paid_amount
            
            eos.append({
                'id': eo.id,
                'eo_number': eo.eo_number,
                'ref_id': eo.ref_id,
                'ref_number': ref_number or '',
                'description': description or '',
                'supplier_name': supplier_name or '',
                'ref_type_name': ref_type_name or '',
                'project_id': project_id,
                'project_hid': project_hid or '',
                'company_name': company_name or '',
                'pax_names': pax_names,
                'cost_price': cost_price,
                'balance': balance,
                'pay_amount': paid_amount,
                'currency': eo.ref.currency if eo.ref and eo.ref.currency else 'SGD',
                'created_at': eo.created_at,
                'dep_date': None,  # 可从extra_info获取
                'due_date': None,
                'inv_number': None,
                'inv_amount': None,
                'conf_by': None,
                'rate': 1.00
            })
        
        # 获取供应商列表
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
        return render_template('business/projects/project_eo/exchange_order.html',
                             eos=eos,
                             suppliers=suppliers,
                             today=date.today().isoformat(),
                             current_filters={
                                 'supplier': supplier_id,
                                 'date_filter_by': date_filter_by,
                                 'date_from': date_from,
                                 'date_to': date_to
                             })
    except Exception as e:
        import traceback
        print(f"Exchange Order页面加载失败: {str(e)}")
        traceback.print_exc()
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.project_eo.eo_list'))


@project_eo.route('/exchange-order/generate-payment-no', methods=['GET'])
@csrf.exempt
@login_required
@staff_only
def generate_payment_no():
    """生成付款编号"""
    try:
        from datetime import datetime
        # 格式：PAY-YYYYMMDD-XXX
        today = datetime.now().strftime('%Y%m%d')
        prefix = f'PAY-{today}-'
        
        # 查找今天最后一个付款编号
        last_eo = ProjectEO.query.filter(
            ProjectEO.payment_no.like(f'{prefix}%')
        ).order_by(ProjectEO.payment_no.desc()).first()
        
        if last_eo and last_eo.payment_no:
            try:
                last_num = int(last_eo.payment_no.split('-')[-1])
                new_num = last_num + 1
            except:
                new_num = 1
        else:
            new_num = 1
        
        payment_no = f'{prefix}{str(new_num).zfill(3)}'
        
        return jsonify({
            'success': True,
            'payment_no': payment_no
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'payment_no': f'PAY-{datetime.now().strftime("%Y%m%d")}-001'
        })


@project_eo.route('/exchange-order/pay', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def exchange_order_pay():
    """Exchange Order 付款提交"""
    try:
        data = request.get_json()
        eo_ids = data.get('eo_ids', [])
        payment_no = data.get('payment_no')
        paid_date_str = data.get('paid_date')
        total_pay_amount = data.get('pay_amount')
        remarks = data.get('remarks', '')
        
        if not eo_ids:
            return jsonify({'success': False, 'message': 'Please select at least one EO'}), 400
        
        if not payment_no or not paid_date_str or total_pay_amount is None:
            return jsonify({'success': False, 'message': 'Please fill in all required fields'}), 400
        
        from datetime import datetime
        paid_date = datetime.strptime(paid_date_str, '%Y-%m-%d').date()
        
        eos = ProjectEO.query.filter(ProjectEO.id.in_(eo_ids)).all()
        
        if len(eos) != len(eo_ids):
            return jsonify({'success': False, 'message': 'Some EOs not found'}), 400
        
        total_cost = sum(float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else 0 for eo in eos)
        
        success_count = 0
        for eo in eos:
            if eo.status in ['void', 'paid']:
                continue
            
            eo_cost = float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else 0
            if total_cost > 0:
                eo_pay_amount = (eo_cost / total_cost) * total_pay_amount
            else:
                eo_pay_amount = total_pay_amount / len(eos)
            
            eo.payment_no = payment_no
            eo.paid_date = paid_date
            eo.pay_amount = round(eo_pay_amount, 2)
            eo.status = 'paid'
            success_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully paid {success_count} EO(s), Payment No: {payment_no}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@project_eo.route('/exchange-order/cancel', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def exchange_order_cancel():
    """Exchange Order 批量取消/作废EO"""
    try:
        data = request.get_json()
        eo_ids = data.get('eo_ids', [])
        
        if not eo_ids:
            return jsonify({'success': False, 'message': 'Please select at least one EO'}), 400
        
        eos = ProjectEO.query.filter(ProjectEO.id.in_(eo_ids)).all()
        
        success_count = 0
        for eo in eos:
            if eo.status == 'void':
                continue
            eo.status = 'void'
            success_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully voided {success_count} EO(s)'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@project_eo.route('/batch-pay')
@login_required
@staff_only
def batch_pay():
    """批量付款页面 - 显示待付款的EO列表"""
    try:
        from sqlalchemy import and_, or_, desc
        from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
        from App_new.shared.models.Suppliers import Supplier
        from App_new.shared.models.business_types import BusinessType
        from datetime import date
        
        # 获取筛选参数
        supplier_type = request.args.get('supplier_type', '')
        supplier_id = request.args.get('supplier', None, type=int)
        keyword = request.args.get('keyword', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # 构建查询 - 只查询未付款的EO（confirmed状态）
        query = db.session.query(
            ProjectEO,
            Supplier.name.label('supplier_name'),
            BusinessType.name.label('ref_type_name'),
            ProjectRef.ref_number.label('ref_number'),
            ProjectRef.header_id.label('project_id'),
            ProjectHeader.hid.label('project_hid'),
            CustomerCompany.company_name.label('company_name')
        ).join(
            ProjectRef, ProjectEO.ref_id == ProjectRef.id, isouter=True
        ).join(
            BusinessType, ProjectRef.ref_type_id == BusinessType.id, isouter=True
        ).join(
            Supplier, ProjectRef.supplier_id == Supplier.supplier_id, isouter=True
        ).join(
            ProjectHeader, ProjectRef.header_id == ProjectHeader.id, isouter=True
        ).join(
            CustomerCompany, ProjectHeader.company_id == CustomerCompany.id, isouter=True
        ).filter(
            ProjectEO.status == 'confirmed'  # 只显示已确认但未付款的
        )
        
        # 应用筛选条件
        if supplier_type:
            supplier_type_map = {
                'visa': '签证', 'flight': '机票', 'hotel': '酒店',
                'transport': '用车', 'local_operator': '地接', 'other': '其他'
            }
            type_name = supplier_type_map.get(supplier_type)
            if type_name:
                query = query.filter(BusinessType.name == type_name)
        
        if supplier_id:
            query = query.filter(ProjectRef.supplier_id == supplier_id)
        
        if keyword:
            keyword_filter = or_(
                ProjectEO.eo_number.ilike(f'%{keyword}%'),
                ProjectRef.ref_number.ilike(f'%{keyword}%'),
                ProjectHeader.hid.ilike(f'%{keyword}%')
            )
            query = query.filter(keyword_filter)
        
        # 日期筛选
        if start_date:
            from datetime import datetime
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(ProjectEO.created_at >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            from datetime import datetime, timedelta
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(ProjectEO.created_at < end_dt)
            except ValueError:
                pass
        
        # 排序
        query = query.order_by(desc(ProjectEO.created_at))
        
        # 获取结果
        results = query.all()
        
        # 处理数据
        eos = []
        for eo, supplier_name, ref_type_name, ref_number, project_id, project_hid, company_name in results:
            # 获取乘客姓名 - 支持所有类型的REF
            pax_names = ''
            if eo.ref:
                import json
                from App_new.business.projects.models.project_member import ProjectMember
                from App_new.business.flight.models.flight import ProjectFlightPassenger
                
                # 方法1: 优先从extra_info获取（机票REF可能已有pax_names_display）
                if eo.ref.extra_info:
                    try:
                        extra_data = json.loads(eo.ref.extra_info)
                        # 如果已有pax_names_display，直接使用
                        if extra_data.get('pax_names_display'):
                            pax_names = extra_data.get('pax_names_display')
                        else:
                            # 其他类型REF：从pax_names ID列表获取
                            pax_names_ids = extra_data.get('pax_names', [])
                            if pax_names_ids:
                                members = ProjectMember.query.filter(ProjectMember.id.in_(pax_names_ids)).all()
                                if members:
                                    pax_names_list = [f"{m.title} {m.member_name}" if m.title else m.member_name for m in members]
                                    pax_names = ', '.join(pax_names_list)
                            else:
                                # 单个姓名
                                pax_names = extra_data.get('pax_name', '')
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # 方法2: 如果没有从extra_info获取到，尝试从flight_passengers获取（机票类型）
                if not pax_names and hasattr(eo.ref, 'flight_passengers'):
                    passengers = ProjectFlightPassenger.query.filter_by(ref_id=eo.ref_id).all()
                    if passengers:
                        pax_names = ', '.join([p.name for p in passengers if p.name])
            
            eos.append({
                'id': eo.id,
                'eo_number': eo.eo_number,
                'ref_id': eo.ref_id,
                'ref_number': ref_number or '',
                'supplier_name': supplier_name or '',
                'ref_type_name': ref_type_name or '',
                'project_id': project_id,
                'project_hid': project_hid or '',
                'company_name': company_name or '',
                'pax_names': pax_names,
                'cost_price': float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else 0,
                'currency': eo.ref.currency if eo.ref and eo.ref.currency else 'SGD',
                'created_at': eo.created_at
            })
        
        # 获取供应商列表
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
        return render_template('business/projects/project_eo/batch_pay.html',
                             eos=eos,
                             suppliers=suppliers,
                             today=date.today().isoformat(),
                             current_filters={
                                 'supplier_type': supplier_type,
                                 'supplier': supplier_id,
                                 'keyword': keyword,
                                 'start_date': start_date,
                                 'end_date': end_date
                             })
    except Exception as e:
        import traceback
        print(f"批量付款页面加载失败: {str(e)}")
        traceback.print_exc()
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.project_eo.eo_list'))


@project_eo.route('/batch-pay/submit', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def batch_pay_submit():
    """批量付款提交"""
    try:
        data = request.get_json()
        eo_ids = data.get('eo_ids', [])
        payment_no = data.get('payment_no')
        paid_date_str = data.get('paid_date')
        total_pay_amount = data.get('pay_amount')
        remarks = data.get('remarks', '')
        
        if not eo_ids:
            return jsonify({'success': False, 'message': '请选择要付款的EO'}), 400
        
        if not payment_no or not paid_date_str or total_pay_amount is None:
            return jsonify({'success': False, 'message': '请填写完整的付款信息'}), 400
        
        # 解析日期
        from datetime import datetime
        paid_date = datetime.strptime(paid_date_str, '%Y-%m-%d').date()
        
        # 查询所有选中的EO
        eos = ProjectEO.query.filter(ProjectEO.id.in_(eo_ids)).all()
        
        if len(eos) != len(eo_ids):
            return jsonify({'success': False, 'message': '部分EO不存在'}), 400
        
        # 计算每个EO的付款金额（按比例分配）
        total_cost = sum(float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else 0 for eo in eos)
        
        success_count = 0
        for eo in eos:
            # 检查状态
            if eo.status in ['void', 'paid']:
                continue
            
            # 计算该EO的付款金额（按比例）
            eo_cost = float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else 0
            if total_cost > 0:
                eo_pay_amount = (eo_cost / total_cost) * total_pay_amount
            else:
                eo_pay_amount = total_pay_amount / len(eos)
            
            # 更新付款信息
            eo.payment_no = payment_no
            eo.paid_date = paid_date
            eo.pay_amount = round(eo_pay_amount, 2)
            eo.status = 'paid'
            success_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功付款 {success_count} 个EO，付款编号：{payment_no}'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@project_eo.route('/<int:eo_id>/pay', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def pay_eo(eo_id):
    """付款给供应商"""
    try:
        eo = ProjectEO.query.get_or_404(eo_id)
        
        # 员工等级权限检查
        if current_user.role and current_user.role.name == 'staff':
            from App_new.business.projects.models.project import ProjectHeader
            header = ProjectHeader.query.get(eo.ref.header_id)
            if header:
                staff_level = 1
                if current_user.profile:
                    staff_level = current_user.profile.staff_level or 1
                
                if staff_level == 1:
                    if header.staff_name != current_user.username:
                        return jsonify({'success': False, 'message': '您没有权限操作此EO'}), 403
        
        # 检查状态
        if eo.status == 'void':
            return jsonify({'success': False, 'message': '此EO已作废，无法付款'}), 400
        
        if eo.status == 'paid':
            return jsonify({'success': False, 'message': '此EO已付款'}), 400
        
        # 获取请求数据
        data = request.get_json()
        payment_no = data.get('payment_no')
        paid_date_str = data.get('paid_date')
        pay_amount = data.get('pay_amount')
        payment_remarks = data.get('payment_remarks', '')
        
        if not payment_no or not paid_date_str or pay_amount is None:
            return jsonify({'success': False, 'message': '请填写完整的付款信息'}), 400
        
        # 解析日期
        from datetime import datetime
        paid_date = datetime.strptime(paid_date_str, '%Y-%m-%d').date()
        
        # 更新付款信息
        eo.payment_no = payment_no
        eo.paid_date = paid_date
        eo.pay_amount = pay_amount
        eo.payment_remarks = payment_remarks
        eo.status = 'paid'
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'EO {eo.eo_number} 付款成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@project_eo.route('/<int:eo_id>/void', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def void_eo(eo_id):
    """作废EO"""
    try:
        eo = ProjectEO.query.get_or_404(eo_id)
        
        # 员工等级权限检查
        if current_user.role and current_user.role.name == 'staff':
            from App_new.business.projects.models.project import ProjectHeader
            header = ProjectHeader.query.get(eo.ref.header_id)
            if header:
                staff_level = 1
                if current_user.profile:
                    staff_level = current_user.profile.staff_level or 1
                
                if staff_level == 1:
                    if header.staff_name != current_user.username:
                        return jsonify({'success': False, 'message': '您没有权限操作此EO'}), 403
        
        # 检查是否已经作废
        if eo.status == 'void':
            return jsonify({'success': False, 'message': '此EO已经作废'}), 400
        
        # 更新状态为作废
        eo.status = 'void'
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'EO {eo.eo_number} 已作废'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@project_eo.route('/quick_create/<int:ref_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def quick_create_eo(ref_id):
    """一键生成EO - API接口"""
    try:
        ref = ProjectRef.query.get_or_404(ref_id)
        
        # 员工等级权限检查
        if current_user.role and current_user.role.name == 'staff':
            # 获取关联的项目信息
            from App_new.business.projects.models.project import ProjectHeader
            header = ProjectHeader.query.get(ref.header_id)
            if header:
                staff_level = 1  # 默认等级
                if current_user.profile:
                    staff_level = current_user.profile.staff_level or 1
                
                if staff_level == 1:
                    # 1级员工只能操作自己创建的项目
                    if header.staff_name != current_user.username:
                        return jsonify({
                            'success': False,
                            'message': '您没有权限访问此项目'
                        }), 403
        
        # 检查REF是否已经有有效的EO (排除已作废的)
        db.session.expire_all()  # 刷新会话，确保获取最新数据
        existing_eo = ProjectEO.query.filter_by(ref_id=ref.id).filter(ProjectEO.status != 'void').first()
        if existing_eo:
            print(f"DEBUG: REF {ref.id} (ref_number: {ref.ref_number}) 已经存在EO {existing_eo.eo_number} (id: {existing_eo.id})")
            return jsonify({
                'success': False,
                'message': f'此REF已存在EO编号 {existing_eo.eo_number}，无法重复创建'
            }), 400
        
        print(f"DEBUG: REF {ref.id} 没有EO记录，准备创建...")
        
        # 创建EO
        eo = ProjectEO(
            ref_id=ref.id,
            external_system=None,
            external_status=None,
            external_reference=None,
            status='confirmed'
        )
        
        # 先保存获取ID
        db.session.add(eo)
        db.session.flush()  # 获取ID但不提交
        
        # 使用ID生成EO编号
        eo.eo_number = f'E{str(eo.id).zfill(3)}'
        
        # 提交事务
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'EO {eo.eo_number} 创建成功！',
            'eo_number': eo.eo_number,
            'eo_id': eo.id
        })
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        
        # 特殊处理重复键错误
        if 'Duplicate entry' in error_msg and 'unique_ref_eo' in error_msg:
            print(f"ERROR: REF {ref_id} 存在重复的EO记录")
            # 尝试查找已存在的EO
            existing_eo = ProjectEO.query.filter_by(ref_id=ref_id).first()
            if existing_eo:
                return jsonify({
                    'success': False,
                    'message': f'此REF已存在EO编号 {existing_eo.eo_number}，请勿重复创建'
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'message': '此REF已存在EO记录，请刷新页面查看'
                }), 400
        
        # 其他错误
        print(f"ERROR: 快速创建EO失败 [ref_id={ref_id}]: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'创建失败：{error_msg}'
        }), 500


@project_eo.route('/list')
@login_required
@staff_only
def eo_list():
    """EO列表页面 - 支持筛选、搜索和分页"""
    try:
        from sqlalchemy import and_, or_, desc, asc
        from datetime import datetime, timedelta
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
        from App_new.shared.models.Suppliers import Supplier
        
        # 获取筛选参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        supplier_type = request.args.get('supplier_type', '')
        status = request.args.get('status', '')
        supplier_id = request.args.get('supplier', None, type=int)
        external_system = request.args.get('external_system', '')
        date_range = request.args.get('date_range', '')
        min_amount = request.args.get('min_amount', None, type=float)
        max_amount = request.args.get('max_amount', None, type=float)
        keyword = request.args.get('keyword', '')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # 构建查询
        from App_new.shared.models.business_types import BusinessType
        query = db.session.query(
            ProjectEO,
            Supplier.name.label('supplier_name'),
            BusinessType.name.label('ref_type_name'),
            ProjectRef.description.label('ref_description'),
            ProjectRef.detailed_description.label('ref_detailed_description'),
            ProjectRef.ref_number.label('ref_number'),
            ProjectRef.header_id.label('project_id'),
            ProjectHeader.hid.label('project_hid'),
            ProjectHeader.desc.label('project_name'),
            CustomerCompany.company_name.label('company_name')
        ).join(
            ProjectRef, ProjectEO.ref_id == ProjectRef.id, isouter=True
        ).join(
            BusinessType, ProjectRef.ref_type_id == BusinessType.id, isouter=True
        ).join(
            Supplier, ProjectRef.supplier_id == Supplier.supplier_id, isouter=True
        ).join(
            ProjectHeader, ProjectRef.header_id == ProjectHeader.id, isouter=True
        ).join(
            CustomerCompany, ProjectHeader.company_id == CustomerCompany.id, isouter=True
        )
        
        # 应用筛选条件
        filters = []
        
        # 根据员工等级过滤EO
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己创建的项目的EO
                filters.append(ProjectHeader.staff_name == current_user.username)
            # 2级员工可以看到所有EO，不需要额外过滤
        
        if status:
            filters.append(ProjectEO.status == status)
        
        if supplier_id:
            filters.append(ProjectRef.supplier_id == supplier_id)
        
        if supplier_type:
            # 通过REF的ref_type_id关联到business_types来筛选
            # 根据供应商类型枚举值匹配业务类型名称
            supplier_type_map = {
                'visa': '签证',
                'flight': '机票',
                'hotel': '酒店',
                'transport': '用车',
                'local_operator': '地接',
                'other': '其他'
            }
            type_name = supplier_type_map.get(supplier_type)
            if type_name:
                filters.append(BusinessType.name == type_name)
        
        if external_system:
            filters.append(ProjectEO.external_system.ilike(f'%{external_system}%'))
        
        if date_range:
            today = datetime.now().date()
            if date_range == 'today':
                start_date = today
                end_date = today + timedelta(days=1)
            elif date_range == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=7)
            elif date_range == 'month':
                start_date = today.replace(day=1)
                if today.month == 12:
                    end_date = today.replace(year=today.year + 1, month=1, day=1)
                else:
                    end_date = today.replace(month=today.month + 1, day=1)
            elif date_range == 'quarter':
                quarter = (today.month - 1) // 3
                start_date = today.replace(month=quarter * 3 + 1, day=1)
                if quarter == 3:
                    end_date = today.replace(year=today.year + 1, month=1, day=1)
                else:
                    end_date = today.replace(month=quarter * 3 + 4, day=1)
            elif date_range == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = today.replace(year=today.year + 1, month=1, day=1)
            
            filters.append(and_(
                ProjectEO.created_at >= start_date,
                ProjectEO.created_at < end_date
            ))
        
        if min_amount is not None and min_amount > 0:
            filters.append(ProjectRef.cost_price >= float(min_amount))
        
        if max_amount is not None and max_amount > 0:
            filters.append(ProjectRef.cost_price <= float(max_amount))
        
        if keyword:
            keyword_filter = or_(
                ProjectEO.eo_number.ilike(f'%{keyword}%'),
                ProjectEO.external_system.ilike(f'%{keyword}%'),
                ProjectEO.external_reference.ilike(f'%{keyword}%'),
                ProjectRef.description.ilike(f'%{keyword}%'),
                ProjectRef.detailed_description.ilike(f'%{keyword}%'),
                ProjectRef.ref_number.ilike(f'%{keyword}%'),
                ProjectHeader.desc.ilike(f'%{keyword}%'),
                CustomerCompany.company_name.ilike(f'%{keyword}%')
            )
            filters.append(keyword_filter)
        
        # 应用筛选条件
        if filters:
            query = query.filter(and_(*filters))
        
        # 排序
        if sort_by == 'created_at':
            order_column = ProjectEO.created_at
        elif sort_by == 'amount':
            order_column = ProjectRef.cost_price
        elif sort_by == 'status':
            order_column = ProjectEO.status
        else:
            order_column = ProjectEO.created_at
        
        if sort_order == 'asc':
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))
        
        # 分页
        try:
            pagination = query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
        except AttributeError:
            # 如果新版本方法不存在，使用旧版本
            pagination = query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
        
        # 确保分页对象有必要的属性
        if not hasattr(pagination, 'has_prev'):
            pagination.has_prev = pagination.page > 1
            pagination.has_next = pagination.page < pagination.pages
            pagination.prev_num = pagination.page - 1 if pagination.page > 1 else None
            pagination.next_num = pagination.page + 1 if pagination.page < pagination.pages else None
        
        # 确保分页对象有iter_pages方法
        if not hasattr(pagination, 'iter_pages'):
            def iter_pages(left_edge=2, left_current=2, right_current=5, right_edge=2):
                last = 0
                for num in range(1, pagination.pages + 1):
                    if num <= left_edge or \
                       (num > pagination.page - left_current - 1 and \
                        num < pagination.page + right_current) or \
                       num > pagination.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num
            pagination.iter_pages = iter_pages
        
        # 处理EO数据，添加显示属性
        eos = []
        for eo, supplier_name, ref_type_name, ref_description, ref_detailed_description, ref_number, project_id, project_hid, project_name, company_name in pagination.items:
            # 获取乘客姓名
            pax_names = ''
            if eo.ref:
                from App_new.business.flight.models.flight import ProjectFlightPassenger
                passengers = ProjectFlightPassenger.query.filter_by(ref_id=eo.ref_id).all()
                if passengers:
                    pax_names = ', '.join([p.name for p in passengers if p.name])
            
            eo_dict = {
                'id': eo.id,
                'eo_number': str(eo.eo_number) if eo.eo_number else '',
                'ref_id': int(eo.ref_id) if eo.ref_id else None,
                'ref_description': str(ref_description) if ref_description else '',
                'ref_detailed_description': str(ref_detailed_description) if ref_detailed_description else '',
                'ref_number': str(ref_number) if ref_number else '',
                'supplier_name': str(supplier_name) if supplier_name else '',
                'ref_type_name': str(ref_type_name) if ref_type_name else '',
                'project_id': int(project_id) if project_id else None,
                'project_hid': str(project_hid) if project_hid else '',
                'project_name': str(project_name) if project_name else '',
                'company_name': str(company_name) if company_name else '',
                'pax_names': pax_names,
                # EO新字段
                'conf_code': str(eo.conf_code) if eo.conf_code else '',
                'discount': float(eo.discount) if eo.discount else 0,
                'tax': float(eo.tax) if eo.tax else 0,
                'payment_no': str(eo.payment_no) if eo.payment_no else '',
                'paid_date': eo.paid_date,
                'pay_amount': float(eo.pay_amount) if eo.pay_amount else None,
                # REF价格信息
                'selling_price': float(eo.ref.selling_price) if eo.ref and eo.ref.selling_price else None,
                'cost_price': float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price else None,
                'currency': str(eo.ref.currency) if eo.ref and eo.ref.currency else 'SGD',
                # 外部系统
                'external_system': str(eo.external_system) if eo.external_system else '',
                'external_status': str(eo.external_status) if eo.external_status else '',
                'external_reference': str(eo.external_reference) if eo.external_reference else '',
                # 状态
                'status': str(eo.status) if eo.status else 'draft',
                'status_display': get_status_display(eo.status),
                'status_color': get_status_color(eo.status),
                'created_at': eo.created_at,
                'updated_at': eo.updated_at
            }
            eos.append(eo_dict)
        
        # 获取筛选选项数据
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
        # 计算筛选结果数量
        filtered_count = pagination.total if any([supplier_type, status, supplier_id, external_system, date_range, min_amount, max_amount, keyword]) else None
        
        return render_template('business/projects/project_eo/eo_list.html',
                             eos=eos,
                             pagination=pagination,
                             suppliers=suppliers,
                             filtered_count=filtered_count,
                             current_filters={
                                 'supplier_type': supplier_type,
                                 'status': status,
                                 'supplier': supplier_id,
                                 'external_system': external_system,
                                 'date_range': date_range,
                                 'min_amount': min_amount,
                                 'max_amount': max_amount,
                                 'keyword': keyword,
                                 'sort_by': sort_by,
                                 'sort_order': sort_order
                             })
                             
    except Exception as e:
        import traceback
        print(f"EO列表加载失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        flash(f'EO列表加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


def get_status_display(status):
    """获取状态的中文显示名称"""
    if not status or not isinstance(status, str):
        return '未知'
    
    status_map = {
        'draft': '草稿',
        'confirmed': '已确认',
        'paid': '已付款',
        'cancelled': '已取消',
        'void': '已作废'
    }
    return status_map.get(status, status)


def get_status_color(status):
    """获取状态对应的Bootstrap颜色类"""
    if not status or not isinstance(status, str):
        return 'secondary'
    
    color_map = {
        'draft': 'secondary',
        'confirmed': 'info',
        'paid': 'success',
        'cancelled': 'danger',
        'void': 'dark'
    }
    return color_map.get(status, 'secondary')


def get_supplier_type_display(supplier_type):
    """获取供应商类型的中文显示名称"""
    if not supplier_type or not isinstance(supplier_type, str):
        return '未知'
    
    type_map = {
        'visa': '签证',
        'flight': '机票',
        'hotel': '酒店',
        'transport': '交通',
        'local_operator': '地接社',
        'other': '其他'
    }
    return type_map.get(supplier_type, supplier_type)


def get_supplier_type_color(supplier_type):
    """获取供应商类型对应的Bootstrap颜色类"""
    if not supplier_type or not isinstance(supplier_type, str):
        return 'secondary'
    
    color_map = {
        'visa': 'warning',
        'flight': 'primary',
        'hotel': 'success',
        'transport': 'info',
        'local_operator': 'dark',
        'other': 'secondary'
    }
    return color_map.get(supplier_type, 'secondary')
