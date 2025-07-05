from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from App.models.projects.BookingProject import db, ProjectHeader, ProjectRef, ProjectEO, ProjectFlightPassenger, ProjectFlightSegment
from App.models.Product.Suppliers import Supplier
from App.models.Product.BusinessType import BusinessType
from App.forms.header_forms import ProjectHeaderForm
from App.forms.ref_forms import ProjectRefForm
from App.forms.eo_forms import ProjectEOForm
from datetime import datetime
from sqlalchemy import func
import traceback  # 添加traceback模块

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
    header = ProjectHeader.query.get_or_404(header_id)
    
    # 获取上一个和下一个项目
    prev_header = ProjectHeader.query.filter(
        ProjectHeader.id < header_id
    ).order_by(ProjectHeader.id.desc()).first()
    
    next_header = ProjectHeader.query.filter(
        ProjectHeader.id > header_id
    ).order_by(ProjectHeader.id.asc()).first()
    
    # 获取公司信息（通过backref自动关联）
    company = header.company
    
    return render_template('projects/BookingProject/header_detail.html', 
                         header=header, 
                         company=company,
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
            ref.supplier_id = request.form.get('supplier_id')
            ref.contact_name = request.form.get('contact_name')
            ref.contact_phone = request.form.get('contact_phone')
            ref.contact_email = request.form.get('contact_email')
            ref.remarks = request.form.get('remarks')
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
                supplier_id=request.form.get('supplier_id'),
                contact_name=request.form.get('contact_name'),
                contact_phone=request.form.get('contact_phone'),
                contact_email=request.form.get('contact_email'),
                remarks=request.form.get('remarks'),
                status='draft'
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
            if flight_numbers[i]:  # 确保航班号不为空
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
                        flight_number=flight_numbers[i],
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
                    print(f"处理航段 {i} 时出错: {e}")
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
    ref = ProjectRef.query.get_or_404(ref_id)
    
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
    return render_template('projects/BookingProject/visa_ref_detail.html', ref=ref)

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
    
    if form.validate_on_submit():
        try:
            eo_number = ProjectEO.generate_eo_number(ref.ref_number)
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
    eo_number = ProjectEO.generate_eo_number(ref.ref_number)
    form.eo_number.data = eo_number
    
    return render_template('projects/BookingProject/create_eo.html',
                           form=form, ref=ref, eo_number=eo_number)

@projects.route('/')
def list_projects():
    status = request.args.get('status')
    query = ProjectHeader.query

    if status:
        query = query.filter(ProjectHeader.status == status)
    
    projects = query.order_by(ProjectHeader.created_at.desc()).all()
    return render_template('projects/BookingProject/list_projects.html', projects=projects)

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
            form.populate_obj(header)
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
def edit_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    form = ProjectRefForm(obj=ref)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(ref)
            db.session.commit()
            flash('REF明细更新成功！', 'success')
            return redirect(url_for('projects.ref_detail', ref_id=ref.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('projects/BookingProject/edit_ref.html', form=form, ref=ref)

@projects.route('/eo/<int:eo_id>/edit', methods=['GET', 'POST'])
def edit_eo(eo_id):
    eo = ProjectEO.query.get_or_404(eo_id)
    form = ProjectEOForm(obj=eo)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(eo)
            db.session.commit()
            flash('EO子明细更新成功！', 'success')
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
        print("Generating new REF number")
        ref_number = ProjectRef.generate_ref_number("")  # 传递空字符串，因为不再需要project_hid
        print(f"Generated REF number: {ref_number}")
        return jsonify({'ref_number': ref_number})
    except Exception as e:
        error_details = traceback.format_exc()
        print("Error generating REF number:", error_details)
        return jsonify({
            'error': str(e),
            'details': error_details
        }), 400 

@projects.route('/ref/delete/<int:ref_id>', methods=['POST', 'GET'])
def delete_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    header_id = ref.header_id
    db.session.delete(ref)
    db.session.commit()
    flash('REF明细已删除', 'success')
    return redirect(url_for('projects.header_detail', header_id=header_id))

@projects.route('/header/delete/<int:header_id>', methods=['POST'])
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
        # 这里处理酒店类型ref的表单提交逻辑
        # TODO: 保存到数据库
        flash('酒店明细创建成功！', 'success')
        return redirect(url_for('projects.header_detail', header_id=header_id))
    return render_template('projects/BookingProject/create_hotel_ref.html')

@projects.route('/ref/create_tour/<int:header_id>', methods=['GET', 'POST'])
def create_tour_ref(header_id):
    if request.method == 'POST':
        # 这里处理旅游团类型ref的表单提交逻辑
        # TODO: 保存到数据库
        flash('旅游团明细创建成功！', 'success')
        return redirect(url_for('projects.header_detail', header_id=header_id))
    return render_template('projects/BookingProject/create_tour_ref.html')

@projects.route('/ref/create_visa/<int:header_id>', methods=['GET', 'POST'])
def create_visa_ref(header_id):
    if request.method == 'POST':
        # 这里处理签证类型ref的表单提交逻辑
        # TODO: 保存到数据库
        flash('签证明细创建成功！', 'success')
        return redirect(url_for('projects.header_detail', header_id=header_id))
    return render_template('projects/BookingProject/create_visa_ref.html')

@projects.route('/ref/create_insurance/<int:header_id>', methods=['GET', 'POST'])
def create_insurance_ref(header_id):
    if request.method == 'POST':
        # 这里处理保险类型ref的表单提交逻辑
        # TODO: 保存到数据库
        flash('保险明细创建成功！', 'success')
        return redirect(url_for('projects.header_detail', header_id=header_id))
    return render_template('projects/BookingProject/create_insurance_ref.html')

@projects.route('/ref/create_transport/<int:header_id>', methods=['GET', 'POST'])
def create_transport_ref(header_id):
    if request.method == 'POST':
        # 这里处理交通类型ref的表单提交逻辑
        # TODO: 保存到数据库
        flash('交通明细创建成功！', 'success')
        return redirect(url_for('projects.header_detail', header_id=header_id))
    return render_template('projects/BookingProject/create_transport_ref.html')

@projects.route('/ref/create_other/<int:header_id>', methods=['GET', 'POST'])
def create_other_ref(header_id):
    if request.method == 'POST':
        # 这里处理其他类型ref的表单提交逻辑
        # TODO: 保存到数据库
        flash('其他明细创建成功！', 'success')
        return redirect(url_for('projects.header_detail', header_id=header_id))
    return render_template('projects/BookingProject/create_other_ref.html') 