from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from App.models.projects.BookingProject import db, ProjectHeader, ProjectRef, ProjectEO, ProjectFlightPassenger, ProjectFlightSegment, CustomerCompany, ProjectReceipt
from App.exts import csrf
from App.models.Product.Suppliers import Supplier
from App.models.Product.BusinessType import BusinessType
from App.forms.header_forms import ProjectHeaderForm
from App.forms.ref_forms import ProjectRefForm
from App.forms.eo_forms import ProjectEOForm
from App.forms.receipt_forms import ProjectReceiptForm, ProjectLevelReceiptForm
from datetime import datetime
from sqlalchemy import func
import traceback  # 添加traceback模块
import json # 添加json模块

projects = Blueprint('projects', __name__)

@projects.route('/header/create', methods=['GET', 'POST'])
def create_header():
    form = ProjectHeaderForm()
    
    if form.validate_on_submit():
        try:
            hid = ProjectHeader.generate_hid()
            
            # 处理公司信息
            company_id = None
            
            if form.company_id.data and form.company_id.data != 0:
                company_id = form.company_id.data
            
            header = ProjectHeader(
                hid=hid,
                desc=form.desc.data,
                company_id=company_id,
                limit=form.limit.data,
                contact=form.contact.data,
                dept=form.dept.data,
                staff_id=form.staff_id.data if form.staff_id.data else None,
                staff_name=form.staff_name.data,
                leader_name=form.leader_name.data,
                currency=form.currency.data,
                type=form.type.data,
                source=form.source.data,
                country=form.country.data,
                status=form.status.data,
                remarks=form.remarks.data
            )
            db.session.add(header)
            db.session.commit()
            flash('项目主表创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充项目编号
    hid = ProjectHeader.generate_hid()
    form.hid.data = hid
    
    return render_template('projects/BookingProject/create_header.html', form=form, hid=hid)

@projects.route('/header/<int:header_id>')
def header_detail(header_id):
    # 使用joinedload预加载refs和相关数据
    from sqlalchemy.orm import joinedload
    
    header = ProjectHeader.query.options(
        joinedload(ProjectHeader.refs).joinedload(ProjectRef.ref_type),
        joinedload(ProjectHeader.refs).joinedload(ProjectRef.supplier)
    ).get_or_404(header_id)
    
    # 获取上一个和下一个项目
    prev_header = ProjectHeader.query.filter(
        ProjectHeader.id < header_id
    ).order_by(ProjectHeader.id.desc()).first()
    
    next_header = ProjectHeader.query.filter(
        ProjectHeader.id > header_id
    ).order_by(ProjectHeader.id.asc()).first()
    
    # 获取公司信息（通过backref自动关联）
    company = header.company
    
    # 获取所有活跃的公司列表供选择
    companies = CustomerCompany.query.filter_by(status='active').order_by(CustomerCompany.company_name).all()
    
    # 财务统计通过属性自动计算，无需手动赋值
    # header.total_selling_amount, header.total_cost_amount, header.total_profit 等属性会自动计算
    # header.payment_status_summary 属性也会自动计算付款状态统计
    
    return render_template('projects/BookingProject/header_detail.html', 
                         header=header, 
                         company=company,
                         companies=companies,
                         prev_header=prev_header, 
                         next_header=next_header)

@projects.route('/ref/create/<int:header_id>', methods=['GET', 'POST'])
def create_ref(header_id):
    header = ProjectHeader.query.get_or_404(header_id)
    form = ProjectRefForm()
    form.header_id.data = header_id
    
    if form.validate_on_submit():
        try:
            ref_number = ProjectRef.generate_ref_number("")  # 不再需要传递project_hid
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=form.name.data,
                ref_type_id=form.ref_type_id.data,
                description=form.description.data,
                supplier_id=form.supplier_id.data if form.supplier_id.data and form.supplier_id.data != 0 else None,
                supplier_contact=form.supplier_contact.data,
                supplier_phone=form.supplier_phone.data,
                selling_price=form.selling_price.data,
                cost_price=form.cost_price.data,
                currency=form.currency.data,
                expected_delivery_date=form.expected_delivery_date.data,
                actual_delivery_date=form.actual_delivery_date.data,
                remarks=form.remarks.data,
                status=form.status.data,
                payment_status=form.payment_status.data
            )
            db.session.add(ref)
            db.session.commit()
            flash('REF明细创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充REF编号
    ref_number = ProjectRef.generate_ref_number("")  # 不再需要传递project_hid
    form.ref_number.data = ref_number
    
    # 获取业务类型和供应商数据
    business_types = BusinessType.query.all()
    suppliers = Supplier.query.all()
    
    return render_template('projects/BookingProject/create_ref.html',
                           form=form, 
                           header=header, 
                           ref_number=ref_number,
                         business_types=business_types,
                         suppliers=suppliers)

@projects.route('/ref/<int:ref_id>')
def ref_detail(ref_id):
    """REF详情页面 - 根据业务类型路由到不同详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 根据业务类型路由到不同的详情页面
    if ref.ref_type and ref.ref_type.name == '机票':
        return redirect(url_for('projects.flight_ref_detail', ref_id=ref.id))
    elif ref.ref_type and ref.ref_type.name == '酒店':
        return redirect(url_for('projects.hotel_ref_detail', ref_id=ref.id))
    elif ref.ref_type and ref.ref_type.name == '签证':
        return redirect(url_for('projects.visa_ref_detail', ref_id=ref.id))
    elif ref.ref_type and ref.ref_type.name == '旅游团':
        return redirect(url_for('projects.tour_ref_detail', ref_id=ref.id))
    elif ref.ref_type and ref.ref_type.name == '保险':
        return redirect(url_for('projects.insurance_ref_detail', ref_id=ref.id))
    elif ref.ref_type and ref.ref_type.name == '交通':
        return redirect(url_for('projects.transport_ref_detail', ref_id=ref.id))
    else:
        # 其他类型或未分类的REF使用通用详情页面
        return render_template('projects/BookingProject/ref_detail.html', ref=ref)

@projects.route('/flight-ref/create/<int:header_id>')
def create_flight_ref(header_id):
    """创建机票REF页面"""
    header = ProjectHeader.query.get_or_404(header_id)
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
    
    return render_template('projects/BookingProject/create_flight_ref.html', 
                         header_id=header_id,
                         suppliers=suppliers,
                         supplier_types=supplier_types)

@projects.route('/flight-ref/submit', methods=['POST'])
@csrf.exempt
def submit_flight_ref():
    """提交机票REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')
        
        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            # 更新REF基本信息
            ref.name = request.form.get('name', '机票订单')
            ref.description = request.form.get('description', '机票订单')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.leader_name = request.form.get('leader_name', '')
            ref.contact_name = request.form.get('contact_name')
            ref.contact_phone = request.form.get('contact_phone')
            ref.contact_email = request.form.get('contact_email')
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'draft')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")  # 不再需要传递project_hid
            
            # 获取机票业务类型ID
            flight_business_type = BusinessType.query.filter_by(name='机票').first()
            if not flight_business_type:
                flash('未找到机票业务类型，请先创建', 'error')
                return redirect(url_for('projects.header_detail', header_id=header_id))
            
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '机票订单'),
                ref_type_id=flight_business_type.id,
                description=request.form.get('description', '机票订单'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None,
                leader_name=request.form.get('leader_name', ''),
                contact_name=request.form.get('contact_name'),
                contact_phone=request.form.get('contact_phone'),
                contact_email=request.form.get('contact_email'),
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'draft'),
                payment_status=request.form.get('payment_status', 'unpaid')
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id
        
        # 保存乘客信息
        passenger_names = request.form.getlist('passenger_name[]')
        passenger_types = request.form.getlist('passenger_type[]')
        selling_prices = request.form.getlist('selling_price[]')
        cost_prices = request.form.getlist('cost_price[]')
        ticket_numbers = request.form.getlist('ticket_number[]')
        pnrs = request.form.getlist('pnr[]')
        
        # 删除现有乘客
        ProjectFlightPassenger.query.filter_by(ref_id=ref.id).delete()
        
        # 安全处理乘客信息 - 确保所有字段长度一致
        max_passenger_len = max(len(passenger_names), len(passenger_types), len(selling_prices), 
                               len(cost_prices), len(ticket_numbers), len(pnrs))
        
        # 扩展较短的列表
        passenger_types.extend(['adult'] * (max_passenger_len - len(passenger_types)))
        selling_prices.extend([''] * (max_passenger_len - len(selling_prices)))
        cost_prices.extend([''] * (max_passenger_len - len(cost_prices)))
        ticket_numbers.extend([''] * (max_passenger_len - len(ticket_numbers)))
        pnrs.extend([''] * (max_passenger_len - len(pnrs)))
        
        # 添加新乘客并计算总价
        total_selling_price = 0
        total_cost_price = 0
        
        for i in range(len(passenger_names)):
            if passenger_names[i]:  # 确保乘客姓名不为空
                # 解析价格
                selling_price = float(selling_prices[i]) if i < len(selling_prices) and selling_prices[i] else 0
                cost_price = float(cost_prices[i]) if i < len(cost_prices) and cost_prices[i] else 0
                
                # 累加总价
                total_selling_price += selling_price
                total_cost_price += cost_price
                
                passenger = ProjectFlightPassenger(
                    ref_id=ref.id,
                    name=passenger_names[i],
                    passenger_type=passenger_types[i] if i < len(passenger_types) else 'adult',
                    selling_price=selling_price if selling_price > 0 else None,
                    cost_price=cost_price if cost_price > 0 else None,
                    ticket_number=ticket_numbers[i] if i < len(ticket_numbers) and ticket_numbers[i] else None,
                    pnr=pnrs[i] if i < len(pnrs) and pnrs[i] else None
                )
                db.session.add(passenger)
        
        # 更新REF级别的总价格
        ref.selling_price = total_selling_price if total_selling_price > 0 else None
        ref.cost_price = total_cost_price if total_cost_price > 0 else None
        
        # 保存航段信息
        flight_numbers = request.form.getlist('flight_number[]')
        cabin_codes = request.form.getlist('cabin_code[]')
        departure_airports = request.form.getlist('departure_airport[]')
        arrival_airports = request.form.getlist('arrival_airport[]')
        departure_dates = request.form.getlist('departure_date[]')
        departure_times = request.form.getlist('departure_time[]')
        arrival_dates = request.form.getlist('arrival_date[]')
        arrival_times = request.form.getlist('arrival_time[]')
        
        # 删除现有航段
        ProjectFlightSegment.query.filter_by(ref_id=ref.id).delete()
        
        # 安全处理航段信息 - 确保所有字段长度一致
        max_segment_len = max(len(flight_numbers), len(cabin_codes), len(departure_airports),
                             len(arrival_airports), len(departure_dates), len(departure_times),
                             len(arrival_dates), len(arrival_times))
        
        # 扩展较短的列表
        cabin_codes.extend([''] * (max_segment_len - len(cabin_codes)))
        departure_airports.extend([''] * (max_segment_len - len(departure_airports)))
        arrival_airports.extend([''] * (max_segment_len - len(arrival_airports)))
        departure_dates.extend([''] * (max_segment_len - len(departure_dates)))
        departure_times.extend([''] * (max_segment_len - len(departure_times)))
        arrival_dates.extend([''] * (max_segment_len - len(arrival_dates)))
        arrival_times.extend([''] * (max_segment_len - len(arrival_times)))
        
        # 添加新航段
        for i in range(len(flight_numbers)):
            # 允许保存空航段，不强制要求航班号不为空
            try:
                # 安全获取日期和时间，提供默认值
                dep_date = departure_dates[i] if i < len(departure_dates) and departure_dates[i] else datetime.now().strftime('%Y-%m-%d')
                dep_time = departure_times[i] if i < len(departure_times) and departure_times[i] else '00:00'
                arr_date = arrival_dates[i] if i < len(arrival_dates) and arrival_dates[i] else dep_date
                arr_time = arrival_times[i] if i < len(arrival_times) and arrival_times[i] else '00:00'
                
                # 合并日期和时间
                dep_datetime = datetime.strptime(f"{dep_date} {dep_time}", '%Y-%m-%d %H:%M')
                arr_datetime = datetime.strptime(f"{arr_date} {arr_time}", '%Y-%m-%d %H:%M')
                
                segment = ProjectFlightSegment(
                    ref_id=ref.id,
                    flight_number=flight_numbers[i] if i < len(flight_numbers) and flight_numbers[i] else '',
                    departure_airport=departure_airports[i] if i < len(departure_airports) else '',
                    arrival_airport=arrival_airports[i] if i < len(arrival_airports) else '',
                    departure_time=dep_datetime,
                    arrival_time=arr_datetime,
                    cabin_class=cabin_codes[i] if i < len(cabin_codes) else '',
                    cabin_code=cabin_codes[i] if i < len(cabin_codes) else '',
                    status='pending'
                )
                db.session.add(segment)
            except (ValueError, IndexError) as e:
                # 记录错误但继续处理其他航段
                continue
        
        db.session.commit()
        flash('机票REF保存成功！', 'success')
        return redirect(url_for('projects.header_detail', header_id=header_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('projects.header_detail', header_id=header_id))

@projects.route('/flight-ref/edit/<int:ref_id>')
def edit_flight_ref(ref_id):
    """编辑机票REF页面"""
    from sqlalchemy.orm import joinedload
    
    # 预加载乘客和航段数据
    ref = ProjectRef.query.options(
        joinedload(ProjectRef.flight_passengers),
        joinedload(ProjectRef.flight_segments)
    ).get_or_404(ref_id)
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
    
    return render_template('projects/BookingProject/create_flight_ref.html', 
                         header_id=ref.header_id,
                         ref_id=ref.id,
                         ref=ref,
                         suppliers=suppliers,
                         supplier_types=supplier_types)

@projects.route('/flight-ref/detail/<int:ref_id>')
def flight_ref_detail(ref_id):
    """机票REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 获取同一个header下的上一个和下一个REF
    prev_ref = ProjectRef.query.filter(
        ProjectRef.header_id == ref.header_id,
        ProjectRef.id < ref_id
    ).order_by(ProjectRef.id.desc()).first()
    
    next_ref = ProjectRef.query.filter(
        ProjectRef.header_id == ref.header_id,
        ProjectRef.id > ref_id
    ).order_by(ProjectRef.id.asc()).first()
    
    return render_template('projects/BookingProject/flight_ref_detail.html', 
                         ref=ref, 
                         prev_ref=prev_ref, 
                         next_ref=next_ref)

@projects.route('/hotel-ref/detail/<int:ref_id>')
def hotel_ref_detail(ref_id):
    """酒店REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    return render_template('projects/BookingProject/hotel_ref_detail.html', ref=ref)

@projects.route('/visa-ref/detail/<int:ref_id>')
def visa_ref_detail(ref_id):
    """签证REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 解析签证专属信息
    visa_info = {}
    if ref.extra_info:
        try:
            visa_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            visa_info = {}
    
    return render_template('projects/BookingProject/visa_ref_detail.html', 
                         ref=ref, 
                         visa_info=visa_info)

@projects.route('/tour-ref/detail/<int:ref_id>')
def tour_ref_detail(ref_id):
    """旅游团REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    return render_template('projects/BookingProject/tour_ref_detail.html', ref=ref)

@projects.route('/insurance-ref/detail/<int:ref_id>')
def insurance_ref_detail(ref_id):
    """保险REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    return render_template('projects/BookingProject/insurance_ref_detail.html', ref=ref)

@projects.route('/transport-ref/detail/<int:ref_id>')
def transport_ref_detail(ref_id):
    """交通REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    return render_template('projects/BookingProject/transport_ref_detail.html', ref=ref)

@projects.route('/eo/create/<int:ref_id>', methods=['GET', 'POST'])
def create_eo(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
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
            return redirect(url_for('projects.ref_detail', ref_id=ref.id))
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
    
    return render_template('projects/BookingProject/create_eo.html',
                           form=form, ref=ref, eo_number=eo_number)

@projects.route('/')
def list_projects():
    # 获取筛选参数
    status = request.args.get('status')
    search = request.args.get('search')
    company = request.args.get('company')
    leader = request.args.get('leader')
    contact = request.args.get('contact')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    selling_min = request.args.get('selling_min')
    selling_max = request.args.get('selling_max')
    profit_min = request.args.get('profit_min')
    profit_max = request.args.get('profit_max')
    balance_min = request.args.get('balance_min')
    balance_max = request.args.get('balance_max')
    sort_by = request.args.get('sort_by', 'created_at_desc')
    
    query = ProjectHeader.query

    # 基础筛选
    if status:
        query = query.filter(ProjectHeader.status == status)
    
    if search:
        query = query.filter(
            db.or_(
                ProjectHeader.hid.contains(search),
                ProjectHeader.desc.contains(search)
            )
        )
    
    if company:
        query = query.filter(ProjectHeader.company_name.contains(company))
    
    if leader:
        query = query.filter(ProjectHeader.leader_name.contains(leader))
    
    if contact:
        query = query.filter(ProjectHeader.contact.contains(contact))
    
    if date_from:
        query = query.filter(ProjectHeader.created_at >= date_from)
    
    if date_to:
        query = query.filter(ProjectHeader.created_at <= date_to + ' 23:59:59')
    
    # 排序
    if sort_by == 'created_at_desc':
        query = query.order_by(ProjectHeader.created_at.desc())
    elif sort_by == 'created_at_asc':
        query = query.order_by(ProjectHeader.created_at.asc())
    elif sort_by == 'updated_at_desc':
        query = query.order_by(ProjectHeader.updated_at.desc())
    elif sort_by == 'updated_at_asc':
        query = query.order_by(ProjectHeader.updated_at.asc())
    else:
        # 默认按创建时间倒序
        query = query.order_by(ProjectHeader.created_at.desc())
    
    projects = query.all()
    
    # 用字典保存每个项目的财务数据
    project_stats = {}
    for project in projects:
        refs = ProjectRef.query.filter_by(header_id=project.id).all()
        total_selling_price = sum([float(ref.selling_price or 0) for ref in refs])
        total_cost_price = sum([float(ref.cost_price or 0) for ref in refs])
        total_profit = total_selling_price - total_cost_price
        
        # 使用模型中的正确方法计算已付款金额
        total_paid_amount = project.total_paid_amount
        balance = project.total_unpaid_amount  # 使用模型中的未付款金额
        
        project_stats[project.id] = {
            'total_selling_price': total_selling_price,
            'total_cost_price': total_cost_price,
            'total_profit': total_profit,
            'total_paid_amount': total_paid_amount,
            'balance': balance
        }
    
    # 财务金额筛选（在内存中筛选）
    filtered_projects = []
    for project in projects:
        stats = project_stats[project.id]
        
        # 总售价范围筛选
        if selling_min and stats['total_selling_price'] < float(selling_min):
            continue
        if selling_max and stats['total_selling_price'] > float(selling_max):
            continue
        
        # 总利润范围筛选
        if profit_min and stats['total_profit'] < float(profit_min):
            continue
        if profit_max and stats['total_profit'] > float(profit_max):
            continue
        
        # Balance范围筛选
        if balance_min and stats['balance'] < float(balance_min):
            continue
        if balance_max and stats['balance'] > float(balance_max):
            continue
        
        filtered_projects.append(project)
    
    # 按财务数据排序（在内存中排序）
    if sort_by in ['selling_price_desc', 'selling_price_asc', 'profit_desc', 'profit_asc', 'balance_desc', 'balance_asc']:
        reverse = sort_by.endswith('_desc')
        if 'selling_price' in sort_by:
            filtered_projects.sort(
                key=lambda p: project_stats[p.id]['total_selling_price'],
                reverse=reverse
            )
        elif 'profit' in sort_by:
            filtered_projects.sort(
                key=lambda p: project_stats[p.id]['total_profit'],
                reverse=reverse
            )
        elif 'balance' in sort_by:
            filtered_projects.sort(
                key=lambda p: project_stats[p.id]['balance'],
                reverse=reverse
            )
    
    # 更新project_stats只包含筛选后的项目
    filtered_stats = {p.id: project_stats[p.id] for p in filtered_projects}
    
    # 分页处理
    page = request.args.get('page', 1, type=int)
    per_page = 30  # 每页显示30条数据
    
    # 计算总页数
    total_count = len(filtered_projects)
    total_pages = max(1, (total_count + per_page - 1) // per_page)  # 确保至少有1页
    
    # 确保页码在有效范围内
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
    
    # 计算当前页的数据范围
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    
    # 获取当前页的数据
    paginated_projects = filtered_projects[start_index:end_index]
    
    # 创建分页对象
    class Pagination:
        def __init__(self, page, per_page, total_count):
            self.page = page
            self.per_page = per_page
            self.total_count = total_count
            self.pages = total_pages
            self.has_prev = page > 1
            self.has_next = page < total_pages
            self.prev_num = page - 1 if page > 1 else None
            self.next_num = page + 1 if page < total_pages else None
            self.iter_pages = lambda: range(1, total_pages + 1)
    
    pagination = Pagination(page, per_page, total_count)
    
    # 更新project_stats只包含当前页的项目
    paginated_stats = {p.id: filtered_stats[p.id] for p in paginated_projects}
    
    # 计算总体统计信息（基于筛选后的所有数据）
    total_projects_count = len(filtered_projects)
    active_projects_count = len([p for p in filtered_projects if p.status == 'active'])
    completed_projects_count = len([p for p in filtered_projects if p.status == 'completed'])
    draft_projects_count = len([p for p in filtered_projects if p.status == 'draft'])
    
    # 计算总体财务统计
    total_selling_sum = sum(stats['total_selling_price'] for stats in filtered_stats.values())
    total_cost_sum = sum(stats['total_cost_price'] for stats in filtered_stats.values())
    total_profit_sum = sum(stats['total_profit'] for stats in filtered_stats.values())
    total_balance_sum = sum(stats['balance'] for stats in filtered_stats.values())
    total_paid_sum = sum(stats['total_paid_amount'] for stats in filtered_stats.values())
    
    return render_template(
        'projects/BookingProject/list_projects.html',
        projects=paginated_projects,
        project_stats=paginated_stats,
        pagination=pagination,
        total_projects_count=total_projects_count,
        active_projects_count=active_projects_count,
        completed_projects_count=completed_projects_count,
        draft_projects_count=draft_projects_count,
        total_selling_sum=total_selling_sum,
        total_cost_sum=total_cost_sum,
        total_profit_sum=total_profit_sum,
        total_balance_sum=total_balance_sum,
        total_paid_sum=total_paid_sum
    )

@projects.route('/statistics')
def project_statistics():
    # 获取项目总数
    total_projects = ProjectHeader.query.count()
    
    # 按状态统计项目数量
    status_stats = db.session.query(
        ProjectHeader.status,
        func.count(ProjectHeader.id)
    ).group_by(ProjectHeader.status).all()
    
    # 按月统计项目数量（最近12个月）
    monthly_stats = db.session.query(
        func.date_format(ProjectHeader.created_at, '%Y-%m'),
        func.count(ProjectHeader.id)
    ).group_by(
        func.date_format(ProjectHeader.created_at, '%Y-%m')
    ).order_by(
        func.date_format(ProjectHeader.created_at, '%Y-%m').desc()
    ).limit(12).all()
    
    # 统计REF类型分布
    ref_type_stats = db.session.query(
        BusinessType.name,
        func.count(ProjectRef.id)
    ).join(ProjectRef.ref_type).group_by(BusinessType.name).all()
    
    # 统计供应商类型分布
    supplier_type_stats = db.session.query(
        ProjectEO.supplier_type,
        func.count(ProjectEO.id)
    ).group_by(ProjectEO.supplier_type).all()
    
    return render_template('projects/statistics.html',
                         total_projects=total_projects,
                         status_stats=status_stats,
                         monthly_stats=monthly_stats,
                         ref_type_stats=ref_type_stats,
                         supplier_type_stats=supplier_type_stats)

@projects.route('/header/<int:header_id>/edit', methods=['GET', 'POST'])
def edit_header(header_id):
    header = ProjectHeader.query.get_or_404(header_id)
    form = ProjectHeaderForm(obj=header)
    
    if form.validate_on_submit():
        try:
            # 处理company_id字段，将0转换为None
            if form.company_id.data == 0:
                header.company_id = None
            else:
                header.company_id = form.company_id.data
            
            # 更新其他字段
            header.hid = form.hid.data
            header.desc = form.desc.data
            header.limit = form.limit.data
            header.contact = form.contact.data
            header.dept = form.dept.data
            header.staff_id = form.staff_id.data if form.staff_id.data else None
            header.staff_name = form.staff_name.data
            header.leader_name = form.leader_name.data
            header.currency = form.currency.data
            header.type = form.type.data
            header.source = form.source.data
            header.country = form.country.data
            header.status = form.status.data
            header.remarks = form.remarks.data
            
            db.session.commit()
            flash('项目主表更新成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('projects/BookingProject/edit_header.html', form=form, header=header)

@projects.route('/ref/<int:ref_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 如果是其他类型的REF，重定向到专门的编辑路由
    if ref.ref_type and ref.ref_type.name == '其他':
        return redirect(url_for('projects.edit_other_ref', ref_id=ref_id))
    
    # 如果是签证类型的REF，重定向到专门的编辑路由
    if ref.ref_type and ref.ref_type.name == '签证':
        return redirect(url_for('projects.edit_visa_ref', ref_id=ref_id))
    
    # 如果是保险类型的REF，重定向到专门的编辑路由
    if ref.ref_type and ref.ref_type.name == '保险':
        return redirect(url_for('projects.edit_insurance_ref', ref_id=ref_id))
    
    # 如果是旅游团类型的REF，重定向到专门的编辑路由
    if ref.ref_type and ref.ref_type.name == '旅游团':
        return redirect(url_for('projects.edit_tour_ref', ref_id=ref_id))
    
    form = ProjectRefForm(obj=ref)
    
    # 解析酒店专属信息（如果是酒店类型）
    hotel_info = None
    if ref.ref_type and ref.ref_type.name == '酒店':
        if ref.extra_info:
            try:
                hotel_info = json.loads(ref.extra_info)
                # 确保guest_info字段存在（从remarks字段映射）
                if 'remarks' in hotel_info and 'guest_info' not in hotel_info:
                    hotel_info['guest_info'] = hotel_info['remarks']
            except (json.JSONDecodeError, TypeError) as e:
                # 如果extra_info不是有效的JSON，尝试从remarks中解析
                hotel_info = {}
                if ref.remarks:
                    # 简单的解析逻辑，从remarks中提取信息
                    lines = ref.remarks.split('\n')
                    for line in lines:
                        if '酒店名称:' in line:
                            hotel_info['hotel_name'] = line.split('酒店名称:')[1].strip()
                        elif '入住日期:' in line:
                            hotel_info['checkin_date'] = line.split('入住日期:')[1].strip()
                        elif '退房日期:' in line:
                            hotel_info['checkout_date'] = line.split('退房日期:')[1].strip()
                        elif '房型:' in line:
                            hotel_info['room_type'] = line.split('房型:')[1].strip()
                        elif '客人信息:' in line:
                            hotel_info['guest_info'] = line.split('客人信息:')[1].strip()
        else:
            hotel_info = {}
            if ref.remarks:
                # 简单的解析逻辑，从remarks中提取信息
                lines = ref.remarks.split('\n')
                for line in lines:
                    if '酒店名称:' in line:
                        hotel_info['hotel_name'] = line.split('酒店名称:')[1].strip()
                    elif '入住日期:' in line:
                        hotel_info['checkin_date'] = line.split('入住日期:')[1].strip()
                    elif '退房日期:' in line:
                        hotel_info['checkout_date'] = line.split('退房日期:')[1].strip()
                    elif '房型:' in line:
                        hotel_info['room_type'] = line.split('房型:')[1].strip()
                    elif '客人信息:' in line:
                        hotel_info['guest_info'] = line.split('客人信息:')[1].strip()
    
    # 对于酒店类型，需要特殊处理表单提交
    if ref.ref_type and ref.ref_type.name == '酒店':
        if request.method == 'POST':
            try:
                # 处理supplier_id，将0转换为None
                if form.supplier_id.data == 0:
                    ref.supplier_id = None
                else:
                    ref.supplier_id = form.supplier_id.data
                
                # 更新基础字段
                ref.name = form.name.data
                ref.ref_type_id = form.ref_type_id.data
                ref.description = form.description.data
                ref.supplier_contact = form.supplier_contact.data
                ref.supplier_phone = form.supplier_phone.data
                ref.leader_name = form.leader_name.data
                ref.selling_price = form.selling_price.data
                ref.cost_price = form.cost_price.data
                ref.currency = form.currency.data
                ref.expected_delivery_date = form.expected_delivery_date.data
                ref.actual_delivery_date = form.actual_delivery_date.data
                ref.status = form.status.data
                ref.payment_status = form.payment_status.data
                
                # 处理酒店专属字段
                extra_info = request.form.get('extra_info')
                if extra_info:
                    try:
                        hotel_data = json.loads(extra_info)
                        ref.extra_info = extra_info
                        # 同时更新remarks字段以保持兼容性
                        ref.remarks = f"酒店名称: {hotel_data.get('hotel_name', '')}\n" \
                                    f"入住日期: {hotel_data.get('checkin_date', '')}\n" \
                                    f"退房日期: {hotel_data.get('checkout_date', '')}\n" \
                                    f"房型: {hotel_data.get('room_type', '')}\n" \
                                    f"客人信息: {hotel_data.get('remarks', '')}"
                    except json.JSONDecodeError as e:
                        pass
                
                db.session.commit()
                flash('酒店REF更新成功！', 'success')
                return redirect(url_for('projects.header_detail', header_id=ref.header_id))
            except Exception as e:
                db.session.rollback()
                flash(f'更新失败：{str(e)}', 'error')
    else:
        # 非酒店类型的标准处理
        if form.validate_on_submit():
            try:
                # 处理supplier_id，将0转换为None
                if form.supplier_id.data == 0:
                    ref.supplier_id = None
                else:
                    ref.supplier_id = form.supplier_id.data
                
                # 更新其他字段
                ref.name = form.name.data
                ref.ref_type_id = form.ref_type_id.data
                ref.description = form.description.data
                ref.supplier_contact = form.supplier_contact.data
                ref.supplier_phone = form.supplier_phone.data
                ref.leader_name = form.leader_name.data
                ref.selling_price = form.selling_price.data
                ref.cost_price = form.cost_price.data
                ref.currency = form.currency.data
                ref.expected_delivery_date = form.expected_delivery_date.data
                ref.actual_delivery_date = form.actual_delivery_date.data
                ref.remarks = form.remarks.data
                ref.status = form.status.data
                ref.payment_status = form.payment_status.data
                
                db.session.commit()
                return redirect(url_for('projects.ref_detail', ref_id=ref.id))
            except Exception as e:
                db.session.rollback()
                flash(f'更新失败：{str(e)}', 'error')
        elif form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 如果是酒店类型，使用通用酒店表单模板
    if ref.ref_type and ref.ref_type.name == '酒店':
        return render_template('projects/BookingProject/hotel_ref_form.html', 
                             form=form, 
                             ref=ref, 
                             hotel_info=hotel_info,
                             is_edit=True)
    else:
        return render_template('projects/BookingProject/edit_ref.html', form=form, ref=ref, hotel_info=hotel_info)

@projects.route('/eo/<int:eo_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_eo(eo_id):
    eo = ProjectEO.query.get_or_404(eo_id)
    form = ProjectEOForm(obj=eo)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(eo)
            db.session.commit()
            return redirect(url_for('projects.eo_detail', eo_id=eo.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('projects/BookingProject/edit_eo.html', form=form, eo=eo)

@projects.route('/eo/<int:eo_id>')
def eo_detail(eo_id):
    eo = ProjectEO.query.get_or_404(eo_id)
    return render_template('projects/BookingProject/eo_detail.html', eo=eo)

@projects.route('/generate_ref_number', methods=['GET'])
def generate_ref_number():
    """生成新的REF编号"""
    try:
        ref_number = ProjectRef.generate_ref_number("")  # 传递空字符串，因为不再需要project_hid
        return jsonify({'ref_number': ref_number})
    except Exception as e:
        error_details = traceback.format_exc()
        return jsonify({
            'error': str(e),
            'details': error_details
        }), 400 

@projects.route('/ref/delete/<int:ref_id>', methods=['POST', 'GET'])
@csrf.exempt
def delete_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    header_id = ref.header_id
    db.session.delete(ref)
    db.session.commit()
    flash('REF明细已删除', 'success')
    return redirect(url_for('projects.header_detail', header_id=header_id))

@projects.route('/header/delete/<int:header_id>', methods=['POST'])
@csrf.exempt
def delete_header(header_id):
    """删除项目主表"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)
        
        # 删除所有相关的EO（通过REF关联）
        refs = ProjectRef.query.filter_by(header_id=header_id).all()
        for ref in refs:
            # 删除该REF下的所有EO
            eos = ProjectEO.query.filter_by(ref_id=ref.id).all()
            for eo in eos:
                db.session.delete(eo)
            # 删除REF
            db.session.delete(ref)
        
        # 删除项目主表
        db.session.delete(header)
        db.session.commit()
        
        flash('项目已成功删除', 'success')
        return redirect(url_for('projects.list_projects'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
        return redirect(url_for('projects.header_detail', header_id=header_id))

# 业务类型ref创建路由
@projects.route('/ref/create_flight/<int:header_id>', methods=['GET', 'POST'])
def create_flight_ref_project(header_id):
    from App.models.projects.BookingProject import ProjectHeader
    from App.models.Product.Suppliers import Supplier
    header = ProjectHeader.query.get_or_404(header_id)
    hid = header.hid
    # 查询所有供应商
    suppliers = Supplier.query.all()
    # 获取所有供应商类型（去重）
    supplier_types = list({s.supplier_type for s in suppliers if s.supplier_type})
    return render_template(
        'flights/order_create.html',
        header_id=header_id,
        hid=hid,
        ref_mode='project_ref',
        suppliers=suppliers,
        supplier_types=supplier_types
    )

@projects.route('/ref/create_hotel/<int:header_id>', methods=['GET', 'POST'])
def create_hotel_ref(header_id):
    if request.method == 'POST':
        try:
            # 获取header
            header = ProjectHeader.query.get_or_404(header_id)
            
            # 生成REF编号
            ref_number = ProjectRef.generate_ref_number("")
            
            # 获取酒店业务类型ID
            hotel_business_type = BusinessType.query.filter_by(name='酒店').first()
            if not hotel_business_type:
                # 如果酒店类型不存在，创建它
                hotel_business_type = BusinessType(name='酒店', description='酒店预订业务')
                db.session.add(hotel_business_type)
                db.session.flush()
            
            # 创建酒店REF
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '酒店预订'),
                ref_type_id=hotel_business_type.id,
                description=request.form.get('name', '酒店预订'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') else None,
                supplier_contact=request.form.get('supplier_contact', ''),
                leader_name=request.form.get('leader_name', ''),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None,
                status=request.form.get('status') or 'draft',
                payment_status='unpaid',
                currency='SGD',
                remarks=f"酒店名称: {request.form.get('hotel_name', '')}\n"
                       f"入住日期: {request.form.get('checkin_date', '')}\n"
                       f"退房日期: {request.form.get('checkout_date', '')}\n"
                       f"房型: {request.form.get('room_type', '')}\n"
                       f"客人信息: {request.form.get('guest_info', '')}"
            )
            
            # 存储酒店专属信息到extra_info字段
            hotel_extra_info = {
                'hotel_name': request.form.get('hotel_name', ''),
                'checkin_date': request.form.get('checkin_date', ''),
                'checkout_date': request.form.get('checkout_date', ''),
                'room_type': request.form.get('room_type', ''),
                'guest_info': request.form.get('guest_info', '')
            }
            ref.extra_info = json.dumps(hotel_extra_info)
            
            db.session.add(ref)
            db.session.commit()
            
            flash('酒店明细创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    return render_template('projects/BookingProject/hotel_ref_form.html', 
                         suppliers=suppliers, 
                         is_edit=False,
                         hotel_info=None)

@projects.route('/ref/create_tour/<int:header_id>', methods=['GET', 'POST'])
def create_tour_ref(header_id):
    if request.method == 'POST':
        try:
            # 获取header
            header = ProjectHeader.query.get_or_404(header_id)
            
            # 生成REF编号
            ref_number = ProjectRef.generate_ref_number("")
            
            # 获取旅游团业务类型ID
            tour_business_type = BusinessType.query.filter_by(name='旅游团').first()
            if not tour_business_type:
                # 如果旅游团类型不存在，创建它
                tour_business_type = BusinessType(name='旅游团', description='旅游团业务')
                db.session.add(tour_business_type)
                db.session.flush()
            
            # 处理旅游团专属字段
            tour_extra_info = {
                'tour_name': request.form.get('tour_name', ''),
                'people_count': request.form.get('people_count', ''),
                'departure_date': request.form.get('departure_date', ''),
                'end_date': request.form.get('end_date', ''),
                'itinerary': request.form.get('itinerary', '')
            }
            
            # 创建旅游团REF
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '旅游团'),
                ref_type_id=tour_business_type.id,
                description=request.form.get('name', '旅游团'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') else None,
                supplier_contact=request.form.get('supplier_contact', ''),
                leader_name=request.form.get('leader_name', ''),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None,
                expected_delivery_date=request.form.get('departure_date'),
                actual_delivery_date=request.form.get('end_date'),
                status=request.form.get('status') or 'draft',
                payment_status='unpaid',
                currency='SGD',
                remarks=request.form.get('remarks', ''),
                extra_info=json.dumps(tour_extra_info)
            )
            
            db.session.add(ref)
            db.session.commit()
            
            # 检查是否是AJAX请求
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '旅游团明细创建成功！'})
            else:
                flash('旅游团明细创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header_id))
            
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'创建失败：{str(e)}'})
            else:
                flash(f'创建失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    # 在创建模式下，tour_info为空字典
    tour_info = {}
    
    return render_template('projects/BookingProject/create_tour_ref.html', 
                         suppliers=suppliers,
                         ref=None,
                         tour_info=tour_info,
                         is_create=True,
                         project_id=header_id)

@projects.route('/ref/create_visa/<int:header_id>', methods=['GET', 'POST'])
def create_visa_ref(header_id):
    if request.method == 'POST':
        try:
            # 获取header
            header = ProjectHeader.query.get_or_404(header_id)
            
            # 生成REF编号
            ref_number = ProjectRef.generate_ref_number("")
            
            # 获取签证业务类型ID
            visa_business_type = BusinessType.query.filter_by(name='签证').first()
            if not visa_business_type:
                # 如果签证类型不存在，创建它
                visa_business_type = BusinessType(name='签证', description='签证业务')
                db.session.add(visa_business_type)
                db.session.flush()
            
            # 获取自动生成的名称
            auto_name = request.form.get('name', '')
            if not auto_name:
                # 如果没有自动生成的名称，使用默认值
                auto_name = '签证申请'
            
            # 创建签证REF
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=auto_name,
                ref_type_id=visa_business_type.id,
                description=auto_name,
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') else None,
                supplier_contact=request.form.get('supplier_contact', ''),
                leader_name=request.form.get('leader_name', ''),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None,
                status=request.form.get('status') or 'draft',
                payment_status='unpaid',
                currency='SGD',
                expected_delivery_date=request.form.get('expected_delivery_date'),
                actual_delivery_date=request.form.get('actual_delivery_date'),
                remarks=request.form.get('remarks', '')
            )
            
            # 存储签证专属信息到extra_info字段
            visa_extra_info = {
                'country': request.form.get('country', ''),
                'visa_type': request.form.get('visa_type', ''),
                'applicant_info': request.form.get('applicant_info', '')
            }
            ref.extra_info = json.dumps(visa_extra_info)
            
            db.session.add(ref)
            db.session.commit()
            
            flash('签证明细创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    # 获取所有国家数据
    from App.models.Product.Visamodels import VisaCountries
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    
    # 在创建模式下，visa_info为空字典
    visa_info = {}
    
    return render_template('projects/BookingProject/create_visa_ref.html', 
                         suppliers=suppliers, 
                         ref=None,
                         countries=countries,
                         visa_info=visa_info,
                         is_create=True)


@projects.route('/api/get_visa_types/<int:country_id>')
def get_visa_types_by_country(country_id):
    """根据国家ID获取签证类型"""
    try:
        from App.models.Product.Visamodels import VisaTypes
        visa_types = VisaTypes.query.filter_by(country_id=country_id).order_by(VisaTypes.visa_type).all()
        
        visa_types_data = []
        for vt in visa_types:
            visa_types_data.append({
                'id': vt.id,
                'visa_type': vt.visa_type
            })
        
        return jsonify({
            'success': True,
            'visa_types': visa_types_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@projects.route('/ref/create_insurance/<int:header_id>', methods=['GET', 'POST'])
def create_insurance_ref(header_id):
    if request.method == 'POST':
        try:
            # 获取header
            header = ProjectHeader.query.get_or_404(header_id)
            
            # 生成REF编号
            ref_number = ProjectRef.generate_ref_number("")
            
            # 获取保险业务类型ID
            insurance_business_type = BusinessType.query.filter_by(name='保险').first()
            if not insurance_business_type:
                # 如果保险类型不存在，创建它
                insurance_business_type = BusinessType(name='保险', description='保险业务')
                db.session.add(insurance_business_type)
                db.session.flush()
            
            # 处理保险专属字段
            insurance_extra_info = {
                'insurance_company': request.form.get('insurance_company', ''),
                'insurance_type': request.form.get('insurance_type', ''),
                'insured_person': request.form.get('insured_person', ''),
                'insured_id_number': request.form.get('insured_id_number', ''),
                'insurance_details': request.form.get('insurance_details', '')
            }
            
            # 创建保险REF
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '保险服务'),
                ref_type_id=insurance_business_type.id,
                description=request.form.get('name', '保险服务'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') else None,
                supplier_contact=request.form.get('supplier_contact', ''),
                supplier_phone=request.form.get('supplier_phone', ''),
                leader_name=request.form.get('leader_name', ''),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None,
                expected_delivery_date=request.form.get('expected_delivery_date'),
                actual_delivery_date=request.form.get('actual_delivery_date'),
                status=request.form.get('status') or 'draft',
                payment_status='unpaid',
                currency='SGD',
                remarks=request.form.get('remarks', ''),
                extra_info=json.dumps(insurance_extra_info)
            )
            
            db.session.add(ref)
            db.session.commit()
            
            flash('保险明细创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    return render_template('projects/BookingProject/create_insurance_ref.html', 
                         suppliers=suppliers,
                         is_create=True)

@projects.route('/ref/create_transport/<int:header_id>', methods=['GET', 'POST'])
def create_transport_ref(header_id):
    if request.method == 'POST':
        try:
            # 获取header
            header = ProjectHeader.query.get_or_404(header_id)
            
            # 生成REF编号
            ref_number = ProjectRef.generate_ref_number("")
            
            # 获取交通业务类型ID
            transport_business_type = BusinessType.query.filter_by(name='交通').first()
            if not transport_business_type:
                # 如果交通类型不存在，创建它
                transport_business_type = BusinessType(name='交通', description='交通业务')
                db.session.add(transport_business_type)
                db.session.flush()
            
            # 创建交通REF
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '交通'),
                ref_type_id=transport_business_type.id,
                description=request.form.get('name', '交通'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') else None,
                supplier_contact=request.form.get('supplier_contact', ''),
                leader_name=request.form.get('leader_name', ''),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                status=request.form.get('status') or 'draft',
                payment_status='unpaid',
                currency='SGD',
                remarks=f"交通类型: {request.form.get('transport_type', '')}\n"
                       f"出发地: {request.form.get('departure', '')}\n"
                       f"目的地: {request.form.get('destination', '')}\n"
                       f"出发时间: {request.form.get('departure_time', '')}"
            )
            
            db.session.add(ref)
            db.session.commit()
            
            flash('交通明细创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    return render_template('projects/BookingProject/create_transport_ref.html', suppliers=suppliers)

@projects.route('/ref/create_other/<int:header_id>', methods=['GET', 'POST'])
def create_other_ref(header_id):
    if request.method == 'POST':
        try:
            # 获取header
            header = ProjectHeader.query.get_or_404(header_id)
            
            # 生成REF编号
            ref_number = ProjectRef.generate_ref_number("")
            
            # 获取其他业务类型ID
            other_business_type = BusinessType.query.filter_by(name='其他').first()
            if not other_business_type:
                # 如果其他类型不存在，创建它
                other_business_type = BusinessType(name='其他', description='其他业务')
                db.session.add(other_business_type)
                db.session.flush()
            
            # 创建其他REF
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '其他'),
                ref_type_id=other_business_type.id,
                description=request.form.get('name', '其他服务'),  # 使用name作为description
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') else None,
                supplier_contact=request.form.get('supplier_contact', ''),
                supplier_phone=request.form.get('supplier_phone', ''),
                leader_name=request.form.get('leader_name', ''),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None,
                currency='SGD',
                expected_delivery_date=request.form.get('expected_delivery_date'),
                actual_delivery_date=request.form.get('actual_delivery_date'),
                status=request.form.get('status') or 'draft',
                payment_status='unpaid',
                remarks=request.form.get('remarks', '')
            )
            
            db.session.add(ref)
            db.session.commit()
            
            flash('其他明细创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    return render_template('projects/BookingProject/create_other_ref.html', suppliers=suppliers) 

@projects.route('/ref/edit_other/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_other_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是其他类型的REF
    if not ref.ref_type or ref.ref_type.name != '其他':
        flash('只能编辑其他类型的REF', 'error')
        return redirect(url_for('projects.header_detail', header_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 更新REF数据
            ref.name = request.form.get('name', '其他')
            ref.description = request.form.get('name', '其他服务')  # 使用name作为description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') else None
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.supplier_phone = request.form.get('supplier_phone', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            ref.expected_delivery_date = request.form.get('expected_delivery_date')
            ref.actual_delivery_date = request.form.get('actual_delivery_date')
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            db.session.commit()
            return redirect(url_for('projects.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=ref.header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    return render_template('projects/BookingProject/create_other_ref.html', 
                         ref=ref, 
                         suppliers=suppliers)

@projects.route('/ref/edit_visa/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_visa_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是签证类型的REF
    if not ref.ref_type or ref.ref_type.name != '签证':
        flash('只能编辑签证类型的REF', 'error')
        return redirect(url_for('projects.header_detail', header_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 获取自动生成的名称
            auto_name = request.form.get('name', '')
            if not auto_name:
                # 如果没有自动生成的名称，使用默认值
                auto_name = '签证服务'
            
            # 更新REF数据
            ref.name = auto_name
            ref.description = auto_name  # 使用name作为description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') else None
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.supplier_phone = request.form.get('supplier_phone', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            ref.expected_delivery_date = request.form.get('expected_delivery_date')
            ref.actual_delivery_date = request.form.get('actual_delivery_date')
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            # 处理签证专属字段
            visa_extra_info = {
                'country': request.form.get('country', ''),
                'visa_type': request.form.get('visa_type', ''),
                'applicant_info': request.form.get('applicant_info', '')
            }
            ref.extra_info = json.dumps(visa_extra_info)
            
            db.session.commit()
            return redirect(url_for('projects.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=ref.header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    # 获取所有国家数据
    from App.models.Product.Visamodels import VisaCountries
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    
    # 解析签证专属信息
    visa_info = {}
    if ref and ref.extra_info:
        try:
            visa_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            visa_info = {}
    
    return render_template('projects/BookingProject/create_visa_ref.html', 
                         ref=ref, 
                         suppliers=suppliers,
                         countries=countries,
                         visa_info=visa_info,
                         is_create=False)

@projects.route('/ref/edit_insurance/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_insurance_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是保险类型的REF
    if not ref.ref_type or ref.ref_type.name != '保险':
        flash('只能编辑保险类型的REF', 'error')
        return redirect(url_for('projects.header_detail', header_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 更新REF数据
            ref.name = request.form.get('name', '保险服务')
            ref.description = request.form.get('name', '保险服务')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') else None
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.supplier_phone = request.form.get('supplier_phone', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            ref.expected_delivery_date = request.form.get('expected_delivery_date')
            ref.actual_delivery_date = request.form.get('actual_delivery_date')
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            # 处理保险专属字段
            insurance_extra_info = {
                'insurance_company': request.form.get('insurance_company', ''),
                'insurance_type': request.form.get('insurance_type', ''),
                'insured_person': request.form.get('insured_person', ''),
                'insured_id_number': request.form.get('insured_id_number', ''),
                'insurance_details': request.form.get('insurance_details', '')
            }
            ref.extra_info = json.dumps(insurance_extra_info)
            
            db.session.commit()
            return redirect(url_for('projects.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('projects.header_detail', header_id=ref.header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    # 解析保险专属信息
    insurance_info = {}
    if ref and ref.extra_info:
        try:
            insurance_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            insurance_info = {}
    
    return render_template('projects/BookingProject/create_insurance_ref.html', 
                         ref=ref, 
                         suppliers=suppliers,
                         insurance_info=insurance_info,
                         is_create=False)

@projects.route('/update_header_desc', methods=['POST'])
@csrf.exempt
def update_header_desc():
    data = request.get_json()
    header_id = data.get('header_id')
    desc = data.get('desc', '').strip()
    if not header_id or not desc:
        return jsonify({'success': False, 'message': '参数错误'})
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    header.desc = desc
    db.session.commit()
    return jsonify({'success': True}) 

@projects.route('/update_header_company', methods=['POST'])
@csrf.exempt
def update_header_company():
    data = request.get_json()
    header_id = data.get('header_id')
    company_id = data.get('company_id')
    if not header_id:
        return jsonify({'success': False, 'message': '参数错误'})
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    
    # 处理company_id，将0或空值转换为None
    if not company_id or company_id == 0:
        header.company_id = None
    else:
        header.company_id = company_id
    
    db.session.commit()
    return jsonify({'success': True})

@projects.route('/update_header_status', methods=['POST'])
@csrf.exempt
def update_header_status():
    data = request.get_json()
    header_id = data.get('header_id')
    status = data.get('status')
    if not header_id or not status:
        return jsonify({'success': False, 'message': '参数错误'})
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    header.status = status
    db.session.commit()
    return jsonify({'success': True}) 

@projects.route('/update_header_contact', methods=['POST'])
@csrf.exempt
def update_header_contact():
    data = request.get_json()
    header_id = data.get('header_id')
    contact = data.get('contact')
    if not header_id:
        return jsonify({'success': False, 'message': '参数错误'})
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    header.contact = contact
    db.session.commit()
    return jsonify({'success': True}) 

@projects.route('/ref/edit_tour/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_tour_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是旅游团类型的REF
    if not ref.ref_type or ref.ref_type.name != '旅游团':
        flash('只能编辑旅游团类型的REF', 'error')
        return redirect(url_for('projects.header_detail', header_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 更新REF数据
            ref.name = request.form.get('name', '旅游团')
            ref.description = request.form.get('name', '旅游团')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') else None
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            ref.expected_delivery_date = request.form.get('departure_date')
            ref.actual_delivery_date = request.form.get('end_date')
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            # 处理旅游团专属字段
            tour_extra_info = {
                'tour_name': request.form.get('tour_name', ''),
                'people_count': request.form.get('people_count', ''),
                'departure_date': request.form.get('departure_date', ''),
                'end_date': request.form.get('end_date', ''),
                'itinerary': request.form.get('itinerary', '')
            }
            ref.extra_info = json.dumps(tour_extra_info)
            
            db.session.commit()
            
            # 检查是否是AJAX请求
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '旅游团REF更新成功！'})
            else:
                return redirect(url_for('projects.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})
            else:
                flash(f'更新失败：{str(e)}', 'error')
                return redirect(url_for('projects.header_detail', header_id=ref.header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    # 解析旅游团专属信息
    tour_info = {}
    if ref and ref.extra_info:
        try:
            tour_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            tour_info = {}
    
    return render_template('projects/BookingProject/create_tour_ref.html', 
                         ref=ref, 
                         suppliers=suppliers,
                         tour_info=tour_info,
                         is_create=False,
                         project_id=ref.header_id) 

@projects.route('/eo/quick_create/<int:ref_id>', methods=['POST'])
@csrf.exempt
def quick_create_eo(ref_id):
    """一键生成EO - API接口"""
    try:
        ref = ProjectRef.query.get_or_404(ref_id)
        
        # 生成EO编号
        eo_number = ProjectEO.generate_eo_number()
        
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
            eo_number=eo_number,
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
        
        db.session.add(eo)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'EO {eo_number} 创建成功！',
            'eo_number': eo_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'创建失败：{str(e)}'
        }), 500

@projects.route('/receipt/create/<int:ref_id>', methods=['GET', 'POST'])
def create_receipt(ref_id):
    """创建收款记录"""
    from App.forms.receipt_forms import ProjectReceiptForm
    from App.models.projects.BookingProject import ProjectReceipt
    
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
            db.session.add(receipt)
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
            
            return redirect(url_for('projects.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    
    # 获取REF的未付款金额
    total_received = sum(float(r.amount) for r in ref.receipts if r.status == 'confirmed')
    unpaid_amount = float(ref.selling_price or 0) - total_received
    
    return render_template('projects/BookingProject/create_receipt.html',
                         form=form,
                         ref=ref,
                         receipt_number=receipt_number,
                         unpaid_amount=unpaid_amount)

@projects.route('/receipt/<int:receipt_id>')
def receipt_detail(receipt_id):
    """收款记录详情"""
    from App.models.projects.BookingProject import ProjectReceipt
    
    receipt = ProjectReceipt.query.get_or_404(receipt_id)
    return render_template('projects/BookingProject/receipt_detail.html', receipt=receipt)

@projects.route('/receipt/<int:receipt_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_receipt(receipt_id):
    """编辑收款记录"""
    from App.forms.receipt_forms import ProjectReceiptForm
    from App.models.projects.BookingProject import ProjectReceipt
    
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
            
            return redirect(url_for('projects.header_detail', header_id=receipt.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    return render_template('projects/BookingProject/edit_receipt.html',
                         form=form,
                         receipt=receipt)

@projects.route('/receipt/<int:receipt_id>/delete', methods=['POST'])
@csrf.exempt
def delete_receipt(receipt_id):
    """删除收款记录"""
    from App.models.projects.BookingProject import ProjectReceipt
    
    receipt = ProjectReceipt.query.get_or_404(receipt_id)
    header_id = receipt.header_id
    
    try:
        # 先删除收款记录
        db.session.delete(receipt)
        db.session.flush()
        
        # 重新查询REF以获取最新的收款记录
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
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
    return redirect(url_for('projects.header_detail', header_id=header_id))

@projects.route('/receipt/<int:receipt_id>/status', methods=['POST'])
@csrf.exempt
def update_receipt_status(receipt_id):
    """更新收款记录状态"""
    from App.models.projects.BookingProject import ProjectReceipt
    
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

@projects.route('/api/ref/<int:ref_id>/receipts')
def get_ref_receipts(ref_id):
    """获取REF的收款记录列表 - API接口"""
    from App.models.projects.BookingProject import ProjectReceipt
    
    ref = ProjectRef.query.get_or_404(ref_id)
    receipts = ProjectReceipt.query.filter_by(ref_id=ref_id).order_by(ProjectReceipt.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'receipts': [receipt.to_dict() for receipt in receipts],
        'total_received': sum(float(r.amount) for r in receipts if r.status == 'confirmed'),
        'unpaid_amount': float(ref.selling_price or 0) - sum(float(r.amount) for r in receipts if r.status == 'confirmed')
    })

@projects.route('/ref/<int:ref_id>/receipts')
def ref_receipts(ref_id):
    """查看REF的收款记录列表"""
    from App.models.projects.BookingProject import ProjectReceipt
    
    ref = ProjectRef.query.get_or_404(ref_id)
    receipts = ProjectReceipt.query.filter_by(ref_id=ref_id).order_by(ProjectReceipt.created_at.desc()).all()
    
    # 计算已收款和未收款金额
    total_received = sum(float(r.amount) for r in receipts if r.status == 'confirmed')
    unpaid_amount = float(ref.selling_price or 0) - total_received
    
    return render_template('projects/BookingProject/ref_receipts.html',
                         ref=ref,
                         receipts=receipts,
                         total_received=total_received,
                         unpaid_amount=unpaid_amount)

# 项目级别收款管理路由
@projects.route('/header/<int:header_id>/receipts')
def header_receipts(header_id):
    """查看项目的收款记录列表"""
    from App.models.projects.BookingProject import ProjectReceipt
    import json
    
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
    
    return render_template('projects/BookingProject/header_receipts.html',
                         header=header,
                         all_receipts=all_receipts,
                         total_received=total_received,
                         unpaid_amount=unpaid_amount)

@projects.route('/header/<int:header_id>/receipt/create', methods=['GET', 'POST'])
def create_header_receipt(header_id):
    """创建项目级别收款记录"""
    from App.forms.receipt_forms import ProjectLevelReceiptForm
    from App.models.projects.BookingProject import ProjectReceipt
    
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
                return render_template('projects/BookingProject/create_header_receipt.html',
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
                    return render_template('projects/BookingProject/create_header_receipt.html',
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
                    return render_template('projects/BookingProject/create_header_receipt.html',
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
                return render_template('projects/BookingProject/create_header_receipt.html',
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
            
            return redirect(url_for('projects.header_receipts', header_id=header.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    
    # 获取项目的未付款金额
    unpaid_amount = ProjectReceipt.get_project_unpaid_amount(header_id)
    
    return render_template('projects/BookingProject/create_header_receipt.html',
                         form=form,
                         header=header,
                         receipt_number=receipt_number,
                         unpaid_amount=unpaid_amount)

@projects.route('/header/<int:header_id>/receipt/<int:receipt_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_header_receipt(header_id, receipt_id):
    """编辑项目级别收款记录"""
    from App.forms.receipt_forms import ProjectLevelReceiptForm
    from App.models.projects.BookingProject import ProjectReceipt
    
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
            
            return redirect(url_for('projects.header_receipts', header_id=header.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    return render_template('projects/BookingProject/edit_header_receipt.html',
                         form=form,
                         header=header,
                         receipt=receipt)

@projects.route('/header/<int:header_id>/receipt/<int:receipt_id>/delete', methods=['POST'])
@csrf.exempt
def delete_header_receipt(header_id, receipt_id):
    """删除项目级别收款记录"""
    from App.models.projects.BookingProject import ProjectReceipt
    
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
    
    return redirect(url_for('projects.header_receipts', header_id=header_id))

@projects.route('/api/header/<int:header_id>/unpaid_refs')
def get_header_unpaid_refs(header_id):
    """获取项目下各REF的未收款详情 - API接口"""
    from App.models.projects.BookingProject import ProjectReceipt
    
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