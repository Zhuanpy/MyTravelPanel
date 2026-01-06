# -*- coding: utf-8 -*-
"""
移动端路由
提供针对手机优化的简化版界面
"""

from flask import render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc

from . import mobile_bp
from App_new.exts import db


@mobile_bp.route('/')
@login_required
def index():
    """移动端首页 - 重定向到员工仪表板"""
    return redirect(url_for('mobile.staff_dashboard'))


@mobile_bp.route('/staff/dashboard')
@login_required
def staff_dashboard():
    """移动端员工仪表板 - 与桌面端保持一致的数据"""
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.shared.models.Utilsmodels import Todo

    # 构建基础查询（根据员工等级过滤）
    base_query = ProjectHeader.query

    if current_user.role and current_user.role.name == 'staff':
        staff_level = 1
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1

        if staff_level == 1:
            base_query = base_query.filter(ProjectHeader.staff_name == current_user.username)

    # 统计数据
    total_projects = base_query.count()
    active_projects = base_query.filter_by(status='active').count()

    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    completed_this_month = base_query.filter(
        ProjectHeader.status == 'completed',
        ProjectHeader.updated_at >= current_month_start
    ).count()

    pending_quotes = base_query.filter_by(status='draft').count()

    stats = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'pending_quotes': pending_quotes,
        'completed_this_month': completed_this_month,
    }

    # 获取最近项目（带财务数据）
    recent_projects_query = base_query.order_by(ProjectHeader.created_at.desc()).limit(10)
    recent_projects = []

    for project in recent_projects_query:
        refs = ProjectRef.query.filter_by(header_id=project.id).all()
        total_selling_price = sum([float(ref.selling_price or 0) for ref in refs])
        total_cost_price = sum([float(ref.cost_price or 0) for ref in refs])
        total_profit = total_selling_price - total_cost_price

        client_name = '未指定客户'
        if project.company_id and project.company:
            client_name = project.company.company_name

        project_data = {
            'id': project.id,
            'hid': project.hid,
            'name': project.desc or f'项目 {project.hid}',
            'client': client_name,
            'leader': project.leader_name or '未指定负责人',
            'status': project.status,
            'type': project.type or '综合',
            'created_at': project.created_at,
            'total_selling': total_selling_price,
            'total_cost': total_cost_price,
            'total_profit': total_profit,
            'ref_count': len(refs)
        }
        recent_projects.append(project_data)

    # 获取待办事项
    todos = Todo.query.filter(
        Todo.user_id == current_user.id,
        Todo.is_completed == False
    ).order_by(
        Todo.priority.asc(),
        Todo.due_date.asc()
    ).limit(10).all()

    return render_template('mobile/staff_dashboard.html',
                         stats=stats,
                         recent_projects=recent_projects,
                         todos=todos)


@mobile_bp.route('/projects')
@login_required
def projects():
    """移动端项目列表"""
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.ref import ProjectRef
    from datetime import datetime, timedelta
    from sqlalchemy import func

    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 搜索参数
    search = request.args.get('q', '')
    status = request.args.get('status', '')
    time_range = request.args.get('time', '')  # 时间筛选: today, week, month

    # 基础查询
    query = ProjectHeader.query

    # 搜索过滤
    if search:
        query = query.filter(
            db.or_(
                ProjectHeader.hid.ilike(f'%{search}%'),
                ProjectHeader.desc.ilike(f'%{search}%')
            )
        )

    # 状态过滤
    if status:
        query = query.filter(ProjectHeader.status == status)

    # 时间范围过滤
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if time_range == 'today':
        query = query.filter(ProjectHeader.created_at >= today)
    elif time_range == 'week':
        week_start = today - timedelta(days=today.weekday())
        query = query.filter(ProjectHeader.created_at >= week_start)
    elif time_range == 'month':
        month_start = today.replace(day=1)
        query = query.filter(ProjectHeader.created_at >= month_start)

    # 分页查询
    projects_paginated = query.order_by(ProjectHeader.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # 统计数据（基于搜索和时间筛选，但不受状态筛选影响）
    stats_query = ProjectHeader.query
    if search:
        stats_query = stats_query.filter(
            db.or_(
                ProjectHeader.hid.ilike(f'%{search}%'),
                ProjectHeader.desc.ilike(f'%{search}%')
            )
        )
    if time_range == 'today':
        stats_query = stats_query.filter(ProjectHeader.created_at >= today)
    elif time_range == 'week':
        week_start = today - timedelta(days=today.weekday())
        stats_query = stats_query.filter(ProjectHeader.created_at >= week_start)
    elif time_range == 'month':
        month_start = today.replace(day=1)
        stats_query = stats_query.filter(ProjectHeader.created_at >= month_start)

    # 计算各状态数量
    total_count = stats_query.count()
    processing_count = stats_query.filter(ProjectHeader.status.in_(['draft', 'active'])).count()
    completed_count = stats_query.filter(ProjectHeader.status == 'completed').count()
    today_count = ProjectHeader.query.filter(ProjectHeader.created_at >= today).count()

    # 计算金额汇总（当前筛选条件下）
    total_selling = 0
    total_cost = 0
    for project in stats_query.all():
        total_selling += project.total_selling_amount or 0
        total_cost += project.total_cost_amount or 0
    total_profit = total_selling - total_cost

    stats = {
        'total': total_count,
        'processing': processing_count,
        'completed': completed_count,
        'today': today_count,
        'total_selling': total_selling,
        'total_cost': total_cost,
        'total_profit': total_profit
    }

    return render_template('mobile/projects.html',
                         projects=projects_paginated,
                         search=search,
                         status=status,
                         time_range=time_range,
                         stats=stats)


@mobile_bp.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    """移动端项目详情"""
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.projects.models.project_member import ProjectMember
    from App_new.utils.permissions import can_access_project

    project = ProjectHeader.query.get_or_404(project_id)

    # 权限检查
    if not can_access_project(project, current_user):
        flash('您没有权限访问此项目', 'error')
        return redirect(url_for('mobile.projects'))

    # 获取REF列表
    refs = ProjectRef.query.filter_by(header_id=project_id).all()

    # 获取人员列表
    members = ProjectMember.query.filter_by(header_id=project_id).order_by(
        ProjectMember.is_leader.desc(),
        ProjectMember.id
    ).all()

    # 上一个/下一个项目
    prev_project = ProjectHeader.query.filter(
        ProjectHeader.id < project_id
    ).order_by(ProjectHeader.id.desc()).first()

    next_project = ProjectHeader.query.filter(
        ProjectHeader.id > project_id
    ).order_by(ProjectHeader.id.asc()).first()

    return render_template('mobile/project_detail.html',
                         project=project,
                         refs=refs,
                         members=members,
                         prev_project=prev_project,
                         next_project=next_project)


@mobile_bp.route('/todos')
@login_required
def todos():
    """移动端待办列表"""
    from App_new.shared.models.Utilsmodels import Todo

    status_filter = request.args.get('status', 'pending')

    query = Todo.query.filter(Todo.user_id == current_user.id)

    if status_filter == 'pending':
        query = query.filter(Todo.is_completed == False)
    elif status_filter == 'completed':
        query = query.filter(Todo.is_completed == True)

    todos = query.order_by(
        Todo.priority.asc(),
        Todo.due_date.asc()
    ).all()

    return render_template('mobile/todos.html',
                         todos=todos,
                         status_filter=status_filter,
                         now=datetime.now())


@mobile_bp.route('/todo/<int:todo_id>')
@login_required
def todo_detail(todo_id):
    """移动端待办详情"""
    from App_new.shared.models.Utilsmodels import Todo

    todo = Todo.query.get_or_404(todo_id)

    return render_template('mobile/todo_detail.html', todo=todo)


@mobile_bp.route('/todo/<int:todo_id>/complete', methods=['POST'])
@login_required
def complete_todo(todo_id):
    """完成待办事项"""
    from App_new.shared.models.Utilsmodels import Todo

    todo = Todo.query.get_or_404(todo_id)

    if todo.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    todo.is_completed = True
    todo.completed_at = datetime.now()
    todo.completed_by = current_user.id
    db.session.commit()

    return jsonify({'success': True, 'message': '已完成'})


@mobile_bp.route('/create-todo', methods=['GET', 'POST'])
@login_required
def create_todo():
    """创建待办事项"""
    from App_new.shared.models.Utilsmodels import Todo

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority_str = request.form.get('priority', 'medium')
        due_date_str = request.form.get('due_date', '')

        # 转换优先级：high=1, medium=2, low=3
        priority_map = {'high': 1, 'medium': 2, 'low': 3}
        priority = priority_map.get(priority_str, 2)

        if not title:
            flash('请输入标题', 'error')
            return redirect(url_for('mobile.create_todo'))

        todo = Todo(
            title=title,
            description=description,
            priority=priority,
            user_id=current_user.id
        )

        if due_date_str:
            try:
                todo.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        db.session.add(todo)
        db.session.commit()

        flash('待办事项已创建', 'success')
        return redirect(url_for('mobile.todos'))

    return render_template('mobile/create_todo.html')


@mobile_bp.route('/create-project')
@login_required
def create_project():
    """创建项目 - 引导用户使用桌面版"""
    return render_template('mobile/desktop_required.html',
                         title='创建项目',
                         message='创建项目需要填写较多信息，建议使用电脑操作。',
                         desktop_url=url_for('business_projects.project_create.create_header'))


@mobile_bp.route('/search')
@login_required
def search():
    """移动端搜索"""
    q = request.args.get('q', '')

    results = {
        'projects': [],
        'todos': []
    }

    if q:
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.shared.models.Utilsmodels import Todo

        # 搜索项目
        results['projects'] = ProjectHeader.query.filter(
            db.or_(
                ProjectHeader.hid.ilike(f'%{q}%'),
                ProjectHeader.desc.ilike(f'%{q}%')
            )
        ).limit(10).all()

        # 搜索待办
        results['todos'] = Todo.query.filter(
            Todo.user_id == current_user.id,
            Todo.title.ilike(f'%{q}%')
        ).limit(10).all()

    return render_template('mobile/search.html', q=q, results=results)


@mobile_bp.route('/scan')
@login_required
def scan():
    """扫一扫 - 占位页面"""
    return render_template('mobile/coming_soon.html',
                         title='扫一扫',
                         message='扫码功能即将上线')


@mobile_bp.route('/notifications')
@login_required
def notifications():
    """通知列表"""
    return render_template('mobile/notifications.html')


@mobile_bp.route('/profile')
@login_required
def profile():
    """个人中心"""
    return render_template('mobile/profile.html')


@mobile_bp.route('/logout')
@login_required
def logout():
    """退出登录"""
    from flask_login import logout_user
    logout_user()
    flash('已退出登录', 'success')
    return redirect(url_for('auth_profile.staff_login'))


# ==================== 机票工具 ====================
@mobile_bp.route('/flight-tools')
@login_required
def flight_tools():
    """移动端机票工具入口"""
    return render_template('mobile/flight_tools.html')


@mobile_bp.route('/flight-conversion', methods=['GET', 'POST'])
@login_required
def flight_conversion():
    """移动端机票行程转换"""
    from App_new.utils.ConvertFlightItinerary import format_flight_info
    from App_new.business.flight.models.models import AirportData

    def city_language(city_name):
        """获取城市中英文名"""
        if not city_name:
            return "未知机场", "Unknown Airport"
        try:
            airport = AirportData.query.with_entities(
                AirportData.airport_name_cn, AirportData.airport_name_en
            ).filter_by(airport_IATA=city_name).first()
            if not airport:
                return "未知机场", "Unknown Airport"
            return airport
        except Exception:
            return "未知机场", "Unknown Airport"

    output_text = ""
    error_msg = ""

    if request.method == 'POST':
        input_text = request.form.get('input_text', '').strip()
        language = request.form.get('language', 'chinese')
        luggage = request.form.get('luggage', '')
        price = request.form.get('price', '')

        if not input_text:
            error_msg = "请输入行程数据"
        else:
            try:
                if language == "english":
                    output_text = format_flight_info(city_language, texts=input_text, language='EN', luggage=luggage, price=price)
                else:
                    output_text = format_flight_info(city_language, texts=input_text, luggage=luggage, price=price)
            except Exception as e:
                error_msg = f"转换失败：{str(e)}"

        # AJAX 请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if error_msg:
                return jsonify({'error': error_msg}), 400
            return jsonify({'success': True, 'output_text': output_text})

    return render_template('mobile/flight_conversion.html',
                         output_text=output_text,
                         error_msg=error_msg)


@mobile_bp.route('/athina-code', methods=['GET', 'POST'])
@login_required
def athina_code():
    """移动端 ATHINA 代码生成"""
    return render_template('mobile/athina_code.html')


@mobile_bp.route('/flight-order/create', methods=['GET', 'POST'])
@login_required
def flight_order_create():
    """移动端创建机票订单"""
    from App_new.shared.models.Suppliers import Supplier
    from App_new.shared.models.business_types import BusinessType

    # 获取供应商列表
    suppliers = Supplier.query.filter_by(status='active').order_by(Supplier.name).all()
    supplier_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()

    return render_template('mobile/flight_order_create.html',
                         suppliers=suppliers,
                         supplier_types=supplier_types)


# ==================== 公开页面（无需登录） ====================

@mobile_bp.route('/home')
def public_home():
    """手机端公开首页 - 无需登录"""
    from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries
    from App_new.business.tour.models.Packagemodels import CompanyInfo, Product, ProductCity, HomeBanner
    from sqlalchemy import or_
    from datetime import date

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 获取精选旅游产品（最多6个）
    tour_packages_raw = Product.query.filter(
        or_(
            Product.product_status == 'active',
            Product.product_status.is_(None),
            Product.product_status == ''
        )
    ).order_by(Product.is_featured.desc(), Product.created_at.desc()).limit(6).all()

    # 转换为模板需要的格式
    tour_packages = []
    for product in tour_packages_raw:
        price_display = f"SGD {product.base_price:,.0f}" if product.base_price else "价格面议"
        duration_display = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else ""
        destination_display = product.city_name or product.destination_city or ""
        if product.country and product.country != '未知':
            destination_display = f"{product.country} · {destination_display}"

        tour_packages.append({
            'id': product.id,
            'name': product.product_name,
            'destination': destination_display,
            'duration': duration_display,
            'price': price_display,
            'image': product.cover_image,
            'is_featured': product.is_featured,
            'product_type': product.product_type
        })

    # 获取签证国家
    visa_countries_raw = db.session.query(
        VisaCountries.country_name_CN,
        VisaCountries.flag_file,
        func.count(VisaTypes.id).label('visa_count')
    ).join(VisaTypes, VisaTypes.country_id == VisaCountries.id).filter(
        VisaTypes.is_active == True
    ).group_by(VisaCountries.id).order_by(desc('visa_count')).limit(8).all()

    visa_countries = [{
        'name': vc[0],
        'flag': vc[1],
        'visa_count': vc[2]
    } for vc in visa_countries_raw]

    # 获取首页轮播图
    banners = HomeBanner.get_active_banners()

    # 统计数据
    stats = {
        'packages': len(tour_packages_raw),
        'visa_countries': len(visa_countries),
        'destinations': db.session.query(ProductCity.country_name).filter(
            ProductCity.country_name.isnot(None)
        ).distinct().count()
    }

    return render_template('mobile/public_home.html',
                         company=company_info,
                         tour_packages=tour_packages,
                         visa_countries=visa_countries,
                         banners=banners,
                         stats=stats)
