# -*- coding: utf-8 -*-
"""
移动端路由
提供针对手机优化的简化版界面
"""

from flask import render_template, redirect, url_for, request, jsonify, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc

from . import mobile_bp
from App_new.exts import db, csrf


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
            base_query = base_query.filter(ProjectHeader.staff_id == current_user.id)

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
    from App_new.business.projects.models.project_member import ProjectMember
    from datetime import datetime, timedelta
    from sqlalchemy import func

    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 搜索参数
    search = (request.args.get('q', '') or '').strip()
    status = request.args.get('status', '')
    time_range = request.args.get('time', '')  # 时间筛选: today, week, month

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def scope_by_permission(query):
        """按员工等级限制可见范围（口径与桌面端 project_list 一致）

        原来手机端列表完全没做权限过滤，1级员工能在列表里看到全公司的项目和金额，
        点进去才被 can_access_project 拦下。
        """
        if current_user.role and current_user.role.name == 'staff':
            staff_level = 1
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            if staff_level == 1:
                query = query.filter(ProjectHeader.staff_id == current_user.id)
        return query

    def apply_filters(query, with_status=True):
        """套用权限 + 搜索 + 时间（+可选状态）筛选"""
        query = scope_by_permission(query)

        if search:
            query = query.filter(
                db.or_(
                    ProjectHeader.hid.ilike(f'%{search}%'),
                    ProjectHeader.desc.ilike(f'%{search}%')
                )
            )

        if with_status and status:
            query = query.filter(ProjectHeader.status == status)

        if time_range == 'today':
            query = query.filter(ProjectHeader.created_at >= today)
        elif time_range == 'week':
            week_start = today - timedelta(days=today.weekday())
            query = query.filter(ProjectHeader.created_at >= week_start)
        elif time_range == 'month':
            query = query.filter(ProjectHeader.created_at >= today.replace(day=1))

        return query

    # ---------- 当前页项目 ----------
    projects_paginated = apply_filters(ProjectHeader.query).options(
        db.joinedload(ProjectHeader.company),
        db.selectinload(ProjectHeader.refs)
    ).order_by(ProjectHeader.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # ---------- 卡片数据：整页批量算，避免每张卡都去查库 ----------
    # 原实现每张卡要查 refs / members / 每个ref的发票和收款，一页轻松几百条SQL。
    page_ids = [p.id for p in projects_paginated.items]
    member_counts = {}
    unpaid_by_project = {}
    if page_ids:
        member_counts = dict(
            db.session.query(ProjectMember.header_id, func.count(ProjectMember.id))
            .filter(ProjectMember.header_id.in_(page_ids))
            .group_by(ProjectMember.header_id).all()
        )
        ref_unpaid = ProjectRef.get_refs_unpaid_bulk(page_ids)
        for p in projects_paginated.items:
            unpaid_by_project[p.id] = sum(ref_unpaid.get(r.id, 0.0) for r in p.refs)

    cards = {}
    for p in projects_paginated.items:
        selling = sum(float(r.selling_price or 0) for r in p.refs)
        cards[p.id] = {
            'ref_count': len(p.refs),
            'member_count': member_counts.get(p.id, 0),
            'selling': selling,
            'unpaid': unpaid_by_project.get(p.id, 0.0),
        }

    # ---------- 统计汇总：交给数据库聚合，不再把全表对象取到内存 ----------
    # 原实现是 `for project in stats_query.all()` 遍历全部命中项目再逐个走 @property，
    # 无筛选时等于把整库项目连同 refs 全部加载一遍，首屏基本卡在这里。
    stats_base = apply_filters(ProjectHeader.query, with_status=False)

    total_count = stats_base.with_entities(func.count(ProjectHeader.id)).scalar() or 0
    processing_count = stats_base.filter(
        ProjectHeader.status.in_(['draft', 'active'])
    ).with_entities(func.count(ProjectHeader.id)).scalar() or 0
    completed_count = stats_base.filter(
        ProjectHeader.status == 'completed'
    ).with_entities(func.count(ProjectHeader.id)).scalar() or 0
    today_count = scope_by_permission(ProjectHeader.query).filter(
        ProjectHeader.created_at >= today
    ).with_entities(func.count(ProjectHeader.id)).scalar() or 0

    amount_query = db.session.query(
        func.coalesce(func.sum(ProjectRef.selling_price), 0),
        func.coalesce(func.sum(ProjectRef.cost_price), 0)
    ).select_from(ProjectHeader).outerjoin(
        ProjectRef, ProjectRef.header_id == ProjectHeader.id
    )
    total_selling, total_cost = apply_filters(amount_query, with_status=False).one()
    total_selling = float(total_selling or 0)
    total_cost = float(total_cost or 0)

    stats = {
        'total': total_count,
        'processing': processing_count,
        'completed': completed_count,
        'today': today_count,
        'total_selling': total_selling,
        'total_cost': total_cost,
        'total_profit': total_selling - total_cost
    }

    return render_template('mobile/projects.html',
                         projects=projects_paginated,
                         cards=cards,
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
    refs = ProjectRef.query.filter_by(header_id=project_id).options(
        db.joinedload(ProjectRef.ref_type),
        db.joinedload(ProjectRef.supplier)
    ).all()
    ref_ids = [r.id for r in refs]

    # 预加载每个REF的EO / Invoice / 未收款
    # 原来是在循环里逐个REF查库（EO一次、发票明细一次，模板里 unpaid_amount 再各查一轮），
    # 现在整批一次查完再在内存里分组。
    from App_new.business.projects.models.eo import ProjectEO
    from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem

    eos_by_ref = {}
    invoice_numbers_by_ref = {}
    unpaid_by_ref = {}
    if ref_ids:
        for eo in ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).all():
            eos_by_ref.setdefault(eo.ref_id, []).append(eo)

        invoice_rows = db.session.query(
            InvoiceItem.ref_id, ProjectInvoice.invoice_number
        ).join(
            ProjectInvoice, InvoiceItem.invoice_id == ProjectInvoice.id
        ).filter(
            InvoiceItem.ref_id.in_(ref_ids),
            ProjectInvoice.status != 'cancelled'
        ).all()
        for ref_id, invoice_number in invoice_rows:
            if invoice_number:
                invoice_numbers_by_ref.setdefault(ref_id, set()).add(invoice_number)

        unpaid_by_ref = ProjectRef.get_refs_unpaid_bulk([project_id])

    for ref in refs:
        ref._eo_list = eos_by_ref.get(ref.id, [])
        ref._invoice_numbers = sorted(invoice_numbers_by_ref.get(ref.id, set()))
        ref._unpaid = unpaid_by_ref.get(ref.id, 0.0)

    # 财务汇总（在内存里算，避免模板反复触发 @property 重新查库）
    total_selling = sum(float(r.selling_price or 0) for r in refs)
    total_cost = sum(float(r.cost_price or 0) for r in refs)
    finance = {
        'selling': total_selling,
        'cost': total_cost,
        'profit': total_selling - total_cost,
        'unpaid': sum(ref._unpaid for ref in refs),
    }

    # 获取人员列表
    members = ProjectMember.query.filter_by(header_id=project_id).order_by(
        ProjectMember.is_leader.desc(),
        ProjectMember.id
    ).all()

    # 上一个/下一个项目（限制在当前用户可见范围内，否则点"下一个"会被权限拦回列表）
    def scoped(query):
        if current_user.role and current_user.role.name == 'staff':
            staff_level = 1
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            if staff_level == 1:
                query = query.filter(ProjectHeader.staff_id == current_user.id)
        return query

    prev_project = scoped(ProjectHeader.query.filter(
        ProjectHeader.id < project_id
    )).order_by(ProjectHeader.id.desc()).first()

    next_project = scoped(ProjectHeader.query.filter(
        ProjectHeader.id > project_id
    )).order_by(ProjectHeader.id.asc()).first()

    return render_template('mobile/project_detail.html',
                         project=project,
                         refs=refs,
                         finance=finance,
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


@mobile_bp.route('/booking-code', methods=['GET', 'POST'])
@login_required
def booking_code():
    """移动端订位代码生成"""
    return render_template('mobile/booking_code.html')


@mobile_bp.route('/flight-order/create', methods=['GET', 'POST'])
@login_required
def flight_order_create():
    """移动端创建机票订单"""
    from App_new.business.projects.models.project import CustomerCompany
    from App_new.shared.models.business_types import BusinessType

    # 获取供应商列表
    suppliers = CustomerCompany.query.filter(
        CustomerCompany.is_supplier == True,
        CustomerCompany.status == 'active'
    ).order_by(CustomerCompany.company_name).all()
    supplier_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()

    return render_template('mobile/flight_order_create.html',
                         suppliers=suppliers,
                         supplier_types=supplier_types)


# ==================== 账号管理 ====================

@mobile_bp.route('/accounts')
@login_required
def accounts():
    """移动端账号管理"""
    from App_new.shared.models.account import Account, ACCESS_LEVEL_PUBLIC, ACCESS_LEVEL_PRIVATE, ACCESS_LEVEL_LEVEL_1, ACCESS_LEVEL_LEVEL_2
    from App_new.utils.decorators import staff_only
    from sqlalchemy import or_

    # 检查是否是员工
    if not current_user.role or current_user.role.name not in ['admin', 'super_admin', 'staff']:
        flash('您没有权限访问此页面', 'error')
        return redirect(url_for('mobile.staff_dashboard'))

    # 构建基础查询
    query = Account.query

    # 根据用户权限过滤账号
    if current_user.role.name not in ['admin', 'super_admin']:
        # 获取用户的员工等级
        staff_level = 1
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1

        # 构建权限过滤条件
        access_conditions = [
            Account.access_level == ACCESS_LEVEL_PUBLIC,
            Account.access_level.is_(None),
        ]

        # 私有权限：仅创建者可见
        access_conditions.append(
            db.and_(
                Account.access_level == ACCESS_LEVEL_PRIVATE,
                or_(
                    Account.created_by == current_user.id,
                    Account.owner == current_user.username
                )
            )
        )

        # 根据员工等级添加可见权限
        if staff_level >= 1:
            access_conditions.append(Account.access_level == ACCESS_LEVEL_LEVEL_1)
        if staff_level >= 2:
            access_conditions.append(Account.access_level == ACCESS_LEVEL_LEVEL_2)

        query = query.filter(or_(*access_conditions))

    # 获取所有账号，按更新时间倒序
    accounts = query.order_by(Account.updated_at.desc()).all()

    # 获取所有类别
    categories = db.session.query(Account.category).filter(
        Account.category.isnot(None)
    ).distinct().all()
    categories = sorted([c[0] for c in categories if c[0]])

    return render_template('mobile/accounts.html',
                         accounts=accounts,
                         categories=categories)


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

    # 获取景点门票（最多6个）
    from App_new.business.products.models import ProductsUnified
    from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant

    attractions_raw = ProductsUnified.query.filter(
        ProductsUnified.product_category == 'ticket',
        ProductsUnified.parent_id.is_(None),
        ProductsUnified.product_status == 'active',
    ).order_by(ProductsUnified.is_featured.desc(), ProductsUnified.view_count.desc(), ProductsUnified.sort_order).limit(6).all()

    attractions = []
    for p in attractions_raw:
        # 计算最低价
        min_price = db.session.query(func.min(ProductsTicketVariant.adult_selling_price)).filter(
            ProductsTicketVariant.product_id == p.id,
            ProductsTicketVariant.is_active == True,
            ProductsTicketVariant.adult_selling_price > 0
        ).scalar()
        price_display = f"SGD {float(min_price):,.0f}" if min_price else "价格面议"

        location = ''
        if p.country:
            location = p.country
            if p.city:
                location += f' · {p.city}'

        attractions.append({
            'id': p.id,
            'name': p.product_name,
            'name_en': p.product_name_en or '',
            'location': location,
            'price': price_display,
            'image': p.cover_image,
            'is_featured': p.is_featured,
            'currency': p.currency or 'SGD',
        })

    # 获取首页轮播图
    banners = HomeBanner.get_active_banners()

    # 统计数据
    stats = {
        'packages': len(tour_packages_raw),
        'visa_countries': len(visa_countries),
        'attractions': len(attractions),
        'destinations': db.session.query(ProductCity.country_name).filter(
            ProductCity.country_name.isnot(None)
        ).distinct().count()
    }

    return render_template('mobile/public_home.html',
                         company=company_info,
                         tour_packages=tour_packages,
                         visa_countries=visa_countries,
                         attractions=attractions,
                         banners=banners,
                         stats=stats)


# 地区到国家的映射
REGION_COUNTRIES = {
    'southeast_asia': ['新加坡', '马来西亚', '泰国', '印尼', '印度尼西亚', '越南', '菲律宾', '柬埔寨', '老挝', '缅甸', '文莱'],
    'east_asia': ['日本', '韩国', '中国', '台湾', '香港', '澳门'],
    'europe': ['法国', '意大利', '德国', '英国', '西班牙', '瑞士', '荷兰', '希腊', '葡萄牙', '奥地利', '捷克', '匈牙利'],
    'america': ['美国', '加拿大', '墨西哥', '巴西', '阿根廷', '智利'],
    'oceania': ['澳大利亚', '新西兰', '斐济'],
    'middle_east': ['阿联酋', '土耳其', '埃及', '以色列', '约旦'],
    'south_asia': ['印度', '斯里兰卡', '马尔代夫', '尼泊尔']
}


@mobile_bp.route('/tour-packages')
def tour_packages():
    """手机端旅游配套页面 - 无需登录"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo, Product, ProductCity
    from sqlalchemy import or_
    from datetime import date
    import json

    # 获取搜索参数
    destination = request.args.get('destination', '').strip()
    departure_date = request.args.get('departure_date', '')
    return_date = request.args.get('return_date', '')
    pax = request.args.get('pax', '')
    region = request.args.get('region', '')
    country = request.args.get('country', '').strip()
    city = request.args.get('city', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 手机端每页显示10个

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 构建查询
    query = Product.query.filter(
        or_(
            Product.product_status == 'active',
            Product.product_status.is_(None),
            Product.product_status == ''
        )
    )

    # 标记是否需要join ProductCity
    need_join_city = False

    # 地区筛选
    if region and region in REGION_COUNTRIES:
        countries_in_region = REGION_COUNTRIES[region]
        region_conditions = []
        for country_name in countries_in_region:
            region_conditions.append(ProductCity.country_name.like(f'%{country_name}%'))
            region_conditions.append(Product.city_name.like(f'%{country_name}%'))
            region_conditions.append(Product.destination_city.like(f'%{country_name}%'))
        query = query.outerjoin(ProductCity, Product.city_id == ProductCity.id).filter(
            or_(*region_conditions)
        ).distinct()
        need_join_city = True

    # 国家筛选
    if country:
        if not need_join_city:
            query = query.outerjoin(ProductCity, Product.city_id == ProductCity.id)
        query = query.filter(ProductCity.country_name == country).distinct()

    # 城市筛选
    if city:
        query = query.filter(Product.city_name == city)

    # 目的地筛选
    if destination:
        query = query.filter(
            or_(
                Product.city_name.like(f'%{destination}%'),
                Product.destination_city.like(f'%{destination}%')
            )
        )

    # 日期筛选
    today = date.today()
    if departure_date:
        try:
            from datetime import datetime
            dep_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
            query = query.filter(
                or_(
                    Product.valid_from.is_(None),
                    Product.valid_from <= dep_date
                )
            )
        except:
            pass

    if return_date:
        try:
            from datetime import datetime
            ret_date = datetime.strptime(return_date, '%Y-%m-%d').date()
            query = query.filter(
                or_(
                    Product.valid_until.is_(None),
                    Product.valid_until >= ret_date
                )
            )
        except:
            pass

    # 人数筛选
    if pax:
        try:
            if pax == '1':
                min_pax = 1
            elif pax == '2':
                min_pax = 2
            elif pax == '3-5':
                min_pax = 3
            elif pax == '6-10':
                min_pax = 6
            elif pax == '10+':
                min_pax = 10
            else:
                min_pax = None

            if min_pax:
                query = query.filter(
                    or_(
                        Product.min_pax.is_(None),
                        Product.min_pax <= min_pax
                    )
                )
        except:
            pass

    # 排序
    query = query.order_by(Product.is_featured.desc(), Product.created_at.desc())

    # 分页
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    products = pagination.items

    # 转换为模板需要的格式
    packages = []
    for product in products:
        # 解析亮点（使用 getattr 安全获取）
        highlights = []
        product_highlights = getattr(product, 'highlights', None)
        if product_highlights:
            try:
                highlights = json.loads(product_highlights) if product_highlights.startswith('[') else product_highlights.split(',')
            except:
                highlights = [h.strip() for h in product_highlights.split(',') if h.strip()]

        # 格式化价格
        price_display = f"SGD {product.base_price:,.0f}" if product.base_price else "价格面议"
        if product.currency and product.currency != 'SGD':
            price_display = f"{product.currency} {product.base_price:,.0f}" if product.base_price else "价格面议"

        # 格式化天数
        duration_display = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "天数待定"

        # 目的地显示
        destination_display = product.city_name or product.destination_city or "目的地待定"
        if product.country and product.country != '未知':
            destination_display = f"{product.country} {destination_display}"

        packages.append({
            'id': product.id,
            'code': product.product_code or f'P{product.id:04d}',
            'name': product.product_name,
            'destination': destination_display,
            'duration': duration_display,
            'price': price_display,
            'image': product.cover_image if product.cover_image else None,
            'highlights': highlights[:5] if highlights else ['精彩行程', '专业服务']
        })

    # 获取国家和城市列表
    countries = db.session.query(ProductCity.country_name).filter(
        ProductCity.country_name.isnot(None)
    ).distinct().order_by(ProductCity.country_name).all()
    countries = [c[0] for c in countries if c[0]]

    # 根据选择的国家获取城市列表
    cities = []
    if country:
        cities = db.session.query(ProductCity.city_name).filter(
            ProductCity.country_name == country,
            ProductCity.city_name.isnot(None)
        ).distinct().order_by(ProductCity.city_name).all()
        cities = [c[0] for c in cities if c[0]]
    else:
        cities = db.session.query(Product.city_name).filter(
            Product.city_name.isnot(None)
        ).distinct().order_by(Product.city_name).all()
        cities = [c[0] for c in cities if c[0]]

    return render_template('mobile/tour_packages.html',
                         packages=packages,
                         pagination=pagination,
                         destination=destination,
                         departure_date=departure_date,
                         return_date=return_date,
                         pax=pax,
                         region=region,
                         country=country,
                         city=city,
                         countries=countries,
                         cities=cities,
                         company=company_info)


@mobile_bp.route('/tour-package/<int:package_id>')
def tour_package_detail(package_id):
    """手机端旅游配套详情 - 无需登录"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo, Product, ProductItinerary
    from datetime import date
    import json

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 查询产品详情
    product = Product.query.filter_by(id=package_id).first_or_404()

    # 检查产品是否有效
    today = date.today()
    if product.valid_until and product.valid_until < today:
        flash('该旅游配套已过期', 'warning')
        return redirect(url_for('mobile.tour_packages'))

    # 解析包含服务（支持换行和逗号分隔）
    includes = []
    if product.included_services:
        try:
            if product.included_services.startswith('['):
                includes = json.loads(product.included_services)
            elif '\n' in product.included_services:
                includes = [i.strip() for i in product.included_services.split('\n') if i.strip()]
            else:
                includes = [i.strip() for i in product.included_services.split(',') if i.strip()]
        except:
            includes = [i.strip() for i in product.included_services.split('\n') if i.strip()]

    # 解析不包含服务（支持换行和逗号分隔）
    excludes = []
    if product.excluded_services:
        try:
            if product.excluded_services.startswith('['):
                excludes = json.loads(product.excluded_services)
            elif '\n' in product.excluded_services:
                excludes = [e.strip() for e in product.excluded_services.split('\n') if e.strip()]
            else:
                excludes = [e.strip() for e in product.excluded_services.split(',') if e.strip()]
        except:
            excludes = [e.strip() for e in product.excluded_services.split('\n') if e.strip()]

    # 解析注意事项
    notes = []
    if product.important_notes:
        try:
            notes = json.loads(product.important_notes) if product.important_notes.startswith('[') else product.important_notes.split('\n')
        except:
            notes = [n.strip() for n in product.important_notes.split('\n') if n.strip()]

    # 解析亮点（使用 getattr 安全获取）
    highlights_list = []
    product_highlights = getattr(product, 'highlights', None)
    if product_highlights:
        try:
            highlights_list = json.loads(product_highlights) if product_highlights.startswith('[') else product_highlights.split(',')
        except:
            highlights_list = [h.strip() for h in product_highlights.split(',') if h.strip()]

    # 格式化价格
    price_display = f"SGD {product.base_price:,.0f}" if product.base_price else "价格面议"
    if product.currency and product.currency != 'SGD':
        price_display = f"{product.currency} {product.base_price:,.0f}" if product.base_price else "价格面议"

    # 格式化天数
    duration_display = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "天数待定"

    # 目的地显示
    destination_display = product.city_name or product.destination_city or "目的地待定"
    if product.country and product.country != '未知':
        destination_display = f"{product.country} {destination_display}"

    # 获取行程数据
    itineraries = ProductItinerary.query.filter_by(product_id=package_id).order_by(ProductItinerary.day_number).all()

    # 获取价格变体
    from App_new.business.tour.models.Packagemodels import ProductPriceVariant
    price_variants = ProductPriceVariant.query.filter_by(product_id=package_id, is_active=True).all()
    itinerary_list = []
    for it in itineraries:
        day_data = {
            'day': it.day_number,
            'title': it.day_title or f'第{it.day_number}天行程',
            'content': it.content,
            'activities': [it.content] if it.content else [],
            'images': [img for img in [it.image1, it.image2, it.image3] if img]
        }
        itinerary_list.append(day_data)

    # 准备产品详情数据
    package_data = {
        'id': product.id,
        'code': product.product_code or f'PKG-{product.id:04d}',
        'name': product.product_name,
        'destination': destination_display,
        'country': product.country,
        'duration': duration_display,
        'price': price_display,
        'child_price': f"{product.currency or 'SGD'} {product.child_price:,.0f}" if product.child_price else None,
        'image': product.cover_image,
        'description': product.product_description or None,
        'highlights': highlights_list,
        'includes': includes if includes else ['专业导游', '优质服务', '舒适住宿', '部分餐饮'],
        'excludes': excludes if excludes else ['个人消费', '小费', '旅游保险', '签证费用'],
        'notes': notes if notes else ['请确保护照有效期6个月以上', '建议购买旅游保险', '行程可能因天气调整'],
        'itinerary': itinerary_list if itinerary_list else None,
        'min_pax': product.min_pax,
        'max_pax': product.max_pax,
        'product_type': product.product_type,
        'supplier': product.display_company_name,
        'price_variants': [pv.to_dict() for pv in price_variants] if price_variants else [],
        'currency': product.currency or 'SGD'
    }

    return render_template('mobile/tour_package_detail.html',
                         package=package_data,
                         company=company_info)


@mobile_bp.route('/attractions')
def attractions():
    """手机端景点门票列表页"""
    from App_new.business.products.models import ProductsUnified
    from App_new.business.products.models.products_ticket_ext import ProductsTicketExt
    from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant
    from App_new.business.tour.models.Packagemodels import CompanyInfo

    keyword = request.args.get('keyword', '').strip()
    country = request.args.get('country', '').strip()
    city = request.args.get('city', '').strip()

    query = ProductsUnified.query.outerjoin(
        ProductsTicketExt, ProductsTicketExt.product_id == ProductsUnified.id
    ).filter(
        ProductsUnified.product_category == 'ticket',
        ProductsUnified.parent_id.is_(None),
        ProductsUnified.product_status == 'active',
    )

    if keyword:
        query = query.filter(
            or_(
                ProductsUnified.product_name.ilike(f'%{keyword}%'),
                ProductsUnified.product_name_en.ilike(f'%{keyword}%'),
                ProductsTicketExt.venue_name.ilike(f'%{keyword}%'),
            )
        )
    if country:
        query = query.filter(ProductsUnified.country == country)
    if city:
        query = query.filter(ProductsUnified.city == city)

    products = query.order_by(
        ProductsUnified.is_featured.desc(), ProductsUnified.view_count.desc(), ProductsUnified.sort_order
    ).all()

    attractions_data = []
    for p in products:
        # 取代表性票种（大门票）：按排序权重取第一个有价格的激活票种
        main_variant = ProductsTicketVariant.query.filter(
            ProductsTicketVariant.product_id == p.id,
            ProductsTicketVariant.is_active == True,
            ProductsTicketVariant.adult_selling_price > 0
        ).order_by(
            ProductsTicketVariant.sort_order, ProductsTicketVariant.id
        ).first()

        adult_price = float(main_variant.adult_selling_price) if main_variant and main_variant.adult_selling_price else None
        child_price = float(main_variant.child_selling_price) if main_variant and main_variant.child_selling_price else None
        currency = (main_variant.currency if main_variant else None) or 'SGD'

        location = ''
        if p.country:
            location = p.country
            if p.city:
                location += f' · {p.city}'

        attractions_data.append({
            'id': p.id,
            'name': p.product_name,
            'name_en': p.product_name_en or '',
            'location': location,
            'currency': currency,
            'adult_price': adult_price,
            'child_price': child_price,
            'image': p.cover_image,
            'is_featured': p.is_featured,
        })

    # 国家 + 区域(城市)列表，按国家分组，供前端联动筛选
    country_city_rows = db.session.query(
        ProductsUnified.country, ProductsUnified.city
    ).filter(
        ProductsUnified.product_category == 'ticket',
        ProductsUnified.product_status == 'active',
        ProductsUnified.parent_id.is_(None),
        ProductsUnified.country.isnot(None),
        ProductsUnified.country != ''
    ).distinct().order_by(ProductsUnified.country, ProductsUnified.city).all()

    countries = []
    city_map = {}
    for c, ct in country_city_rows:
        if c not in city_map:
            city_map[c] = []
            countries.append(c)
        if ct and ct not in city_map[c]:
            city_map[c].append(ct)

    company_info = CompanyInfo.query.first()
    return render_template('mobile/attractions.html',
                         attractions=attractions_data,
                         countries=countries,
                         city_map=city_map,
                         keyword=keyword,
                         country=country,
                         city=city,
                         company=company_info)


@mobile_bp.route('/attractions/<int:product_id>')
def attraction_detail(product_id):
    """手机端景点门票详情页"""
    from App_new.business.products.models import ProductsUnified
    from App_new.business.products.models.products_ticket_ext import ProductsTicketExt
    from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant
    from App_new.business.tour.models.Packagemodels import CompanyInfo

    product = ProductsUnified.query.filter_by(
        id=product_id, product_category='ticket', product_status='active'
    ).first()
    if not product:
        return "未找到该景点门票", 404

    product.view_count = (product.view_count or 0) + 1
    db.session.commit()

    ticket_ext = ProductsTicketExt.query.filter_by(product_id=product_id).first()
    variants = ProductsTicketVariant.query.filter_by(
        product_id=product_id, is_active=True
    ).order_by(ProductsTicketVariant.sort_order, ProductsTicketVariant.id).all()

    delivery_map = {
        'e_ticket': '电子票', 'physical': '实体票',
        'voucher': '兑换券', 'pickup': '现场取票'
    }

    def none_safe(val):
        if val is not None and str(val).strip().lower() == 'none':
            return None
        return val

    variants_data = []
    for v in variants:
        variants_data.append({
            'id': v.id,
            'name': v.variant_name,
            'name_en': none_safe(v.variant_name_en),
            'description': none_safe(v.description),
            'adult_price': float(v.adult_selling_price) if v.adult_selling_price else None,
            'child_price': float(v.child_selling_price) if v.child_selling_price else None,
            'delivery_type': delivery_map.get(v.delivery_type, v.delivery_type) if none_safe(v.delivery_type) else None,
            'includes': none_safe(v.includes),
            'excludes': none_safe(v.excludes),
            'important_notes': none_safe(v.important_notes),
            'currency': v.currency or 'SGD',
        })

    # 清理 None 字符串
    for f in ['description', 'product_name_en']:
        val = getattr(product, f, None)
        if val and str(val).strip().lower() == 'none':
            setattr(product, f, None)

    company_info = CompanyInfo.query.first()
    return render_template('mobile/attraction_detail.html',
                         product=product,
                         ticket_ext=ticket_ext,
                         variants=variants_data,
                         is_logged_in=current_user.is_authenticated,
                         company=company_info)


@mobile_bp.route('/book-ticket/<int:product_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def book_ticket(product_id):
    """手机端景点门票下单"""
    from App_new.business.products.models import ProductsUnified
    from App_new.business.products.models.products_ticket_ext import ProductsTicketExt
    from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.member.models.order import Order
    from datetime import date, datetime
    import json, random

    company_info = CompanyInfo.query.first()
    product = ProductsUnified.query.filter_by(
        id=product_id, product_category='ticket', product_status='active'
    ).first_or_404()

    ticket_ext = ProductsTicketExt.query.filter_by(product_id=product_id).first()
    variants = ProductsTicketVariant.query.filter_by(
        product_id=product_id, is_active=True
    ).order_by(ProductsTicketVariant.sort_order, ProductsTicketVariant.id).all()

    def none_safe(val):
        if val is not None and str(val).strip().lower() == 'none':
            return None
        return val

    if request.method == 'POST':
        try:
            variant_id = request.form.get('variant_id', type=int)
            visit_date = request.form.get('visit_date', '')
            adult_count = int(request.form.get('adult_count', 1))
            child_count = int(request.form.get('child_count', 0))
            contact_name = request.form.get('contact_name', '')
            contact_email = request.form.get('contact_email', '')
            contact_phone = request.form.get('contact_phone', '')
            special_requirements = request.form.get('special_requirements', '')

            if not contact_name or not contact_phone:
                flash('请填写联系人信息', 'error')
                return redirect(url_for('mobile.book_ticket', product_id=product_id))

            # 获取票种
            variant = ProductsTicketVariant.query.get(variant_id) if variant_id else (variants[0] if variants else None)
            if not variant:
                flash('请选择票种', 'error')
                return redirect(url_for('mobile.book_ticket', product_id=product_id))

            # 计算价格
            adult_price = float(variant.adult_selling_price or 0)
            child_price = float(variant.child_selling_price or 0)
            total_amount = adult_count * adult_price + child_count * child_price

            # 生成订单号
            order_number = f"TK{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"

            location = product.country or ''
            if product.city:
                location += f' · {product.city}'

            description = f"""景点门票: {product.product_name}
票种: {variant.variant_name}
地点: {location}
游玩日期: {visit_date or '待定'}
人数: 成人{adult_count}人"""
            if child_count > 0:
                description += f", 儿童{child_count}人"

            order = Order(
                order_number=order_number,
                user_id=current_user.id,
                service_type='ticket',
                service_name=product.product_name,
                description=description,
                status='pending',
                currency=variant.currency or 'SGD',
                base_price=total_amount,
                total_amount=total_amount,
                customer_name=contact_name,
                customer_email=contact_email,
                customer_phone=contact_phone,
                special_requirements=special_requirements,
            )
            db.session.add(order)
            db.session.flush()

            # 订单项：结构化数据放到 properties（与桌面端保持一致）
            from App_new.member.models.order import OrderItem
            order_item = OrderItem(
                order_id=order.id,
                item_name=f"{product.product_name} - {variant.variant_name}",
                item_description=location,
                item_type='ticket',
                quantity=adult_count + child_count,
                unit_price=adult_price,
                total_price=total_amount,
                properties={
                    'product_id': product_id,
                    'variant_id': variant.id,
                    'variant_name': variant.variant_name,
                    'visit_date': visit_date,
                    'adult_count': adult_count,
                    'child_count': child_count,
                    'adult_price': adult_price,
                    'child_price': child_price,
                }
            )
            db.session.add(order_item)
            db.session.commit()

            flash('下单成功！我们将尽快与您联系确认', 'success')
            return redirect(url_for('mobile.orders_list'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'门票下单失败: {str(e)}')
            flash(f'下单失败: {str(e)}', 'error')
            return redirect(url_for('mobile.book_ticket', product_id=product_id))

    # GET: 显示下单表单
    variants_data = []
    for v in variants:
        variants_data.append({
            'id': v.id,
            'name': v.variant_name,
            'name_en': none_safe(v.variant_name_en),
            'adult_price': float(v.adult_selling_price) if v.adult_selling_price else 0,
            'child_price': float(v.child_selling_price) if v.child_selling_price else 0,
            'currency': v.currency or 'SGD',
        })

    user_profile = current_user.profile if hasattr(current_user, 'profile') else None

    # 从详情页传来的预选参数
    prefill = {
        'variant_id': request.args.get('variant_id', type=int),
        'visit_date': request.args.get('visit_date', ''),
        'adult_count': request.args.get('adult_count', 1, type=int),
        'child_count': request.args.get('child_count', 0, type=int),
    }

    return render_template('mobile/book_ticket.html',
                         product=product,
                         ticket_ext=ticket_ext,
                         variants=variants_data,
                         prefill=prefill,
                         user_profile=user_profile,
                         company=company_info)


@mobile_bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    """手机端编辑项目"""
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.auth.models.auth import AuthUser, UserProfile, Role
    from App_new.shared.models.Suppliers import CustomerCompany
    from App_new.utils.permissions import can_access_project

    project = ProjectHeader.query.get_or_404(project_id)
    if not can_access_project(project, current_user):
        flash('无权操作', 'error')
        return redirect(url_for('mobile.projects'))

    # 获取公司列表
    companies = CustomerCompany.query.filter_by(status='active').order_by(CustomerCompany.company_name).all()

    # 获取员工列表
    staff_role = Role.query.filter_by(name='staff').first()
    admin_role = Role.query.filter_by(name='admin').first()
    role_ids = [r.id for r in [staff_role, admin_role] if r]
    staff_list = []
    if role_ids:
        users = db.session.query(AuthUser.id, AuthUser.username, UserProfile.first_name, UserProfile.last_name
        ).outerjoin(UserProfile, AuthUser.id == UserProfile.user_id
        ).filter(AuthUser.role_id.in_(role_ids), AuthUser.is_active == True).all()
        for u in users:
            name = f"{u.first_name or ''}{u.last_name or ''}".strip() or u.username
            staff_list.append({'id': u.id, 'name': name})

    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}

            # 只更新请求里出现过的字段。
            # 详情页的就地编辑只提交单个字段（如 {"status": "completed"}），
            # 若沿用 data.get(key) 的写法，没提交的 company_id 会被当成 None 把客户公司清掉。
            if 'company_id' in data:
                company_id = data.get('company_id')
                try:
                    company_id = int(company_id) if company_id not in (None, '') else 0
                except (TypeError, ValueError):
                    company_id = 0
                project.company_id = company_id if company_id > 0 else None

            if 'desc' in data:
                project.desc = data.get('desc')
            if 'contact' in data:
                project.contact = data.get('contact')
            if 'staff_id' in data and data.get('staff_id'):
                project.staff_id = int(data.get('staff_id'))
            if 'status' in data and data.get('status'):
                project.status = data.get('status')
            if 'remarks' in data:
                project.remarks = data.get('remarks')
            if 'reminder_event' in data:
                project.reminder_event = data.get('reminder_event')

            if 'reminder_date' in data:
                reminder_date = data.get('reminder_date') or ''
                if reminder_date:
                    from datetime import datetime as dt
                    project.reminder_date = dt.strptime(reminder_date, '%Y-%m-%d').date()
                else:
                    project.reminder_date = None

            db.session.commit()
            return jsonify({'success': True, 'message': '保存成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

    return render_template('mobile/edit_project.html',
                         project=project,
                         companies=companies,
                         staff_list=staff_list)


@mobile_bp.route('/project/<int:project_id>/receipts')
@login_required
def project_receipts(project_id):
    """手机端项目收款记录"""
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.projects.models.receipt import ProjectReceipt
    from App_new.utils.permissions import can_access_project
    import json

    project = ProjectHeader.query.get_or_404(project_id)
    if not can_access_project(project, current_user):
        flash('无权访问', 'error')
        return redirect(url_for('mobile.projects'))

    # 收款记录
    receipts = ProjectReceipt.query.filter_by(header_id=project_id).order_by(
        ProjectReceipt.payment_date.desc()
    ).all()

    # 财务统计
    total_selling = float(project.total_selling_amount or 0)
    total_received = 0
    for ref in project.refs:
        if ref.selling_price:
            total_received += ProjectReceipt.get_ref_total_received(ref.id, project_id)
    unpaid = total_selling - total_received

    return render_template('mobile/project_receipts.html',
                         project=project,
                         receipts=receipts,
                         total_selling=total_selling,
                         total_received=total_received,
                         unpaid=unpaid)


@mobile_bp.route('/project/<int:project_id>/invoices')
@login_required
def project_invoices(project_id):
    """手机端项目发票列表"""
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.invoice import ProjectInvoice
    from App_new.utils.permissions import can_access_project

    project = ProjectHeader.query.get_or_404(project_id)
    if not can_access_project(project, current_user):
        flash('无权访问', 'error')
        return redirect(url_for('mobile.projects'))

    invoices = ProjectInvoice.query.filter_by(header_id=project_id).order_by(
        ProjectInvoice.created_at.desc()
    ).all()

    total_invoiced = ProjectInvoice.get_header_total_invoiced(project_id)
    total_paid = ProjectInvoice.get_header_total_paid(project_id)
    total_unpaid = total_invoiced - total_paid
    total_selling = sum(float(ref.selling_price or 0) for ref in project.refs)

    return render_template('mobile/project_invoices.html',
                         project=project,
                         invoices=invoices,
                         total_invoiced=total_invoiced,
                         total_paid=total_paid,
                         total_unpaid=total_unpaid,
                         total_selling=total_selling)


@mobile_bp.route('/invoice/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    """手机端发票详情"""
    from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
    from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
    import json

    invoice = ProjectInvoice.query.get_or_404(invoice_id)

    # 发票明细
    items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()

    # 收款记录
    allocations = ReceiptInvoiceAllocation.query.filter_by(invoice_id=invoice_id).all()
    payments = []
    for alloc in allocations:
        receipt = ProjectReceipt.query.get(alloc.receipt_id)
        if receipt and receipt.status == 'confirmed':
            payments.append({
                'receipt_number': receipt.receipt_number,
                'date': receipt.payment_date.strftime('%Y-%m-%d') if receipt.payment_date else '',
                'method': receipt.payment_method_display,
                'amount': float(alloc.allocated_amount),
            })

    return render_template('mobile/invoice_detail.html',
                         invoice=invoice,
                         items=items,
                         payments=payments)


@mobile_bp.route('/invoice/<int:invoice_id>/pdf')
@login_required
def invoice_pdf(invoice_id):
    """手机端发票PDF - 渲染打印版发票"""
    from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
    from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
    from App_new.business.projects.models.project_member import ProjectMember
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    import json

    invoice = ProjectInvoice.query.get_or_404(invoice_id)
    items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
    company = CompanyInfo.query.first()
    header = invoice.header

    # 为每个item的ref构建extra_data
    for item in items:
        if item.ref and item.ref.extra_info:
            try:
                item.ref.extra_data = json.loads(item.ref.extra_info)
            except:
                item.ref.extra_data = {}
        elif item.ref:
            item.ref.extra_data = {}

    # 客户显示信息
    customer_display = invoice.customer_name or ''
    customer_company_display = invoice.customer_company or ''
    if header and header.company:
        customer_company_display = header.company.company_name
    if header and header.contact:
        customer_display = header.contact

    # 收款记录
    payment_method_en = {
        'cash': 'Cash', 'bank_transfer': 'Bank Transfer',
        'credit_card': 'Credit Card', 'cheque': 'Cheque',
        'wechat': 'WeChat', 'other': 'Other'
    }
    payments = []
    allocations = ReceiptInvoiceAllocation.query.filter_by(invoice_id=invoice_id).all()
    for alloc in allocations:
        receipt = ProjectReceipt.query.get(alloc.receipt_id)
        if receipt and receipt.status == 'confirmed':
            payments.append({
                'date': receipt.payment_date.strftime('%d/%m/%Y') if receipt.payment_date else '',
                'ref': receipt.receipt_number,
                'method': payment_method_en.get(receipt.payment_method, receipt.payment_method),
                'amount': float(alloc.allocated_amount),
            })

    return render_template('mobile/invoice_print.html',
                         invoice=invoice, items=items, company=company,
                         customer_display=customer_display,
                         customer_company_display=customer_company_display,
                         payments=payments)


@mobile_bp.route('/project/<int:project_id>/receipt/create', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def create_receipt(project_id):
    """手机端创建收款"""
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
    from App_new.business.projects.models.invoice import ProjectInvoice
    from App_new.utils.permissions import can_access_project
    import json

    project = ProjectHeader.query.get_or_404(project_id)
    if not can_access_project(project, current_user):
        return jsonify({'success': False, 'message': '无权操作'})

    if request.method == 'POST':
        try:
            data = request.get_json()
            amount = float(data.get('amount', 0))
            payment_method = data.get('payment_method', 'bank_transfer')
            payment_date = data.get('payment_date', '')
            payer_name = data.get('payer_name', '')
            remarks = data.get('remarks', '')

            if amount <= 0:
                return jsonify({'success': False, 'message': '金额必须大于0'})

            unpaid = ProjectReceipt.get_project_unpaid_amount(project_id)
            if amount > unpaid + 0.01:
                return jsonify({'success': False, 'message': f'金额不能超过未收款{unpaid:.2f}'})

            # 按顺序分配到发票
            invoices = ProjectInvoice.query.filter_by(header_id=project_id).filter(
                ProjectInvoice.status.in_(['confirmed', 'partial'])
            ).order_by(ProjectInvoice.invoice_date).all()

            allocations = {}
            remaining = amount
            for inv in invoices:
                inv_unpaid = inv.unpaid_amount
                if inv_unpaid > 0 and remaining > 0:
                    allocated = min(inv_unpaid, remaining)
                    allocations[inv.id] = round(allocated, 2)
                    remaining -= allocated
                    if remaining <= 0.01:
                        break

            if not allocations:
                return jsonify({'success': False, 'message': '没有可分配的发票，请先生成发票'})

            from datetime import datetime as dt
            receipt_number = ProjectReceipt.generate_receipt_number()
            receipt = ProjectReceipt(
                receipt_number=receipt_number,
                header_id=project_id,
                amount=amount,
                currency=project.currency or 'SGD',
                payment_method=payment_method,
                payment_date=dt.strptime(payment_date, '%Y-%m-%d').date() if payment_date else dt.now().date(),
                payer_name=payer_name,
                remarks=remarks,
                status='confirmed',
                extra_info=json.dumps({
                    'distribution_method': 'sequential',
                    'allocations': {str(k): v for k, v in allocations.items()},
                    'total_amount': amount,
                })
            )
            db.session.add(receipt)
            db.session.flush()

            for inv_id, alloc_amount in allocations.items():
                alloc = ReceiptInvoiceAllocation(
                    receipt_id=receipt.id,
                    invoice_id=inv_id,
                    allocated_amount=alloc_amount
                )
                db.session.add(alloc)

            # 更新发票付款状态
            for inv_id in allocations:
                ProjectReceipt.update_invoice_paid_amount(inv_id)

            db.session.commit()
            return jsonify({'success': True, 'message': f'收款 {receipt_number} 创建成功'})

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

    # GET: 获取数据
    unpaid = ProjectReceipt.get_project_unpaid_amount(project_id)
    invoices = ProjectInvoice.query.filter_by(header_id=project_id).filter(
        ProjectInvoice.status.in_(['confirmed', 'partial'])
    ).order_by(ProjectInvoice.invoice_date).all()

    invoice_list = []
    for inv in invoices:
        inv_unpaid = inv.unpaid_amount
        if inv_unpaid > 0:
            invoice_list.append({
                'id': inv.id,
                'number': inv.invoice_number,
                'customer': inv.customer_name or '',
                'amount': float(inv.amount or 0),
                'unpaid': round(inv_unpaid, 2),
            })

    from datetime import date
    return render_template('mobile/create_receipt.html',
                         project=project,
                         unpaid=unpaid,
                         invoices=invoice_list,
                         today=date.today().isoformat())


@mobile_bp.route('/card/<int:user_id>')
def business_card(user_id):
    """手机端电子名片"""
    from App_new.auth.models.auth import AuthUser
    from App_new.business.tour.models.Packagemodels import CompanyInfo, HomeBanner
    import random

    user = AuthUser.query.get_or_404(user_id)
    is_owner = current_user.is_authenticated and current_user.id == user_id
    if not is_owner and (not user.profile or not user.profile.is_public):
        flash('该名片不存在或未公开', 'warning')
        return redirect(url_for('mobile.public_home'))

    company = CompanyInfo.query.first()
    banners = HomeBanner.get_active_banners()
    banner_image = None
    if banners:
        banner = random.choice(banners)
        from flask import url_for as _url_for
        banner_image = _url_for('static', filename=banner.image_path)

    return render_template('staff/business_card.html', user=user, company=company,
                           is_owner=is_owner, banner_image=banner_image)


@mobile_bp.route('/cart/add', methods=['POST'])
@csrf.exempt
@login_required
def cart_add():
    """添加到购物车"""
    from App_new.member.models.cart import CartItem
    from App_new.business.products.models import ProductsUnified
    from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant

    data = request.get_json()
    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    adult_qty = data.get('adult_count', 1)
    child_qty = data.get('child_count', 0)
    visit_date = data.get('visit_date', '')

    product = ProductsUnified.query.get(product_id)
    variant = ProductsTicketVariant.query.get(variant_id)
    if not product or not variant:
        return jsonify({'success': False, 'message': '产品或票种不存在'})

    # 检查是否已在购物车（同产品同票种合并）
    existing = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id, variant_id=variant_id
    ).first()

    if existing:
        existing.adult_qty = adult_qty
        existing.child_qty = child_qty
        if visit_date:
            existing.visit_date = visit_date
        existing.adult_price = variant.adult_selling_price or 0
        existing.child_price = variant.child_selling_price or 0
    else:
        location = product.country or ''
        if product.city:
            location += f' · {product.city}'

        item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            variant_id=variant_id,
            adult_qty=adult_qty,
            child_qty=child_qty,
            adult_price=variant.adult_selling_price or 0,
            child_price=variant.child_selling_price or 0,
            currency=variant.currency or 'SGD',
            visit_date=visit_date,
            properties={
                'product_name': product.product_name,
                'variant_name': variant.variant_name,
                'cover_image': product.cover_image,
                'location': location,
            }
        )
        db.session.add(item)

    db.session.commit()

    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'success': True, 'message': '已加入购物车', 'cart_count': cart_count})


@mobile_bp.route('/cart')
@login_required
def cart():
    """购物车页面"""
    from App_new.member.models.cart import CartItem
    from App_new.business.tour.models.Packagemodels import CompanyInfo

    items = CartItem.query.filter_by(user_id=current_user.id).order_by(CartItem.created_at.desc()).all()
    company_info = CompanyInfo.query.first()

    return render_template('mobile/cart.html', items=items, company=company_info)


@mobile_bp.route('/cart/remove', methods=['POST'])
@csrf.exempt
@login_required
def cart_remove():
    """移除购物车项"""
    from App_new.member.models.cart import CartItem

    data = request.get_json()
    item_id = data.get('item_id')
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item:
        db.session.delete(item)
        db.session.commit()

    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'success': True, 'cart_count': cart_count})


@mobile_bp.route('/cart/checkout', methods=['POST'])
@csrf.exempt
@login_required
def cart_checkout():
    """购物车结算 — 批量创建订单"""
    from App_new.member.models.cart import CartItem
    from App_new.member.models.order import Order
    from datetime import datetime
    import json, random

    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        return jsonify({'success': False, 'message': '购物车为空'})

    data = request.get_json() or {}
    contact_name = data.get('contact_name', '')
    contact_phone = data.get('contact_phone', '')
    contact_email = data.get('contact_email', '')

    if not contact_name or not contact_phone:
        return jsonify({'success': False, 'message': '请填写联系人信息'})

    try:
        from App_new.member.models.order import OrderItem
        for item in items:
            props = item.properties or {}
            adult_total = float(item.adult_price or 0) * (item.adult_qty or 0)
            child_total = float(item.child_price or 0) * (item.child_qty or 0)
            total_amount = adult_total + child_total

            order_number = f"TK{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"

            description = f"景点门票: {props.get('product_name', '')}\n票种: {props.get('variant_name', '')}\n地点: {props.get('location', '')}\n游玩日期: {item.visit_date or '待定'}\n人数: 成人{item.adult_qty}人"
            if item.child_qty > 0:
                description += f", 儿童{item.child_qty}人"

            order = Order(
                order_number=order_number,
                user_id=current_user.id,
                service_type='ticket',
                service_name=props.get('product_name', '景点门票'),
                description=description,
                status='pending',
                currency=item.currency or 'SGD',
                base_price=total_amount,
                total_amount=total_amount,
                customer_name=contact_name,
                customer_email=contact_email,
                customer_phone=contact_phone,
            )
            db.session.add(order)
            db.session.flush()

            # 订单项：结构化数据放到 properties
            order_item = OrderItem(
                order_id=order.id,
                item_name=f"{props.get('product_name', '景点门票')} - {props.get('variant_name', '')}".rstrip(' -'),
                item_description=props.get('location', ''),
                item_type='ticket',
                quantity=(item.adult_qty or 0) + (item.child_qty or 0),
                unit_price=float(item.adult_price or 0),
                total_price=total_amount,
                properties={
                    'product_id': item.product_id,
                    'variant_id': item.variant_id,
                    'variant_name': props.get('variant_name'),
                    'visit_date': item.visit_date,
                    'adult_count': item.adult_qty,
                    'child_count': item.child_qty,
                    'adult_price': float(item.adult_price or 0),
                    'child_price': float(item.child_price or 0),
                }
            )
            db.session.add(order_item)

        # 清空购物车
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        return jsonify({'success': True, 'message': f'成功下单 {len(items)} 个产品'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'结算失败: {str(e)}'})


@mobile_bp.route('/contact')
def contact():
    """手机端联系我们页面"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.auth.models.auth import AuthUser, UserProfile, Role

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 获取公开展示的员工列表
    staff_role = Role.query.filter_by(name='staff').first()
    staff_list = []
    if staff_role:
        # 查询所有设置为公开显示的员工
        public_staff = db.session.query(AuthUser, UserProfile).join(
            UserProfile, AuthUser.id == UserProfile.user_id
        ).filter(
            AuthUser.role_id == staff_role.id,
            AuthUser.is_active == True,
            UserProfile.is_public == True
        ).all()

        for user, profile in public_staff:
            staff_list.append({
                'id': user.id,
                'name': profile.get_full_name() if profile else user.username,
                'position': profile.position if profile else '旅游顾问',
                'phone': profile.phone if profile else None,
                'whatsapp': profile.whatsapp if profile else None,
                'wechat_id': profile.wechat_id if profile else None,
                'wechat_qr': profile.wechat_qr if profile else None,
                'avatar': profile.avatar if profile else None,
                'email': user.email
            })

    # 构建联系信息对象
    if company_info:
        contact_info = {
            'address': company_info.address,
            'phone': company_info.phone,
            'email': company_info.email,
            'wechat': 'MyTravelPanel',
            'business_hours': '周一至周五: 9:00 AM - 6:00 PM'
        }
    else:
        contact_info = {
            'address': '新加坡市中心商业区',
            'phone': '+65 1234 5678',
            'email': 'info@joyesc.com',
            'wechat': 'MyTravelPanel',
            'business_hours': '周一至周五: 9:00 AM - 6:00 PM'
        }

    return render_template('mobile/contact.html',
                         contact=contact_info,
                         staff_list=staff_list,
                         company=company_info)


@mobile_bp.route('/visa-services')
def visa_services():
    """手机端签证服务列表"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 获取筛选参数
    region_filter = request.args.get('region', '')
    search_query = request.args.get('search', '')

    # 地区选项
    region_options = {
        'asia': '亚洲',
        'europe': '欧洲',
        'america': '美洲',
        'oceania': '大洋洲',
        'africa': '非洲'
    }

    # 地区与国家的映射
    region_countries = {
        'asia': ['中国', '日本', '韩国', '泰国', '新加坡', '马来西亚', '越南', '印度', '印度尼西亚', '菲律宾', '柬埔寨', '老挝', '缅甸', '尼泊尔', '斯里兰卡', '土耳其', '阿联酋', '沙特阿拉伯'],
        'europe': ['英国', '法国', '德国', '意大利', '西班牙', '荷兰', '瑞士', '奥地利', '比利时', '瑞典', '挪威', '丹麦', '芬兰', '希腊', '葡萄牙', '爱尔兰', '波兰', '捷克', '匈牙利', '俄罗斯'],
        'america': ['美国', '加拿大', '墨西哥', '巴西', '阿根廷', '智利', '秘鲁', '古巴'],
        'oceania': ['澳大利亚', '新西兰', '斐济'],
        'africa': ['南非', '埃及', '摩洛哥', '肯尼亚', '坦桑尼亚']
    }

    # 查询所有激活的签证类型
    visa_types = VisaTypes.query.filter_by(is_active=True).all()

    # 按国家分组
    country_services = {}
    for visa_type in visa_types:
        if visa_type.country:
            country_name = visa_type.country.country_name_CN
            country_en = visa_type.country.country_name_EN or ''
            flag_file = visa_type.country.flag_file

            if country_name not in country_services:
                country_services[country_name] = {
                    'country': country_name,
                    'country_en': country_en,
                    'flag_file': flag_file,
                    'services': [],
                    'visa_count': 0
                }

            country_services[country_name]['services'].append(visa_type.visa_type)
            country_services[country_name]['visa_count'] += 1

    # 转换为列表
    visa_services_list = list(country_services.values())

    # 按地区筛选
    if region_filter and region_filter in region_countries:
        region_country_list = region_countries[region_filter]
        visa_services_list = [s for s in visa_services_list if s['country'] in region_country_list]

    # 搜索筛选
    if search_query:
        search_lower = search_query.lower()
        visa_services_list = [
            s for s in visa_services_list
            if search_lower in s['country'].lower() or
               search_lower in s['country_en'].lower() or
               any(search_lower in service.lower() for service in s['services'])
        ]

    # 按国家名排序
    visa_services_list.sort(key=lambda x: x['country'])

    return render_template('mobile/visa_services.html',
                         visa_services=visa_services_list,
                         region_filter=region_filter,
                         search_query=search_query,
                         region_options=region_options,
                         company=company_info)


@mobile_bp.route('/visa-services/<country_name>')
def visa_country(country_name):
    """手机端按国家查看签证"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 获取国家信息
    country = VisaCountries.query.filter(
        (VisaCountries.country_name_CN == country_name) |
        (VisaCountries.country_name_EN == country_name)
    ).first()

    if not country:
        flash('未找到该国家', 'error')
        return redirect(url_for('mobile.visa_services'))

    # 获取该国家的签证类型
    visa_types = VisaTypes.query.filter_by(country_id=country.id, is_active=True).order_by(VisaTypes.visa_type).all()

    visa_types_data = []
    for visa_type in visa_types:
        visa_types_data.append({
            'id': visa_type.id,
            'visa_type': visa_type.visa_type,
            'fee': visa_type.fee,
            'processing_time': visa_type.processing_time,
            'validity': getattr(visa_type, 'validity', None)
        })

    country_info = {
        'country': country.country_name_CN,
        'country_en': country.country_name_EN,
        'country_code': country.country_code,
        'visa_types': visa_types_data
    }

    return render_template('mobile/visa_country.html',
                         country_info=country_info,
                         company=company_info)


@mobile_bp.route('/visa-detail/<visa_type_name>')
def visa_detail(visa_type_name):
    """手机端签证详情"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.business.visa.models.Visamodels import VisaTypes
    from urllib.parse import unquote

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # URL解码
    visa_type_name = unquote(visa_type_name)

    # 获取签证类型信息
    visa_type = VisaTypes.query.filter_by(visa_type=visa_type_name, is_active=True).first()

    if not visa_type:
        flash('未找到该签证类型', 'error')
        return redirect(url_for('mobile.visa_services'))

    return render_template('mobile/visa_detail.html',
                         visa_type=visa_type,
                         company=company_info)


@mobile_bp.route('/login', methods=['GET', 'POST'])
def member_login():
    """手机端会员登录"""
    from flask_login import login_user, current_user
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.auth.models.auth import AuthUser

    # 已登录用户跳转
    if current_user.is_authenticated:
        next_url = request.args.get('next')
        if next_url:
            return redirect(next_url)
        return redirect(url_for('mobile.public_home'))

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == '1'

        if not email or not password:
            flash('请填写邮箱和密码', 'error')
            return render_template('mobile/member_login.html', company=company_info)

        # 查找用户
        user = AuthUser.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # 检查用户角色
            if user.role and user.role.name not in ['member', 'admin', 'staff']:
                flash('该账号不是会员账号', 'error')
                return render_template('mobile/member_login.html', company=company_info)

            # 检查用户状态
            if not user.is_active:
                flash('该账号已被禁用，请联系管理员', 'error')
                return render_template('mobile/member_login.html', company=company_info)

            # 登录用户
            login_user(user, remember=remember)
            # 写入会话版本号（load_user 校验需要，缺失会被强制登出）
            from flask import session
            session['session_version'] = user.session_version or 1

            # 跳转到目标页面
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for('mobile.public_home'))
        else:
            flash('邮箱或密码错误', 'error')

    return render_template('mobile/member_login.html', company=company_info)


@mobile_bp.route('/register', methods=['GET', 'POST'])
def member_register():
    """手机端会员注册 - 第一步：发送验证码"""
    from flask import session
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.auth.models.auth import AuthUser
    import re

    # 已登录用户跳转
    if current_user.is_authenticated:
        return redirect(url_for('mobile.public_home'))

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        # 基础验证
        if not email:
            flash('请输入邮箱地址', 'error')
            return render_template('mobile/member_register.html', company=company_info)

        # 邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('请输入有效的邮箱地址', 'error')
            return render_template('mobile/member_register.html', company=company_info)

        # 检查邮箱是否已存在
        existing_user = AuthUser.query.filter_by(email=email).first()
        if existing_user:
            flash('该邮箱已被注册', 'error')
            return render_template('mobile/member_register.html', company=company_info)

        # 生成并发送验证码
        try:
            from App_new.auth.models.auth import EmailVerificationCode
            verification_code_obj, verification_code = EmailVerificationCode.generate_code(email)
            db.session.add(verification_code_obj)
            db.session.commit()

            # 发送验证码邮件
            from App_new.shared.routes.auth import send_verification_code_email
            send_verification_code_email(email, verification_code)

            # 将邮箱存储到session中
            session['registration_email'] = email
            flash('验证码已发送到您的邮箱，请查收', 'success')
            return redirect(url_for('mobile.member_register_verify'))

        except Exception as e:
            current_app.logger.error(f'发送验证码失败: {str(e)}')
            flash(f'发送验证码失败，请稍后重试', 'error')
            return render_template('mobile/member_register.html', company=company_info)

    return render_template('mobile/member_register.html', company=company_info)


@mobile_bp.route('/register/verify', methods=['GET', 'POST'])
def member_register_verify():
    """手机端会员注册 - 第二步：验证码确认和完成注册"""
    from flask import session
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.auth.models.auth import AuthUser, Role, UserProfile

    # 已登录用户跳转
    if current_user.is_authenticated:
        return redirect(url_for('mobile.public_home'))

    # 检查是否有注册邮箱在session中
    if 'registration_email' not in session:
        flash('请先输入邮箱地址', 'error')
        return redirect(url_for('mobile.member_register'))

    email = session['registration_email']

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    if request.method == 'POST':
        verification_code = request.form.get('verification_code', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()

        # 基础验证
        if not all([verification_code, password, confirm_password, first_name]):
            flash('请填写所有必填字段', 'error')
            return render_template('mobile/member_register_verify.html', email=email, company=company_info)

        # 验证验证码
        try:
            from App_new.auth.models.auth import EmailVerificationCode
            is_valid, message = EmailVerificationCode.verify_code(email, verification_code)
            if not is_valid:
                flash(f'验证码{message}，请重新输入', 'error')
                return render_template('mobile/member_register_verify.html', email=email, company=company_info)
        except Exception as e:
            flash(f'验证码验证失败：{str(e)}', 'error')
            return render_template('mobile/member_register_verify.html', email=email, company=company_info)

        # 密码验证
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('mobile/member_register_verify.html', email=email, company=company_info)

        if len(password) < 6:
            flash('密码长度至少6位', 'error')
            return render_template('mobile/member_register_verify.html', email=email, company=company_info)

        # 创建用户账户
        try:
            # 获取会员角色
            member_role = Role.query.filter_by(name='member').first()
            if not member_role:
                flash('系统错误：会员角色不存在', 'error')
                return render_template('mobile/member_register_verify.html', email=email, company=company_info)

            # 创建用户名
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while AuthUser.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1

            # 创建用户
            new_user = AuthUser(
                username=username,
                email=email,
                role_id=member_role.id,
                is_verified=True,
                is_active=True
            )
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            # 创建用户资料
            user_profile = UserProfile(
                user_id=new_user.id,
                first_name=first_name,
                last_name=last_name,
                phone=phone
            )
            db.session.add(user_profile)
            db.session.commit()

            # 清除session中的注册邮箱
            session.pop('registration_email', None)

            flash('注册成功！您的账户已激活，现在可以登录了。', 'success')
            return redirect(url_for('mobile.member_login'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'注册失败: {str(e)}')
            flash(f'注册失败：{str(e)}', 'error')
            return render_template('mobile/member_register_verify.html', email=email, company=company_info)

    return render_template('mobile/member_register_verify.html', email=email, company=company_info)


@mobile_bp.route('/register/resend-code', methods=['POST'])
def resend_verification_code():
    """手机端重新发送验证码"""
    from flask import session

    # 检查是否有注册邮箱在session中
    if 'registration_email' not in session:
        flash('请先输入邮箱地址', 'error')
        return redirect(url_for('mobile.member_register'))

    email = session['registration_email']

    try:
        from App_new.auth.models.auth import EmailVerificationCode
        verification_code_obj, verification_code = EmailVerificationCode.generate_code(email)
        db.session.add(verification_code_obj)
        db.session.commit()

        # 发送验证码邮件
        from App_new.shared.routes.auth import send_verification_code_email
        if send_verification_code_email(email, verification_code):
            flash('验证码已重新发送，请查收邮箱', 'success')
        else:
            flash('验证码发送失败，请稍后重试', 'error')

        return redirect(url_for('mobile.member_register_verify'))

    except Exception as e:
        current_app.logger.error(f'重新发送验证码失败: {str(e)}')
        flash(f'重新发送验证码失败：{str(e)}', 'error')
        return redirect(url_for('mobile.member_register_verify'))


# ==================== 会员中心页面 ====================

@mobile_bp.route('/member')
@login_required
def member_profile():
    """手机端会员中心"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.member.models.order import Order

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 获取订单统计
    order_stats = {
        'total': Order.query.filter_by(user_id=current_user.id).count(),
        'pending': Order.query.filter_by(user_id=current_user.id, status='pending').count(),
        'confirmed': Order.query.filter_by(user_id=current_user.id, status='confirmed').count(),
        'completed': Order.query.filter_by(user_id=current_user.id, status='completed').count()
    }

    return render_template('mobile/member_profile.html',
                         order_stats=order_stats,
                         company=company_info)


@mobile_bp.route('/member/logout', methods=['POST'])
@login_required
def member_logout():
    """手机端会员退出登录"""
    from flask_login import logout_user
    logout_user()
    flash('已退出登录', 'success')
    return redirect(url_for('mobile.public_home'))


@mobile_bp.route('/orders')
@login_required
def orders_list():
    """手机端订单列表"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.member.models.order import Order

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 获取筛选参数
    status = request.args.get('status', '')
    service_type = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # 查询当前用户的订单
    query = Order.query.filter_by(user_id=current_user.id)

    if status:
        query = query.filter_by(status=status)
    if service_type:
        query = query.filter_by(service_type=service_type)

    # 按创建时间倒序排列
    query = query.order_by(Order.created_at.desc())

    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    orders = pagination.items

    return render_template('mobile/member_orders.html',
                         orders=orders,
                         pagination=pagination,
                         current_status=status,
                         current_type=service_type,
                         company=company_info)


@mobile_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """手机端订单详情"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    from App_new.member.models.order import Order

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 查询订单
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    return render_template('mobile/order_detail.html',
                         order=order,
                         company=company_info)


@mobile_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@csrf.exempt
@login_required
def cancel_order(order_id):
    """手机端取消订单"""
    from App_new.member.models.order import Order

    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    if not order:
        return jsonify({'success': False, 'message': '订单不存在'})

    if order.status not in ('draft', 'pending'):
        return jsonify({'success': False, 'message': '当前状态不可取消'})

    order.status = 'cancelled'
    order.cancelled_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': '订单已取消'})


@mobile_bp.route('/order/<int:order_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
def delete_order(order_id):
    """手机端删除已取消的订单"""
    from App_new.member.models.order import Order

    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    if not order:
        return jsonify({'success': False, 'message': '订单不存在'})

    if order.status != 'cancelled':
        return jsonify({'success': False, 'message': '只能删除已取消的订单'})

    db.session.delete(order)
    db.session.commit()

    return jsonify({'success': True, 'message': '订单已删除'})


@mobile_bp.route('/book-tour/<int:product_id>', methods=['GET', 'POST'])
@login_required
def book_tour(product_id):
    """手机端旅游预订"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo, Product
    from App_new.member.models.order import Order, OrderItem, OrderStatus
    from datetime import date, datetime
    import json

    # 获取公司信息
    company_info = CompanyInfo.query.first()

    # 获取产品信息
    product = Product.query.get_or_404(product_id)

    # 检查产品是否可预订
    today = date.today()
    if product.product_status != 'active':
        flash('该产品目前不可预订', 'error')
        return redirect(url_for('mobile.tour_package_detail', package_id=product_id))

    if product.valid_until and product.valid_until < today:
        flash('该产品已过期', 'error')
        return redirect(url_for('mobile.tour_package_detail', package_id=product_id))

    if request.method == 'POST':
        try:
            # 获取表单数据
            travel_date = request.form.get('travel_date')
            adult_count = int(request.form.get('adult_count', 1))
            child_count = int(request.form.get('child_count', 0))
            infant_count = int(request.form.get('infant_count', 0))

            # 联系人信息
            contact_name = request.form.get('contact_name')
            contact_email = request.form.get('contact_email')
            contact_phone = request.form.get('contact_phone')
            special_requirements = request.form.get('special_requirements', '')

            # 验证数据
            if not travel_date:
                flash('请选择出发日期', 'error')
                return redirect(url_for('mobile.book_tour', product_id=product_id))

            if not contact_name or not contact_email or not contact_phone:
                flash('请填写完整的联系人信息', 'error')
                return redirect(url_for('mobile.book_tour', product_id=product_id))

            # 计算价格
            base_price = float(product.base_price or 0)
            child_price = float(product.child_price or (base_price * 0.7))
            infant_price = float(product.infant_price or 0)

            adult_total = adult_count * base_price
            child_total = child_count * child_price
            infant_total = infant_count * infant_price
            total_amount = adult_total + child_total + infant_total

            # 生成订单号
            import random
            order_number = f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"

            # 构建订单描述
            destination = product.city_name or product.destination_city or '未指定'
            duration = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "待定"

            description = f"""旅游产品: {product.product_name}
产品编号: {product.product_code or f'PKG-{product.id:04d}'}
目的地: {destination}
行程: {duration}
出发日期: {travel_date}
人数: 成人{adult_count}人"""
            if child_count > 0:
                description += f", 儿童{child_count}人"
            if infant_count > 0:
                description += f", 婴儿{infant_count}人"

            # 创建订单
            order = Order(
                order_number=order_number,
                user_id=current_user.id,
                service_type='tour',
                service_name=product.product_name,
                description=description,
                status='pending',
                currency=product.currency or 'SGD',
                base_price=total_amount,
                total_amount=total_amount,
                customer_name=contact_name,
                customer_email=contact_email,
                customer_phone=contact_phone,
                special_requirements=special_requirements,
            )

            db.session.add(order)
            db.session.flush()

            # 订单项：结构化数据放到 properties（与桌面端保持一致）
            from App_new.member.models.order import OrderItem
            order_item = OrderItem(
                order_id=order.id,
                item_name=product.product_name,
                item_description=f"{destination} | {duration}",
                item_type='tour_package',
                quantity=adult_count + child_count + infant_count,
                unit_price=base_price,
                total_price=total_amount,
                properties={
                    'product_id': product_id,
                    'product_code': product.product_code,
                    'travel_date': travel_date,
                    'adult_count': adult_count,
                    'child_count': child_count,
                    'infant_count': infant_count,
                    'adult_price': base_price,
                    'child_price': child_price,
                    'infant_price': infant_price,
                }
            )
            db.session.add(order_item)
            db.session.commit()

            flash('预订提交成功！我们将尽快与您联系确认', 'success')
            return redirect(url_for('mobile.orders_list'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'预订失败: {str(e)}')
            import traceback
            current_app.logger.error(traceback.format_exc())
            flash(f'预订失败: {str(e)}', 'error')
            return redirect(url_for('mobile.book_tour', product_id=product_id))

    # GET 请求：显示预订表单
    # 准备产品数据
    destination = product.city_name or product.destination_city or '未指定'
    if product.country and product.country != '未知':
        destination = f"{product.country} {destination}"

    duration = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "待定"
    price_display = f"{product.currency or 'SGD'} {product.base_price:,.0f}" if product.base_price else "价格面议"

    product_data = {
        'id': product.id,
        'code': product.product_code or f'PKG-{product.id:04d}',
        'name': product.product_name,
        'destination': destination,
        'duration': duration,
        'price': price_display,
        'currency': product.currency or 'SGD',
        'base_price': product.base_price or 0,
        'child_price': product.child_price,
        'infant_price': product.infant_price or 0,
        'min_pax': product.min_pax,
        'max_pax': product.max_pax,
        'image': product.cover_image
    }

    # 获取用户信息
    user_profile = current_user.profile if hasattr(current_user, 'profile') else None

    return render_template('mobile/book_tour.html',
                         product=product_data,
                         user_profile=user_profile,
                         company=company_info)
