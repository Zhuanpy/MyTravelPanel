from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.models import FlightOrder, Passenger, FlightSegment, FlightSchedule, AirportData
from App_new.shared.models.Suppliers import Supplier
from App_new.business.visa.models.Visamodels import VisaCountries
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.flight.models.flight import ProjectFlightSegment, ProjectFlightPassenger
from App_new.shared.models.business_types import BusinessType
from App_new.utils.decorators import staff_only
from datetime import datetime, timedelta
from App_new.exts import db
import random
import string
import json

flights_booking = Blueprint('flights_booking', __name__, url_prefix='/flights_booking')

def generate_order_number():
    """生成订单编号：TP + 年月日 + 6位随机数"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.digits, k=6))
    return f'TP{date_str}{random_str}'

@flights_booking.route('/create_order', methods=['GET'])
@login_required
@staff_only
def create_order():
    """创建订单页面"""
    # 获取所有活跃的供应商
    suppliers = Supplier.query.filter_by(status='active').all()
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_types()
    return render_template('business/flight/order_create.html', 
                         suppliers=suppliers,
                         supplier_types=supplier_types)

@flights_booking.route('/submit_order', methods=['POST'])
@login_required
@staff_only
def submit_order():
    """提交订单处理"""
    try:
        print("开始处理订单提交...")  # 调试日志
        print("接收到的表单数据:")
        
        # 详细的表单数据调试
        print("所有表单数据:", request.form.to_dict(flat=False))
        print("乘客姓名列表:", request.form.getlist('passenger_name[]'))
        print("第一个乘客姓名:", request.form.getlist('passenger_name[]')[0] if request.form.getlist('passenger_name[]') else "无")
        print("联系人姓名:", request.form.get('contact_name'))
        
        # 1. 获取第一个航段的信息用于主表
        first_flight_number = request.form.getlist('flight_number[]')[0]
        first_departure_time_str = request.form.getlist('departure_time[]')[0]
        # 处理可能的两种日期时间格式
        try:
            first_departure_time = datetime.strptime(first_departure_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            first_departure_time = datetime.strptime(first_departure_time_str, '%Y-%m-%d %H:%M')
            
        first_departure_airport = request.form.getlist('departure_airport[]')[0]
        last_arrival_airport = request.form.getlist('arrival_airport[]')[-1]
        
        # 2. 自动生成HID和REF
        print("开始生成HID和REF...")
        
        # 获取或创建"个人"公司记录
        from App_new.business.projects.models.project import CustomerCompany
        personal_company = CustomerCompany.query.filter_by(company_name='个人').first()
        if not personal_company:
            personal_company = CustomerCompany(
                company_name='个人',
                company_code='PERSONAL',
                contact_person='系统',
                status='active',
                created_by='系统'
            )
            db.session.add(personal_company)
            db.session.flush()  # 获取ID
        
        # 创建项目主表（HID）
        hid = ProjectHeader.generate_hid()
        project_header = ProjectHeader(
            hid=hid,
            desc=f"机票订单 - {request.form['contact_name']} - {first_departure_airport}>{last_arrival_airport}",
            company_id=personal_company.id,  # 自动设置为"个人"公司
            contact=request.form['contact_name'],
            staff_id=current_user.id if current_user else None,
            staff_name=current_user.profile.get_full_name() if current_user and current_user.profile and current_user.profile.get_full_name() != "未设置姓名" else (current_user.profile.first_name if current_user and current_user.profile else '系统'),
            currency='SGD',  # 默认货币
            type='flight',
            status='active',
            remarks=request.form.get('remarks', '')
        )
        db.session.add(project_header)
        db.session.flush()  # 获取project_header.id
        print(f"创建项目主表: {hid}")
        
        # 获取机票业务类型
        flight_business_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_business_type:
            # 如果不存在，创建一个默认的机票业务类型
            flight_business_type = BusinessType(
                name='机票',
                description='机票订单业务',
                is_active=True
            )
            db.session.add(flight_business_type)
            db.session.flush()
        
        # 读取前端供应商/状态字段
        selected_supplier_id = request.form.get('supplier_id')
        selected_status = request.form.get('status') or 'processing'
        selected_payment_status = request.form.get('payment_status') or 'unpaid'

        # 创建项目明细表（REF）
        ref_number = ProjectRef.generate_ref_number()
        
        # 计算总价
        selling_prices = request.form.getlist('selling_price[]')
        cost_prices = request.form.getlist('cost_price[]')
        total_selling_price = sum(float(price) for price in selling_prices if price)
        total_cost_price = sum(float(price) for price in cost_prices if price)
        
        # 生成机票REF名称：参考项目模块的生成规则（出发日期DDMON + 航线路径）
        def generate_flight_ref_name(departure_airports, arrival_airports, departure_times):
            try:
                first_dep_time_str = departure_times[0] if departure_times else None
                if first_dep_time_str:
                    try:
                        first_dep_dt = datetime.strptime(first_dep_time_str, '%Y-%m-%dT%H:%M')
                    except ValueError:
                        first_dep_dt = datetime.strptime(first_dep_time_str, '%Y-%m-%d %H:%M')
                    formatted_date = first_dep_dt.strftime('%d%b').upper()
                else:
                    formatted_date = datetime.now().strftime('%d%b').upper()
            except Exception:
                formatted_date = datetime.now().strftime('%d%b').upper()

            # 构建有效航段
            valid_segments = []
            for dep, arr in zip(departure_airports, arrival_airports):
                if dep and arr:
                    valid_segments.append((dep, arr))

            if not valid_segments:
                return f"{formatted_date} 机票订单"

            if len(valid_segments) == 1:
                dep_airport, arr_airport = valid_segments[0]
                return f"{formatted_date} {dep_airport}-{arr_airport}"

            if len(valid_segments) == 2:
                dep1, arr1 = valid_segments[0]
                dep2, arr2 = valid_segments[1]
                if dep1 == arr2 and arr1 == dep2:
                    return f"{formatted_date} {dep1}-{arr1}-{dep1}"
                return f"{formatted_date} {dep1}-{arr1}-{arr2}"

            route_parts = []
            for i, (dep_airport, arr_airport) in enumerate(valid_segments):
                if i == 0:
                    route_parts.append(f"{dep_airport}-{arr_airport}")
                else:
                    route_parts.append(arr_airport)
            return f"{formatted_date} {'-'.join(route_parts)}"

        # 取第一个乘客作为出行人(leader_name)
        passenger_names_for_leader = request.form.getlist('passenger_name[]')
        first_passenger_name_for_leader = passenger_names_for_leader[0] if passenger_names_for_leader else request.form['contact_name']

        # 生成REF名称
        dep_airports_list = request.form.getlist('departure_airport[]')
        arr_airports_list = request.form.getlist('arrival_airport[]')
        dep_times_list = request.form.getlist('departure_time[]')
        generated_ref_name = generate_flight_ref_name(dep_airports_list, arr_airports_list, dep_times_list)

        project_ref = ProjectRef(
            header_id=project_header.id,
            ref_number=ref_number,
            name=generated_ref_name,
            ref_type_id=flight_business_type.id,
            description=f"{first_departure_airport} > {last_arrival_airport} 机票订单",
            supplier_id=int(selected_supplier_id) if selected_supplier_id else None,
            contact_name=request.form['contact_name'],
            contact_phone=request.form.get('contact_phone', ''),
            contact_email=request.form.get('contact_email', ''),
            leader_name=first_passenger_name_for_leader,
            selling_price=total_selling_price,
            cost_price=total_cost_price,
            currency='SGD',
            expected_delivery_date=first_departure_time.date(),
            remarks=request.form.get('remarks', ''),
            status=selected_status,
            payment_status=selected_payment_status
        )
        db.session.add(project_ref)
        db.session.flush()  # 获取project_ref.id
        print(f"创建项目明细: {ref_number}")
        
        # 2.1 创建REF的航段信息
        flight_numbers = request.form.getlist('flight_number[]')
        cabin_codes = request.form.getlist('cabin_code[]')
        departure_airports = request.form.getlist('departure_airport[]')
        arrival_airports = request.form.getlist('arrival_airport[]')
        departure_dates = request.form.getlist('departure_date[]')
        departure_times = request.form.getlist('departure_time[]')
        arrival_dates = request.form.getlist('arrival_date[]')
        arrival_times = request.form.getlist('arrival_time[]')
        
        print(f"航段数据: {len(flight_numbers)} 个航段")
        
        for i in range(len(flight_numbers)):
            if flight_numbers[i]:  # 只处理非空的航班号
                try:
                    # 处理出发时间
                    if i < len(departure_dates) and departure_dates[i]:
                        dep_date = departure_dates[i]
                        dep_time = departure_times[i] if i < len(departure_times) and departure_times[i] else '00:00'
                        dep_datetime = datetime.strptime(f"{dep_date} {dep_time}", '%Y-%m-%d %H:%M')
                    else:
                        dep_datetime = first_departure_time
                    
                    # 处理到达时间
                    if i < len(arrival_dates) and arrival_dates[i]:
                        arr_date = arrival_dates[i]
                        arr_time = arrival_times[i] if i < len(arrival_times) and arrival_times[i] else '00:00'
                        arr_datetime = datetime.strptime(f"{arr_date} {arr_time}", '%Y-%m-%d %H:%M')
                    else:
                        arr_datetime = dep_datetime + timedelta(hours=2)  # 默认2小时后到达
                    
                    segment = ProjectFlightSegment(
                        ref_id=project_ref.id,
                        flight_number=flight_numbers[i],
                        departure_airport=departure_airports[i] if i < len(departure_airports) else '',
                        arrival_airport=arrival_airports[i] if i < len(arrival_airports) else '',
                        departure_time=dep_datetime,
                        arrival_time=arr_datetime,
                        cabin_class=cabin_codes[i] if i < len(cabin_codes) else 'Y',
                        cabin_code=cabin_codes[i] if i < len(cabin_codes) else 'Y',
                        status='pending'
                    )
                    db.session.add(segment)
                    print(f"创建航段: {flight_numbers[i]} {departure_airports[i] if i < len(departure_airports) else ''}-{arrival_airports[i] if i < len(arrival_airports) else ''}")
                    
                except (ValueError, IndexError) as e:
                    print(f"航段 {i} 处理错误: {e}")
                    continue
        
        # 2.2 创建REF的乘客信息
        passenger_names = request.form.getlist('passenger_name[]')
        passenger_types = request.form.getlist('passenger_type[]')
        selling_prices = request.form.getlist('selling_price[]')
        cost_prices = request.form.getlist('cost_price[]')
        ticket_numbers = request.form.getlist('ticket_number[]')
        pnrs = request.form.getlist('pnr[]')
        
        print(f"乘客数据: {len(passenger_names)} 个乘客")
        
        for i in range(len(passenger_names)):
            if passenger_names[i]:  # 只处理非空的乘客姓名
                try:
                    passenger = ProjectFlightPassenger(
                        ref_id=project_ref.id,
                        name=passenger_names[i],
                        passenger_type=passenger_types[i] if i < len(passenger_types) and passenger_types[i] else 'adult',
                        selling_price=float(selling_prices[i]) if i < len(selling_prices) and selling_prices[i] else None,
                        cost_price=float(cost_prices[i]) if i < len(cost_prices) and cost_prices[i] else None,
                        ticket_number=ticket_numbers[i] if i < len(ticket_numbers) and ticket_numbers[i] else '',
                        pnr=pnrs[i] if i < len(pnrs) and pnrs[i] else ''
                    )
                    db.session.add(passenger)
                    print(f"创建乘客: {passenger_names[i]} - 售价: {selling_prices[i] if i < len(selling_prices) else 'N/A'}")
                    
                except (ValueError, IndexError) as e:
                    print(f"乘客 {i} 处理错误: {e}")
                    continue
        
        # 3. 创建订单主表记录
        passenger_names = request.form.getlist('passenger_name[]')
        if not passenger_names:
            raise ValueError("未提供乘客姓名")
            
        # 解析供应商名称（用于订单主表冗余存储显示）
        supplier_name_value = None
        if selected_supplier_id:
            try:
                supplier_obj = Supplier.query.get(int(selected_supplier_id))
                supplier_name_value = supplier_obj.name if supplier_obj else None
            except Exception:
                supplier_name_value = None

        order = FlightOrder(
            order_number=generate_order_number(),
            project_header_id=project_header.id,  # 关联HID
            project_ref_id=project_ref.id,        # 关联REF
            contact_name=request.form['contact_name'],
            contact_person=request.form['contact_name'],  # 使用联系人姓名作为联系人
            contact_phone=request.form.get('contact_phone', ''),  # 修改为get方法，允许为空
            supplier_name=supplier_name_value or '',
            passenger_name=passenger_names[0],  # 确保使用第一个乘客姓名
            departure_date=first_departure_time.date(),
            departure_city=first_departure_airport,
            arrival_city=last_arrival_airport,
            flight_number=first_flight_number,
            departure_time=first_departure_time,
            selling_price=total_selling_price,
            cost_price=total_cost_price,
            status='pending',
            order_status='pending',
            payment_status=selected_payment_status,
            remarks=request.form.get('remarks', '')
        )
        
        print(f"订单基本信息: {order.order_number}, HID: {hid}, REF: {ref_number}")  # 调试日志
        db.session.add(order)
        db.session.flush()  # 获取order.id

        # 4. 处理乘客信息
        
        # 获取基本乘客信息
        passenger_names = request.form.getlist('passenger_name[]')
        passenger_types = request.form.getlist('passenger_type[]')
        selling_prices = request.form.getlist('selling_price[]')
        cost_prices = request.form.getlist('cost_price[]')
        
        # 安全获取ticket_number和pnr，确保长度与passenger_names匹配
        ticket_numbers = []
        pnrs = []
        for _ in range(len(passenger_names)):
            ticket_numbers.append('')
            pnrs.append('')
            
        # 获取实际提交的值
        submitted_ticket_numbers = request.form.getlist('ticket_number[]')
        submitted_pnrs = request.form.getlist('pnr[]')
        
        # 将提交的值填充到准备好的数组中
        for i in range(len(submitted_ticket_numbers)):
            if i < len(ticket_numbers):
                ticket_numbers[i] = submitted_ticket_numbers[i]
                
        for i in range(len(submitted_pnrs)):
            if i < len(pnrs):
                pnrs[i] = submitted_pnrs[i]
        
        # 处理乘客信息
        for i in range(len(passenger_names)):
            name = passenger_names[i]
            p_type = passenger_types[i]
            selling_price = selling_prices[i]
            cost_price = cost_prices[i]
            ticket_number = ticket_numbers[i]
            pnr = pnrs[i]
            
            print(f"处理乘客信息: {name}")  # 调试日志
            passenger = Passenger(
                order_id=order.id,
                name=name,
                passenger_type=p_type,
                selling_price=float(selling_price),
                cost_price=float(cost_price),
                ticket_number=ticket_number if ticket_number else None,
                pnr=pnr if pnr else None
            )
            db.session.add(passenger)
            total_selling_price += float(selling_price)
            total_cost_price += float(cost_price)

        # 4. 处理航段信息
        segments_data = zip(
            request.form.getlist('flight_number[]'),
            request.form.getlist('departure_airport[]'),
            request.form.getlist('arrival_airport[]'),
            request.form.getlist('departure_time[]'),
            request.form.getlist('arrival_time[]'),
            request.form.getlist('cabin_class[]'),
            request.form.getlist('cabin_code[]')
        )

        # 构建行程信息
        itinerary_parts = []
        for f_num, dep, arr, dep_time, arr_time, c_class, c_code in segments_data:
            print(f"处理航段信息: {f_num}")  # 调试日志
            # 处理可能的两种日期时间格式
            try:
                departure_time = datetime.strptime(dep_time, '%Y-%m-%dT%H:%M')
                arrival_time = datetime.strptime(arr_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                departure_time = datetime.strptime(dep_time, '%Y-%m-%d %H:%M')
                arrival_time = datetime.strptime(arr_time, '%Y-%m-%d %H:%M')
                
            segment = FlightSegment(
                order_id=order.id,
                flight_number=f_num,
                departure_airport=dep,
                arrival_airport=arr,
                departure_time=departure_time,
                arrival_time=arrival_time,
                cabin_class=c_class,
                cabin_code=c_code,
                status='pending'
            )
            db.session.add(segment)
            itinerary_parts.append(f"{dep}-{arr}")

        # 5. 更新订单其他信息
        order.itinerary = '/'.join(itinerary_parts)
        order.selling_price = total_selling_price
        order.cost_price = total_cost_price
        print(f"订单总金额: {order.selling_price}")  # 调试日志
        
        # 提交事务
        print("准备提交事务...")  # 调试日志
        db.session.commit()
        print("事务提交成功!")  # 调试日志

        # 跳转到订单详情：此处详情页按 ProjectRef.id 展示
        return redirect(url_for('flights_booking.order_detail', order_id=project_ref.id))

    except Exception as e:
        db.session.rollback()
        print(f"订单创建失败: {str(e)}")  # 调试日志
        # 回填用户已填写的数据，避免选择项丢失
        try:
            suppliers = Supplier.query.filter_by(status='active').all()
            supplier_types = Supplier.get_supplier_types()
        except Exception:
            suppliers = []
            supplier_types = []
        # 将表单数据传回页面用于回显
        form_data = request.form.to_dict(flat=False)
        flash(f'订单创建失败：{str(e)}', 'error')
        return render_template(
            'business/flight/order_create.html',
            suppliers=suppliers,
            supplier_types=supplier_types,
            form_data=form_data
        )

@flights_booking.route('/order_detail/<int:order_id>')
@login_required
@staff_only

def order_detail(order_id):
    """订单详情页面（按 REF ID 构建）"""
    # 这里的 order_id 实际为 ProjectRef.id
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.flight.models.flight import ProjectFlightSegment, ProjectFlightPassenger

    ref = ProjectRef.query.get_or_404(order_id)
    header = ProjectHeader.query.get(ref.header_id) if ref.header_id else None
    # 关联的 FlightOrder（如果有），用于状态更新等操作
    try:
        from App_new.business.flight.models.models import FlightOrder as NewFlightOrder
        FlightOrderModel = NewFlightOrder
    except Exception:
        from App_new.business.flight.models.models import FlightOrder as FlightOrderModel  # 兼容导入
    flight_order = FlightOrderModel.query.filter_by(project_ref_id=ref.id).order_by(FlightOrderModel.id.desc()).first()

    # 明细：乘客与航段
    passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).all()
    flight_segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).order_by(ProjectFlightSegment.departure_time).all()

    # 组装模板所需字段
    order = {
        'id': ref.id,
        'order_number': ref.ref_number,
        'project_header_hid': header.hid if header else None,
        'project_ref_ref_number': ref.ref_number,
        'order_status': ref.status,  # 保留为 REF 状态，供显示兼容
        'selling_price': float(ref.selling_price or 0),
        'cost_price': float(ref.cost_price or 0),
        'supplier_name': ref.supplier.name if getattr(ref, 'supplier', None) else '',
        'supplier_type': ref.supplier.supplier_type if getattr(ref, 'supplier', None) else '',
        'contact_person': ref.contact_name,
        'contact_phone': ref.contact_phone,
        'remarks': ref.remarks,
        'project_header': header,
        'passengers': passengers,
        'flight_segments': flight_segments,
        # 注入 FlightOrder 信息
        'flight_order_id': flight_order.id if flight_order else None,
        'flight_order_status': flight_order.order_status if flight_order else None,
    }

    return render_template('business/flight/order_detail.html', order=order)

@flights_booking.route('/search_flights', methods=['POST'])
@login_required
@staff_only
def search_flights():
    """搜索航班信息"""
    dep_airport = request.form.get('departure_airport')
    arr_airport = request.form.get('arrival_airport')
    
    flights = FlightSchedule.query.filter_by(
        departure_airport=dep_airport,
        arrival_airport=arr_airport
    ).all()
    
    return jsonify([flight.to_dict() for flight in flights])

@flights_booking.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
@staff_only
def cancel_order(order_id):
    """取消订单"""
    try:
        order = FlightOrder.query.get_or_404(order_id)
        
        # 检查订单状态是否允许取消
        if order.order_status != 'pending':
            return jsonify({
                'success': False,
                'message': '只能取消待处理状态的订单'
            })
        
        # 更新订单状态
        order.order_status = 'cancelled'
        order.status = 'cancelled'
        
        # 更新所有航段状态
        for segment in order.flight_segments:
            segment.status = 'cancelled'
        
        # 提交更改
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '订单取消成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'订单取消失败：{str(e)}'
        })

@flights_booking.route('/orders')
@login_required
@staff_only
def order_list():
    """订单列表页面 - 从新的project_flight_segments表获取数据"""
    from App_new.business.flight.models.flight import ProjectFlightSegment, ProjectFlightPassenger
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.projects.models.project import ProjectHeader
    
    # 获取搜索参数
    ref_number = request.args.get('ref_number', '')
    contact_name = request.args.get('contact_name', '')
    ref_status = request.args.get('ref_status', '')
    payment_status = request.args.get('payment_status', '')
    supplier_name = request.args.get('supplier_name', '')
    departure_filter = request.args.get('departure_filter', '')
    page = request.args.get('page', 1, type=int)

    # 获取所有国家信息
    countries = VisaCountries.query.all()

    # 构建查询 - 按REF分组，获取每个REF的汇总信息
    query = db.session.query(
        ProjectRef,
        ProjectHeader,
        db.func.count(ProjectFlightPassenger.id).label('passenger_count'),
        db.func.sum(ProjectFlightPassenger.selling_price).label('total_selling_price'),
        db.func.sum(ProjectFlightPassenger.cost_price).label('total_cost_price'),
        db.func.min(ProjectFlightSegment.departure_time).label('first_departure_time'),
        db.func.max(ProjectFlightSegment.arrival_time).label('last_arrival_time')
    ).join(
        ProjectHeader, ProjectRef.header_id == ProjectHeader.id
    ).outerjoin(
        ProjectFlightPassenger, ProjectRef.id == ProjectFlightPassenger.ref_id
    ).outerjoin(
        ProjectFlightSegment, ProjectRef.id == ProjectFlightSegment.ref_id
    ).filter(
        ProjectRef.ref_type_id == 1  # 机票业务类型ID
    )
    
    # 根据员工等级过滤订单
    if current_user.role and current_user.role.name == 'staff':
        # 检查用户资料中的员工等级
        staff_level = 1  # 默认等级
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1
        
        if staff_level == 1:
            # 1级员工只能看到自己创建的订单
            query = query.filter(ProjectHeader.staff_name == current_user.username)
        # 2级员工可以看到所有订单，不需要额外过滤
    
    query = query.group_by(
        ProjectRef.id,
        ProjectHeader.id
    )
    
    # 处理出发日期过滤
    today = datetime.now().date()
    if departure_filter == 'today':
        # 今日出发
        query = query.filter(db.func.date(ProjectFlightSegment.departure_time) == today)
    elif departure_filter == 'upcoming':
        # 未来3天内出发
        three_days_later = today + timedelta(days=3)
        query = query.filter(db.func.date(ProjectFlightSegment.departure_time).between(today, three_days_later))
    
    if ref_number:
        query = query.filter(ProjectRef.ref_number.like(f'%{ref_number}%'))
    if contact_name:
        query = query.filter(ProjectRef.contact_name.like(f'%{contact_name}%'))
    
    # 修复订单状态筛选逻辑
    if ref_status and ref_status != 'all':
        # 用户选择了特定的订单状态
        query = query.filter(ProjectRef.status == ref_status)
    elif 'ref_status' not in request.args or request.args.get('ref_status') == '':
        # 如果URL中没有ref_status参数或者参数为空值，应用默认过滤（排除已取消订单）
        query = query.filter(ProjectRef.status != 'cancelled')
    
    if payment_status:
        query = query.filter(ProjectRef.payment_status == payment_status)
    if supplier_name:
        query = query.filter(ProjectRef.supplier.has(name=supplier_name))

    # 获取所有活跃的供应商列表供筛选使用
    suppliers = Supplier.query.filter_by(status='active').all()

    # 按创建时间倒序排序并分页
    results = query.order_by(ProjectRef.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    # 转换数据格式以兼容模板
    orders_data = []
    for result in results.items:
        ref, header, passenger_count, total_selling, total_cost, first_departure_time, last_arrival_time = result
        
        # 获取乘客信息
        passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).all()
        
        # 获取航段信息
        flight_segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).order_by(ProjectFlightSegment.departure_time).all()
        
        # 构建行程信息
        itinerary_parts = []
        for segment in flight_segments:
            itinerary_parts.append(f"{segment.departure_airport}-{segment.arrival_airport}")
        itinerary = '/'.join(itinerary_parts) if itinerary_parts else ''
        
        # 构建订单数据
        order_data = {
            'id': ref.id,
            'order_number': ref.ref_number,  # 使用REF编号作为订单号
            'contact_name': ref.contact_name,
            'contact_person': ref.contact_name,
            'contact_phone': ref.contact_phone,
            'supplier_name': ref.supplier.name if ref.supplier else '',
            'passenger_name': f"{passenger_count}人" if passenger_count else "0人",
            'departure_date': first_departure_time.date() if first_departure_time else None,
            'departure_city': flight_segments[0].departure_airport if flight_segments else '',
            'arrival_city': flight_segments[-1].arrival_airport if flight_segments else '',
            'flight_number': flight_segments[0].flight_number if flight_segments else '',
            'departure_time': first_departure_time,
            'itinerary': itinerary,
            'selling_price': float(total_selling) if total_selling else 0,
            'cost_price': float(total_cost) if total_cost else 0,
            'order_status': ref.status,
            'payment_status': ref.payment_status,
            'status': ref.status,
            'created_date': ref.created_at,
            'remarks': ref.remarks,
            'header': header,
            'ref': ref,
            'passengers': passengers,
            'flight_segments': flight_segments
        }
        orders_data.append(order_data)
    
    # 创建分页对象
    class PaginationWrapper:
        def __init__(self, pagination, items):
            self.items = items
            self.page = pagination.page
            self.per_page = pagination.per_page
            self.total = pagination.total
            self.pages = pagination.pages
            self.has_prev = pagination.has_prev
            self.has_next = pagination.has_next
            self.prev_num = pagination.prev_num
            self.next_num = pagination.next_num
            self.iter_pages = pagination.iter_pages
    
    orders = PaginationWrapper(results, orders_data)
    
    return render_template('business/flight/order_list.html', 
                         orders=orders, 
                         suppliers=suppliers,
                         countries=countries)

@flights_booking.route('/edit_order/<int:order_id>', methods=['GET', 'POST'])
@login_required
@staff_only

def edit_order(order_id):
    """编辑订单（以 ProjectRef.id 作为标识）"""
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.flight.models.flight import ProjectFlightSegment, ProjectFlightPassenger

    # 找到对应的 REF
    ref = ProjectRef.query.get_or_404(order_id)
    header = ProjectHeader.query.get(ref.header_id) if ref.header_id else None

    # 获取供应商列表与类型
    suppliers = Supplier.query.filter_by(status='active').all()
    supplier_types = Supplier.get_supplier_types()

    if request.method == 'POST':
        try:
            # 基本信息
            ref.contact_name = request.form.get('contact_name', ref.contact_name)
            ref.contact_phone = request.form.get('contact_phone', ref.contact_phone)
            ref.contact_email = request.form.get('contact_email', ref.contact_email)
            ref.remarks = request.form.get('remarks', ref.remarks)

            # 供应商更新（按名称选择）
            supplier_name = request.form.get('supplier_name')
            if supplier_name:
                supplier = Supplier.query.filter_by(name=supplier_name).first()
                if supplier:
                    ref.supplier_id = supplier.id

            # 更新乘客：先清空再重建
            ProjectFlightPassenger.query.filter_by(ref_id=ref.id).delete(synchronize_session=False)
            passenger_names = request.form.getlist('passenger_name[]')
            passenger_types_form = request.form.getlist('passenger_type[]')
            selling_prices = request.form.getlist('selling_price[]')
            cost_prices = request.form.getlist('cost_price[]')
            ticket_numbers = request.form.getlist('ticket_number[]')
            pnrs = request.form.getlist('pnr[]')

            for idx, name in enumerate(passenger_names):
                if not name:
                    continue
                passenger = ProjectFlightPassenger(
                    ref_id=ref.id,
                    name=name,
                    passenger_type=(passenger_types_form[idx] if idx < len(passenger_types_form) else 'adult'),
                    selling_price=float(selling_prices[idx]) if idx < len(selling_prices) and selling_prices[idx] else 0,
                    cost_price=float(cost_prices[idx]) if idx < len(cost_prices) and cost_prices[idx] else 0,
                    ticket_number=(ticket_numbers[idx] if idx < len(ticket_numbers) else None),
                    pnr=(pnrs[idx] if idx < len(pnrs) else None)
                )
                db.session.add(passenger)

            # 更新航段：先清空再重建
            ProjectFlightSegment.query.filter_by(ref_id=ref.id).delete(synchronize_session=False)
            flight_numbers = request.form.getlist('flight_number[]')
            cabin_codes = request.form.getlist('cabin_code[]')
            departure_airports = request.form.getlist('departure_airport[]')
            arrival_airports = request.form.getlist('arrival_airport[]')
            departure_times = request.form.getlist('departure_time[]')  # 已由前端合并为 YYYY-MM-DD HH:MM
            arrival_times = request.form.getlist('arrival_time[]')
            cabin_classes = request.form.getlist('cabin_class[]')  # 前端提交的隐藏字段

            for i in range(len(flight_numbers)):
                if not flight_numbers[i]:
                    continue
                # 解析日期时间
                dep_dt = None
                arr_dt = None
                dep_raw = departure_times[i] if i < len(departure_times) else ''
                arr_raw = arrival_times[i] if i < len(arrival_times) else ''
                if dep_raw:
                    try:
                        dep_dt = datetime.strptime(dep_raw, '%Y-%m-%d %H:%M')
                    except ValueError:
                        try:
                            dep_dt = datetime.strptime(dep_raw, '%Y-%m-%dT%H:%M')
                        except ValueError:
                            dep_dt = None
                if arr_raw:
                    try:
                        arr_dt = datetime.strptime(arr_raw, '%Y-%m-%d %H:%M')
                    except ValueError:
                        try:
                            arr_dt = datetime.strptime(arr_raw, '%Y-%m-%dT%H:%M')
                        except ValueError:
                            arr_dt = None

                segment = ProjectFlightSegment(
                    ref_id=ref.id,
                    flight_number=flight_numbers[i],
                    cabin_code=(cabin_codes[i] if i < len(cabin_codes) else None),
                    cabin_class=(cabin_classes[i] if i < len(cabin_classes) else None),
                    departure_airport=(departure_airports[i] if i < len(departure_airports) else None),
                    arrival_airport=(arrival_airports[i] if i < len(arrival_airports) else None),
                    departure_time=dep_dt,
                    arrival_time=arr_dt,
                )
                db.session.add(segment)

            db.session.commit()
            flash('订单已更新', 'success')
            return redirect(url_for('flights_booking.order_detail', order_id=ref.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')

    # 组装编辑页所需数据
    passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).all()
    flight_segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).order_by(ProjectFlightSegment.departure_time).all()

    order = {
        'id': ref.id,
        'order_number': ref.ref_number,
        'contact_name': ref.contact_name,
        'contact_phone': ref.contact_phone,
        'contact_email': ref.contact_email,
        'supplier_name': ref.supplier.name if getattr(ref, 'supplier', None) else '',
        'remarks': ref.remarks,
        'passengers': passengers,
        'flight_segments': flight_segments,
    }

    return render_template(
        'business/flight/order_edit.html',
        order=order,
        suppliers=suppliers,
        supplier_types=supplier_types,
    )

@flights_booking.route('/update_order_status/<int:order_id>', methods=['POST'])
@login_required
@staff_only
def update_order_status(order_id):
    """更新订单状态"""
    try:
        order = FlightOrder.query.get_or_404(order_id)
        new_status = request.form.get('order_status')
        
        # 验证状态值
        valid_statuses = ['pending', 'confirmed', 'ticketed', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'message': '无效的状态值'
            }), 400
            
        # 更新状态
        order.order_status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '状态更新成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@flights_booking.route('/update_payment_status/<int:order_id>', methods=['POST'])
@login_required
@staff_only
def update_payment_status(order_id):
    """更新支付状态"""
    try:
        order = FlightOrder.query.get_or_404(order_id)
        new_status = request.form.get('payment_status')
        
        # 验证状态值
        valid_statuses = ['unpaid', 'paid', 'refunded']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'message': '无效的支付状态值'
            }), 400
            
        # 更新状态
        order.payment_status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '支付状态更新成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@flights_booking.route('/search_airports')
@login_required
@staff_only
def search_airports():
    """搜索机场"""
    query = request.args.get('q', '').strip().upper()
    if not query or len(query) < 2:
        return jsonify([])
        
    # 搜索机场（IATA代码、城市名或机场名）
    airports = AirportData.query.filter(
        db.or_(
            AirportData.airport_IATA.ilike(f'{query}%'),  # IATA代码前缀匹配
            AirportData.city_name.ilike(f'%{query}%'),    # 城市名模糊匹配
            AirportData.airport_name_cn.ilike(f'%{query}%') # 机场名模糊匹配
        )
    ).order_by(
        # IATA代码匹配的优先显示
        db.case(
            (AirportData.airport_IATA.ilike(f'{query}%'), 0),
            else_=1
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': airport.airport_IATA,
        'text': f'{airport.airport_IATA} - {airport.city_name} ({airport.airport_name_cn})'
    } for airport in airports]) 