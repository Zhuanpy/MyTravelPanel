from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.models import FlightOrder, Passenger, FlightSegment, FlightSchedule, AirportData
from App_new.business.projects.models.project import CustomerCompany
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
import re

flights_booking = Blueprint('flights_booking', __name__, url_prefix='/flights_booking')


def get_city_name_en(iata_code):
    """从机场IATA代码获取城市英文名"""
    if not iata_code:
        return iata_code

    iata_code = iata_code.upper().strip()
    airport = AirportData.query.filter_by(airport_IATA=iata_code).first()

    # 优先使用 city_name_en，回退到机场代码
    if airport and airport.city_name_en:
        return airport.city_name_en
    return iata_code

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
    suppliers = CustomerCompany.query.filter(
        CustomerCompany.is_supplier == True,
        CustomerCompany.status == 'active'
    ).order_by(CustomerCompany.company_name).all()
    # 从 BusinessType 表获取供应商类型列表
    from App_new.shared.models.business_types import BusinessType
    supplier_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()
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
        
        # 获取第一个乘客姓名作为联系人（如果存在）
        passenger_names_list = request.form.getlist('passenger_name[]')
        contact_name = passenger_names_list[0] if passenger_names_list else '未设置'
        
        # 2. 自动生成HID和REF
        print("开始生成HID和REF...")
        
        # 获取"个人"公司记录（通过 company_code 查询）
        from App_new.business.projects.models.project import CustomerCompany
        personal_company = CustomerCompany.query.filter_by(company_code='PERSONAL').first()
        if not personal_company:
            # 如果没有找到，尝试通过名称查询
            personal_company = CustomerCompany.query.filter_by(company_name='个人').first()
        if not personal_company:
            flash('未找到"个人"客户公司记录，请先在系统中创建', 'error')
            return redirect(url_for('flights_booking.create_order'))
        
        # 创建项目主表（HID）
        hid = ProjectHeader.generate_hid()
        staff_id_value = current_user.id if current_user else None

        project_header = ProjectHeader(
            hid=hid,
            desc=f"机票订单 - {contact_name} - {first_departure_airport}>{last_arrival_airport}",
            company_id=personal_company.id,
            contact=contact_name,
            staff_id=staff_id_value,
            currency='SGD',
            type='flight',
            status='active',
            remarks=request.form.get('remarks', '')
        )
        # staff_name 已由事件自动同步，设置操作员和业务员默认值
        project_header.operator_ids = str(staff_id_value) if staff_id_value else None
        project_header.operator_names = project_header.staff_name
        project_header.salesperson_ids = str(staff_id_value) if staff_id_value else None
        project_header.salesperson_names = project_header.staff_name
        db.session.add(project_header)
        db.session.flush()  # 获取project_header.id
        print(f"创建项目主表: {hid}")
        
        # 2.0.1 创建项目人员（使用乘客姓名）
        from App_new.business.projects.models.project_member import ProjectMember
        passenger_names_for_members = request.form.getlist('passenger_name[]')
        passenger_types_for_members = request.form.getlist('passenger_type[]')
        
        passenger_type_map = {
            'adult': '成人',
            'child': '儿童',
            'infant': '婴儿'
        }
        
        first_member_added = False
        for idx, pname in enumerate(passenger_names_for_members):
            if pname:
                ptype = passenger_types_for_members[idx] if idx < len(passenger_types_for_members) else 'adult'
                # 第一个有效乘客设置为 leader
                is_leader = not first_member_added
                member = ProjectMember(
                    header_id=project_header.id,
                    member_name=pname,
                    member_role=passenger_type_map.get(ptype, '成人'),
                    is_leader=is_leader,
                    remarks=f'从机票订单自动创建'
                )
                db.session.add(member)
                first_member_added = True
                leader_flag = ' [Leader]' if is_leader else ''
                print(f"创建项目人员: {pname} ({passenger_type_map.get(ptype, '成人')}){leader_flag}")
        
        # 获取机票业务类型（先按code查找，再按name查找）
        flight_business_type = BusinessType.query.filter_by(code='flight').first()
        if not flight_business_type:
            flight_business_type = BusinessType.query.filter_by(name='机票').first()
        if not flight_business_type:
            flight_business_type = BusinessType(
                code='flight',
                name='机票',
                name_en='Flight',
                product_code_prefix='FLT',
                description='航空机票服务',
                is_active=True
            )
            db.session.add(flight_business_type)
            db.session.flush()
        
        # 读取前端供应商字段
        selected_supplier_id = request.form.get('supplier_id')
        # 状态和支付状态字段已从表单中移除，使用默认值
        selected_status = 'confirmed'  # 默认设置为"已确认"
        selected_payment_status = 'unpaid'  # 默认设置为"未付款"

        # 创建项目明细表（REF）
        ref_number = ProjectRef.generate_ref_number()
        
        # 计算总价
        selling_prices = request.form.getlist('selling_price[]')
        cost_prices = request.form.getlist('cost_price[]')
        total_selling_price = sum(float(price) for price in selling_prices if price)
        total_cost_price = sum(float(price) for price in cost_prices if price)
        
        # 生成 description：首末日期 + 机场代码航线
        def generate_flight_description(departure_airports, arrival_airports, departure_times):
            """生成简洁描述：12AUG-15AUG SIN-HKG-SIN"""
            valid_segments = []
            valid_dates = []

            for dep, arr, dep_time in zip(departure_airports, arrival_airports, departure_times):
                if dep and arr and dep_time:
                    valid_segments.append((dep, arr))
                    valid_dates.append(dep_time)

            if not valid_segments or not valid_dates:
                return '机票订单'

            # 格式化首末日期
            try:
                # 处理两种日期格式
                first_time_str = valid_dates[0]
                last_time_str = valid_dates[-1]
                try:
                    first_dt = datetime.strptime(first_time_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    first_dt = datetime.strptime(first_time_str, '%Y-%m-%d %H:%M')
                try:
                    last_dt = datetime.strptime(last_time_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    last_dt = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M')

                first_date = first_dt.strftime('%d%b').upper()
                last_date = last_dt.strftime('%d%b').upper()
                date_str = f"{first_date}-{last_date}" if first_date != last_date else first_date
            except Exception:
                date_str = datetime.now().strftime('%d%b').upper()

            # 构建航线路径（支持 multi-city）
            # 连续航段用 - 连接，不连续（出发地≠上段到达地）用 -- 分隔
            segments_groups = []  # 每组是连续航段的城市列表
            current_group = [valid_segments[0][0]]

            for i, (dep, arr) in enumerate(valid_segments):
                if dep.upper() != current_group[-1].upper():
                    # 出发地与上一组末尾不同，开始新组
                    segments_groups.append('-'.join(current_group))
                    current_group = [dep]
                current_group.append(arr)

            segments_groups.append('-'.join(current_group))
            route_str = '--'.join(segments_groups)

            return f"{date_str} {route_str}"

        # 生成 detailed_description：分行格式
        def generate_flight_detailed_description(flight_nums, dep_airports, arr_airports, dep_times, cabin_codes_list, arr_times):
            """
            生成详细描述（航空公司 Itin 格式）：
            TR 156 02/04/2026 SINGAPORE-SHENYANG  Y  HK  02:50 09:40
            TR 157 17/04/2026 SHENYANG-SINGAPORE  Y  HK  10:55 17:45
            """
            lines = []

            for i, (flight_num, dep, arr, dep_time) in enumerate(zip(flight_nums, dep_airports, arr_airports, dep_times)):
                if not dep or not arr:
                    continue

                # 解析出发时间（日期和时间）
                try:
                    try:
                        dt = datetime.strptime(dep_time, '%Y-%m-%dT%H:%M')
                    except ValueError:
                        dt = datetime.strptime(dep_time, '%Y-%m-%d %H:%M')
                    formatted_date = dt.strftime('%d/%m/%Y')
                    dep_time_str = dt.strftime('%H:%M')
                except (ValueError, TypeError):
                    formatted_date = ''
                    dep_time_str = ''

                # 解析到达时间
                arr_time_str = ''
                if i < len(arr_times) and arr_times[i]:
                    try:
                        try:
                            arr_dt = datetime.strptime(arr_times[i], '%Y-%m-%dT%H:%M')
                        except ValueError:
                            arr_dt = datetime.strptime(arr_times[i], '%Y-%m-%d %H:%M')
                        arr_time_str = arr_dt.strftime('%H:%M')
                    except (ValueError, TypeError):
                        arr_time_str = ''

                # 获取城市英文名并转大写
                dep_city = get_city_name_en(dep).upper()
                arr_city = get_city_name_en(arr).upper()

                # 格式化航班号：在航空公司代码和数字之间添加空格
                flight_num = (flight_num or '').upper().strip()
                match = re.match(r'^([A-Z]{2,3})(\d+)$', flight_num)
                if match:
                    flight_num = f"{match.group(1)} {match.group(2)}"

                # 获取舱位代码
                cabin = cabin_codes_list[i].upper() if i < len(cabin_codes_list) and cabin_codes_list[i] else 'Y'

                # 状态 HK = Holds Confirmed（已确认）
                status = 'HK'
                route = f"{dep_city}-{arr_city}"

                # 格式化：航班号 日期 航线 舱位 状态 出发时间 到达时间
                line_content = f"{flight_num} {formatted_date} {route}  {cabin}  {status}  {dep_time_str} {arr_time_str}"
                lines.append(line_content)

            return '\n'.join(lines) if lines else '机票订单'

        # 取第一个乘客作为出行人(leader_name)
        passenger_names_for_leader = request.form.getlist('passenger_name[]')
        first_passenger_name_for_leader = passenger_names_for_leader[0] if passenger_names_for_leader else contact_name

        # 生成REF描述
        dep_airports_list = request.form.getlist('departure_airport[]')
        arr_airports_list = request.form.getlist('arrival_airport[]')
        dep_times_list = request.form.getlist('departure_time[]')
        arr_times_list = request.form.getlist('arrival_time[]')
        flight_nums_list = request.form.getlist('flight_number[]')
        cabin_codes_list = request.form.getlist('cabin_code[]')

        ref_description = generate_flight_description(dep_airports_list, arr_airports_list, dep_times_list)
        ref_detailed_description = generate_flight_detailed_description(
            flight_nums_list, dep_airports_list, arr_airports_list, dep_times_list,
            cabin_codes_list, arr_times_list
        )

        project_ref = ProjectRef(
            header_id=project_header.id,
            ref_number=ref_number,
            description=ref_description,
            ref_type_id=flight_business_type.id,
            detailed_description=ref_detailed_description,
            supplier_id=int(selected_supplier_id) if selected_supplier_id else None,
            selling_price=total_selling_price,
            cost_price=total_cost_price,
            currency='SGD',
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

        # 统计各类型乘客数量并设置 extra_info
        adult_qty = 0
        child_qty = 0
        infant_qty = 0
        for i, name in enumerate(passenger_names):
            if name:
                pax_type = passenger_types[i] if i < len(passenger_types) and passenger_types[i] else 'adult'
                if pax_type == 'adult':
                    adult_qty += 1
                elif pax_type == 'child':
                    child_qty += 1
                elif pax_type == 'infant':
                    infant_qty += 1

        # 获取操作员和业务员
        operator_name = request.form.get('operator', '')
        salesman_name = request.form.get('salesman', '')

        extra_info = {
            'pax_names_display': ', '.join([name for name in passenger_names if name]),
            'departure_date': departure_dates[0] if departure_dates and departure_dates[0] else '',
            'leader_name': passenger_names[0] if passenger_names else '',
            'flight_route': ref_description,
            'total_passengers': len([name for name in passenger_names if name]),
            'adult_qty': adult_qty,
            'child_qty': child_qty,
            'infant_qty': infant_qty,
            'operator': operator_name,
            'salesman': salesman_name
        }
        project_ref.extra_info = json.dumps(extra_info)

        # 3. 创建订单主表记录
        passenger_names = request.form.getlist('passenger_name[]')
        if not passenger_names:
            raise ValueError("未提供乘客姓名")
            
        # 解析供应商名称（用于订单主表冗余存储显示）
        supplier_name_value = None
        if selected_supplier_id:
            try:
                supplier_obj = CustomerCompany.query.get(int(selected_supplier_id))
                supplier_name_value = supplier_obj.company_name if supplier_obj else None
            except Exception:
                supplier_name_value = None

        order = FlightOrder(
            order_number=generate_order_number(),
            project_header_id=project_header.id,  # 关联HID
            project_ref_id=project_ref.id,        # 关联REF
            contact_name=contact_name,
            contact_person=contact_name,  # 使用第一个乘客姓名作为联系人
            contact_phone='',  # 联系人电话字段已从表单中移除
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
            operator=operator_name,  # 操作员
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

        # 跳转到项目详细页面（根据来源判断跳转目标）
        if request.form.get('from_mobile') == '1':
            # 手机端访问，跳转到手机端项目详情页
            return redirect(url_for('mobile.project_detail', project_id=project_header.id))
        else:
            # PC端访问，跳转到PC端项目详情页
            return redirect(url_for('business_projects.detail.project_detail', project_id=project_header.id))

    except Exception as e:
        db.session.rollback()
        print(f"订单创建失败: {str(e)}")  # 调试日志
        # 回填用户已填写的数据，避免选择项丢失
        try:
            suppliers = CustomerCompany.query.filter(
                CustomerCompany.is_supplier == True,
                CustomerCompany.status == 'active'
            ).order_by(CustomerCompany.company_name).all()
            supplier_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()
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
        'contact_person': ref.header.contact if ref.header else '',
        'contact_phone': '',  # contact_phone 已从 ProjectRef 中移除，如需可从其他地方获取
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
            query = query.filter(ProjectHeader.staff_id == current_user.id)
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
        query = query.filter(ProjectHeader.contact.like(f'%{contact_name}%'))
    
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
    suppliers = CustomerCompany.query.filter(
        CustomerCompany.is_supplier == True,
        CustomerCompany.status == 'active'
    ).order_by(CustomerCompany.company_name).all()

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
            'contact_name': ref.header.contact if ref.header else '',
            'contact_person': ref.header.contact if ref.header else '',
            'contact_phone': '',  # contact_phone 已从 ProjectRef 中移除
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
    suppliers = CustomerCompany.query.filter(
        CustomerCompany.is_supplier == True,
        CustomerCompany.status == 'active'
    ).order_by(CustomerCompany.company_name).all()
    supplier_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()

    if request.method == 'POST':
        try:
            # 基本信息
            # contact_name, contact_phone, contact_email 已从 ProjectRef 中移除
            # 如需更新联系人信息，应更新 ProjectHeader
            if ref.header:
                ref.header.contact = request.form.get('contact_name', ref.header.contact)
            ref.remarks = request.form.get('remarks', ref.remarks)

            # 供应商更新（按名称选择）
            supplier_name = request.form.get('supplier_name')
            if supplier_name:
                supplier = CustomerCompany.query.filter(
                    CustomerCompany.company_name == supplier_name,
                    CustomerCompany.is_supplier == True
                ).first()
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
        'contact_name': ref.header.contact if ref.header else '',
        'contact_phone': '',  # contact_phone 已从 ProjectRef 中移除
        'contact_email': '',  # contact_email 已从 ProjectRef 中移除
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