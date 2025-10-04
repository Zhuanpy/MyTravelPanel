from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
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
    
    # 确保供应商选项已加载
    form._load_choices()
    
    if form.validate_on_submit():
        try:
            eo_number = ProjectEO.generate_eo_number()
            eo = ProjectEO(
                ref_id=ref.id,
                eo_number=eo_number,
                name=form.name.data,
                supplier_type=form.supplier_type.data,
                supplier_id=form.supplier_id.data,
                external_system=form.external_system.data,
                external_status=form.external_status.data,
                external_reference=form.external_reference.data,
                amount=form.amount.data,
                currency=form.currency.data,
                remarks=form.remarks.data,
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
        # 预填充EO名称（使用REF名称）
        if not form.name.data:
            form.name.data = ref.name or ref.description or f"{ref.ref_type.name if ref.ref_type else 'REF'}订单"
        
        # 预填充供应商类型（根据REF类型推断）
        if not form.supplier_type.data:
            if ref.ref_type:
                ref_type_name = ref.ref_type.name
                if '机票' in ref_type_name:
                    form.supplier_type.data = 'flight'
                elif '酒店' in ref_type_name:
                    form.supplier_type.data = 'hotel'
                elif '签证' in ref_type_name:
                    form.supplier_type.data = 'visa'
                elif '交通' in ref_type_name or '用车' in ref_type_name:
                    form.supplier_type.data = 'transport'
                elif '旅游' in ref_type_name or '团' in ref_type_name:
                    form.supplier_type.data = 'local_operator'
                elif '保险' in ref_type_name:
                    form.supplier_type.data = 'other'
                else:
                    form.supplier_type.data = 'other'
        
        # 预填充供应商ID（使用REF的供应商）
        if not form.supplier_id.data and ref.supplier_id:
            form.supplier_id.data = ref.supplier_id
        
        # 预填充金额（使用REF的成本价格）
        if not form.amount.data and ref.cost_price:
            form.amount.data = ref.cost_price
        
        # 预填充货币（使用REF的货币）
        if not form.currency.data and ref.currency:
            form.currency.data = ref.currency
        elif not form.currency.data:
            form.currency.data = 'SGD'  # 默认货币
        
        # 预填充备注（使用REF的备注）
        if not form.remarks.data and ref.remarks:
            form.remarks.data = ref.remarks
        
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

@project_eo.route('/<int:eo_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@staff_only
def edit_eo(eo_id):
    """编辑EO"""
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
    form = ProjectEOForm(obj=eo)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(eo)
            db.session.commit()
            return redirect(url_for('project_eo.eo_detail', eo_id=eo.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('business/projects/project_eo/edit_eo.html', form=form, eo=eo)

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
        
        # 检查REF是否已经有EO
        existing_eo = ProjectEO.query.filter_by(ref_id=ref.id).first()
        if existing_eo:
            return jsonify({
                'success': False,
                'message': f'REF {ref.ref_number} 已经存在EO编号 {existing_eo.eo_number}'
            }), 400
        
        # 根据REF类型推断供应商类型
        supplier_type = 'other'
        if ref.ref_type:
            ref_type_name = ref.ref_type.name
            if '机票' in ref_type_name:
                supplier_type = 'flight'
            elif '酒店' in ref_type_name:
                supplier_type = 'hotel'
            elif '签证' in ref_type_name:
                supplier_type = 'visa'
            elif '交通' in ref_type_name or '用车' in ref_type_name:
                supplier_type = 'transport'
            elif '旅游' in ref_type_name or '团' in ref_type_name:
                supplier_type = 'local_operator'
            elif '保险' in ref_type_name:
                supplier_type = 'other'
        
        # 创建EO
        eo = ProjectEO(
            ref_id=ref.id,
            name=ref.name or ref.description or f"{ref.ref_type.name if ref.ref_type else 'REF'}订单",
            supplier_type=supplier_type,
            supplier_id=ref.supplier_id or 1,  # 如果没有供应商，使用默认供应商
            external_system=None,
            external_status=None,
            external_reference=None,
            amount=ref.cost_price or 0,
            currency=ref.currency or 'SGD',
            remarks=ref.remarks,
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
            'eo_number': eo.eo_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'创建失败：{str(e)}'
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
        query = db.session.query(
            ProjectEO,
            Supplier.name.label('supplier_name'),
            ProjectRef.name.label('ref_name'),
            ProjectRef.ref_number.label('ref_number'),
            ProjectRef.header_id.label('project_id'),
            ProjectHeader.desc.label('project_name'),
            CustomerCompany.company_name.label('company_name')
        ).join(
            Supplier, ProjectEO.supplier_id == Supplier.supplier_id, isouter=True
        ).join(
            ProjectRef, ProjectEO.ref_id == ProjectRef.id, isouter=True
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
        
        if supplier_type:
            filters.append(ProjectEO.supplier_type == supplier_type)
        
        if status:
            filters.append(ProjectEO.status == status)
        
        if supplier_id:
            filters.append(ProjectEO.supplier_id == supplier_id)
        
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
            filters.append(ProjectEO.amount >= float(min_amount))
        
        if max_amount is not None and max_amount > 0:
            filters.append(ProjectEO.amount <= float(max_amount))
        
        if keyword:
            keyword_filter = or_(
                ProjectEO.name.ilike(f'%{keyword}%'),
                ProjectEO.eo_number.ilike(f'%{keyword}%'),
                ProjectEO.external_system.ilike(f'%{keyword}%'),
                ProjectEO.external_reference.ilike(f'%{keyword}%'),
                ProjectEO.remarks.ilike(f'%{keyword}%'),
                ProjectRef.name.ilike(f'%{keyword}%'),
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
        elif sort_by == 'name':
            order_column = ProjectEO.name
        elif sort_by == 'amount':
            order_column = ProjectEO.amount
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
        for eo, supplier_name, ref_name, ref_number, project_id, project_name, company_name in pagination.items:
            eo_dict = {
                'id': eo.id,
                'eo_number': str(eo.eo_number) if eo.eo_number else '',
                'name': str(eo.name) if eo.name else '',
                'supplier_type': str(eo.supplier_type) if eo.supplier_type else '',
                'supplier_type_display': get_supplier_type_display(eo.supplier_type),
                'supplier_type_color': get_supplier_type_color(eo.supplier_type),
                'supplier_name': str(supplier_name) if supplier_name else '',
                'ref_id': int(eo.ref_id) if eo.ref_id else None,
                'ref_name': str(ref_name) if ref_name else '',
                'ref_number': str(ref_number) if ref_number else '',
                'project_id': int(project_id) if project_id else None,
                'project_name': str(project_name) if project_name else '',
                'company_name': str(company_name) if company_name else '',
                'external_system': str(eo.external_system) if eo.external_system else '',
                'external_status': str(eo.external_status) if eo.external_status else '',
                'external_reference': str(eo.external_reference) if eo.external_reference else '',
                'amount': float(eo.amount) if eo.amount is not None else 0,
                'currency': str(eo.currency) if eo.currency else 'SGD',
                'status': str(eo.status) if eo.status else 'draft',
                'status_display': get_status_display(eo.status),
                'status_color': get_status_color(eo.status),
                'remarks': str(eo.remarks) if eo.remarks else '',
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
        'cancelled': '已取消'
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
        'cancelled': 'danger'
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
