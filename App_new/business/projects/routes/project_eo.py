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
        
        # 检查REF是否已经有EO (使用ref_id检查，加上数据库刷新)
        db.session.expire_all()  # 刷新会话，确保获取最新数据
        existing_eo = ProjectEO.query.filter_by(ref_id=ref.id).first()
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
        for eo, supplier_name, ref_type_name, ref_description, ref_detailed_description, ref_number, project_id, project_name, company_name in pagination.items:
            
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
                'project_name': str(project_name) if project_name else '',
                'company_name': str(company_name) if company_name else '',
                'external_system': str(eo.external_system) if eo.external_system else '',
                'external_status': str(eo.external_status) if eo.external_status else '',
                'external_reference': str(eo.external_reference) if eo.external_reference else '',
                'amount': float(eo.ref.cost_price) if eo.ref and eo.ref.cost_price is not None else 0,
                'currency': str(eo.ref.currency) if eo.ref and eo.ref.currency else 'SGD',
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
