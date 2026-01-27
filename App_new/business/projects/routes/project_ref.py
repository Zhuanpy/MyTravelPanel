# -*- coding: utf-8 -*-
"""
项目管理REF路由模块
包含各种REF类型的创建、编辑、详情等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.flight.models.flight import ProjectFlightPassenger, ProjectFlightSegment
from App_new.business.flight.models.models import AirportData
from App_new.exts import csrf, db
from App_new.business.projects.models.project import CustomerCompany
from App_new.business.visa.models.Visamodels import VisaCountries
from App_new.shared.models.business_types import BusinessType
from App_new.business.projects.forms.ref_forms import ProjectRefForm
from App_new.utils.decorators import staff_only, admin_only
from App_new.utils.permissions import can_access_project
from datetime import datetime
import traceback
import json
import re

project_ref = Blueprint('project_ref', __name__)


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

@project_ref.route('/general/create/<int:header_id>', methods=['GET', 'POST'])
@login_required
@staff_only
def create_ref(header_id):
    """创建REF"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)
        
        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))
        
        # 检查是否有人员名单
        if header.members.count() == 0:
            flash('请先在人员名单中添加人员后再创建REF', 'warning')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))
        
        form = ProjectRefForm()
        form.header_id.data = header_id
        
        if form.validate_on_submit():
            try:
                # 在应用上下文中生成REF编号
                ref_number = ProjectRef.generate_ref_number("")
                
                # 自动设置REF类型为"其他"
                other_business_type = BusinessType.query.filter_by(name='其他').first()
                if not other_business_type:
                    # 如果"其他"类型不存在，创建一个
                    other_business_type = BusinessType(name='其他', code='other', description='其他服务')
                    db.session.add(other_business_type)
                    db.session.flush()
                
                # 处理描述字段，如果 detailed_description 为空，使用 description
                description = form.description.data or '其他服务'
                detailed_description = form.detailed_description.data or description
                
                ref = ProjectRef(
                    header_id=header.id,
                    ref_number=ref_number,
                    description=description,
                    ref_type_id=other_business_type.id,  # 强制使用"其他"类型
                    detailed_description=detailed_description,
                    supplier_id=form.supplier_id.data if form.supplier_id.data and form.supplier_id.data != 0 else None,
                    selling_price=form.selling_price.data,
                    cost_price=form.cost_price.data,
                    currency='SGD',  # 强制使用新加坡元
                    remarks=form.remarks.data,
                    status='confirmed',  # 强制使用"处理中"
                    payment_status='unpaid'  # 强制使用"未支付"
                )
                db.session.add(ref)
                db.session.flush()  # 获取ref.id
                
                # 处理出行人信息
                if form.passenger_names.data:
                    from App_new.business.flight.models.flight import ProjectFlightPassenger
                    passenger_names = [name.strip() for name in form.passenger_names.data.split(',') if name.strip()]
                    for passenger_name in passenger_names:
                        passenger = ProjectFlightPassenger(
                            ref_id=ref.id,
                            name=passenger_name,
                            passenger_type='adult'  # 默认为成人
                        )
                        db.session.add(passenger)
                
                db.session.commit()
                return redirect(url_for('business_projects.detail.project_detail', project_id=header.id))
            except Exception as e:
                db.session.rollback()
                flash(f'创建失败：{str(e)}', 'error')
        elif form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'error')
        
        # 预填充REF编号
        ref_number = ProjectRef.generate_ref_number("")
        form.ref_number.data = ref_number
        
        # 获取业务类型和供应商数据
        business_types = BusinessType.query.all()
        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
        
        # 设置默认REF类型为"其他"
        other_business_type = BusinessType.query.filter_by(name='其他').first()
        if other_business_type:
            form.ref_type_id.data = other_business_type.id
        
        return render_template('business/projects/project_ref/create_ref.html',
                           form=form, 
                           header=header, 
                           ref_number=ref_number,
                           business_types=business_types,
                           suppliers=suppliers,
                           is_create=True)
    except Exception as e:
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/general/detail/<int:ref_id>', methods=['GET'])
def ref_detail(ref_id):
    """REF详情页面 - 根据业务类型路由到不同详情页"""
    ref = ProjectRef.query.get_or_404(ref_id)

    # 根据业务类型ID路由到不同的详情页面
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None

    if ref_type_name == '机票':
        return redirect(url_for('business_projects.project_ref.flight_ref_detail', ref_id=ref.id))
    elif ref_type_name == '酒店':
        return redirect(url_for('business_projects.project_ref.hotel_ref_detail', ref_id=ref.id))
    elif ref_type_name == '签证':
        return redirect(url_for('business_projects.project_ref.visa_ref_detail', ref_id=ref.id))
    elif ref_type_name == '旅游':
        return redirect(url_for('business_projects.project_ref.tour_ref_detail', ref_id=ref.id))
    elif ref_type_name == '保险':
        return redirect(url_for('business_projects.project_ref.insurance_ref_detail', ref_id=ref.id))
    elif ref_type_name == '交通':
        return redirect(url_for('business_projects.project_ref.transport_ref_detail', ref_id=ref.id))
    else:
        # 其他类型或未分类的REF使用通用详情页面
        return render_template(
            'business/projects/project_ref/ref_detail.html',
            ref=ref,
            ref_type_name=ref_type_name
        )


@project_ref.route('/flight/create/<int:header_id>', methods=['GET'])
@login_required
@staff_only
def create_flight_ref(header_id):
    """创建机票REF页面"""
    header = ProjectHeader.query.get_or_404(header_id)

    # 员工等级权限检查
    if not can_access_project(header, current_user):
        flash('您没有权限访问此项目', 'error')
        return redirect(url_for('business_projects.list.list_projects'))

    # 检查是否有人员名单
    if header.members.count() == 0:
        flash('请先在人员名单中添加人员后再创建REF', 'warning')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    # 获取供应商数据
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
    # 动态获取供应商类型（从 BusinessType 表）
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

    return render_template('business/projects/project_ref/create_flight_ref.html',
                        header_id=header_id,
                        suppliers=suppliers,
                        supplier_types=supplier_types)


@project_ref.route('/flight/submit', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def submit_flight_ref():
    """提交机票REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)

            # 检查是否有已付款的EO
            if ref.has_paid_eo():
                flash('此REF的EO已付款，不能编辑', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

            # 记录旧的成本价格（用于调整预付账款）
            old_cost = ref.cost_price

            # 更新REF基本信息
            ref.description = '机票订单'
            ref.detailed_description = '机票订单'
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                'supplier_id') != '0' else None
            ref.remarks = request.form.get('remarks')
            # 状态和支付状态字段已从表单中移除，保持现有值不变
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")

            # 获取机票业务类型ID
            flight_business_type = BusinessType.query.filter_by(name='机票').first()
            if not flight_business_type:
                flash('未找到机票业务类型，请先创建', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

            # 生成基于航段信息的名称
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                description='机票订单',
                ref_type_id=flight_business_type.id,
                detailed_description='机票订单',
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                    'supplier_id') != '0' else None,
                remarks=request.form.get('remarks'),
                status='confirmed',  # 默认设置为"处理中"
                payment_status='unpaid'  # 默认设置为"未付款"
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

        # 扩展较短的列
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

        # 更新REF级别的总价
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

        # 生成 description：首末日期 + 机场代码航线
        def generate_flight_description(departure_airports, arrival_airports, departure_dates):
            """
            生成简洁描述：12AUG-15AUG SIN-HKG-SIN
            """
            if not departure_airports or not arrival_airports or not departure_dates:
                return '机票订单'

            valid_segments = []
            valid_dates = []

            for dep, arr, date in zip(departure_airports, arrival_airports, departure_dates):
                if dep and arr and date:
                    valid_segments.append((dep, arr))
                    valid_dates.append(date)

            if not valid_segments or not valid_dates:
                return '机票订单'

            # 格式化首末日期
            try:
                first_date = datetime.strptime(valid_dates[0], '%Y-%m-%d').strftime('%d%b').upper()
                last_date = datetime.strptime(valid_dates[-1], '%Y-%m-%d').strftime('%d%b').upper()
                date_str = f"{first_date}-{last_date}" if first_date != last_date else first_date
            except ValueError:
                date_str = valid_dates[0]

            # 构建航线路径
            route_parts = [valid_segments[0][0]]
            for dep, arr in valid_segments:
                if arr not in route_parts or arr == valid_segments[-1][1]:
                    route_parts.append(arr)

            return f"{date_str} {'-'.join(route_parts)}"

        # 生成 detailed_description：分行格式
        def generate_flight_detailed_description(flight_nums, dep_airports, arr_airports, dep_dates,
                                                  cabin_codes_list, dep_times, arr_times):
            """
            生成详细描述（航空公司 Itin 格式）：
            TR 156 02/04/2026 SINGAPORE-SHENYANG  Y  HK  02:50 09:40
            TR 157 17/04/2026 SHENYANG-SINGAPORE  Y  HK  10:55 17:45
            """
            lines = []

            for i, (flight_num, dep, arr, dep_date) in enumerate(zip(flight_nums, dep_airports, arr_airports, dep_dates)):
                if not dep or not arr:
                    continue

                # 格式化日期为 DD/MM/YYYY
                try:
                    formatted_date = datetime.strptime(dep_date, '%Y-%m-%d').strftime('%d/%m/%Y')
                except (ValueError, TypeError):
                    formatted_date = dep_date or ''

                # 获取城市英文名并转大写
                dep_city = get_city_name_en(dep).upper()
                arr_city = get_city_name_en(arr).upper()

                # 格式化航班号：在航空公司代码和数字之间添加空格
                flight_num = (flight_num or '').upper().strip()
                # 分离航空公司代码和航班数字（假设前2-3位是航空公司代码）
                match = re.match(r'^([A-Z]{2,3})(\d+)$', flight_num)
                if match:
                    flight_num = f"{match.group(1)} {match.group(2)}"

                # 获取舱位代码
                cabin = cabin_codes_list[i].upper() if i < len(cabin_codes_list) and cabin_codes_list[i] else 'Y'

                # 获取出发和到达时间
                dep_time_str = dep_times[i] if i < len(dep_times) and dep_times[i] else ''
                arr_time_str = arr_times[i] if i < len(arr_times) and arr_times[i] else ''

                # 构建行内容
                # 状态 HK = Holds Confirmed（已确认）
                status = 'HK'
                route = f"{dep_city}-{arr_city}"

                # 格式化：航班号 日期 航线 舱位 状态 出发时间 到达时间
                line_content = f"{flight_num} {formatted_date} {route}  {cabin}  {status}  {dep_time_str} {arr_time_str}"
                lines.append(line_content)

            return '\n'.join(lines) if lines else '机票订单'

        # 检查是否有有效的航段数据提交（至少有一个航段有出发日期）
        has_valid_segment_data = any(
            departure_dates[i] for i in range(len(departure_dates)) if i < len(departure_dates)
        )

        # 只有当有有效航段数据时才更新航段，否则保留原有航段
        if has_valid_segment_data:
            # 生成并更新描述
            ref.description = generate_flight_description(departure_airports, arrival_airports, departure_dates)
            ref.detailed_description = generate_flight_detailed_description(
                flight_numbers, departure_airports, arrival_airports, departure_dates,
                cabin_codes, departure_times, arrival_times
            )

            # 删除现有航段
            ProjectFlightSegment.query.filter_by(ref_id=ref.id).delete()

            # 安全处理航段信息 - 确保所有字段长度一致
            max_segment_len = max(len(flight_numbers), len(cabin_codes), len(departure_airports),
                                  len(arrival_airports), len(departure_dates), len(departure_times),
                                  len(arrival_dates), len(arrival_times))

            # 扩展较短的列
            cabin_codes.extend([''] * (max_segment_len - len(cabin_codes)))
            departure_airports.extend([''] * (max_segment_len - len(departure_airports)))
            arrival_airports.extend([''] * (max_segment_len - len(arrival_airports)))
            departure_dates.extend([''] * (max_segment_len - len(departure_dates)))
            departure_times.extend([''] * (max_segment_len - len(departure_times)))
            arrival_dates.extend([''] * (max_segment_len - len(arrival_dates)))
            arrival_times.extend([''] * (max_segment_len - len(arrival_times)))

            # 添加新航段
            for i in range(len(flight_numbers)):
                # 跳过没有出发日期的航段
                if not departure_dates[i]:
                    continue
                try:
                    dep_date = departure_dates[i]
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

        # 统计各类型乘客数量
        adult_qty = 0
        child_qty = 0
        infant_qty = 0
        for i, name in enumerate(passenger_names):
            if name:
                pax_type = passenger_types[i] if i < len(passenger_types) else 'adult'
                if pax_type == 'adult':
                    adult_qty += 1
                elif pax_type == 'child':
                    child_qty += 1
                elif pax_type == 'infant':
                    infant_qty += 1

        # 同步到extra_info，便于发票统一打印
        extra_info = {
            'pax_names_display': ', '.join([name for name in passenger_names if name]),  # 乘客姓名列表
            'departure_date': departure_dates[0] if departure_dates and departure_dates[0] else '',  # 第一个航段的出发日期
            'leader_name': request.form.get('leader_name', passenger_names[0] if passenger_names else ''),
            'flight_route': ref.description,  # 航线描述
            'total_passengers': len([name for name in passenger_names if name]),
            'adult_qty': adult_qty,
            'child_qty': child_qty,
            'infant_qty': infant_qty
        }
        ref.extra_info = json.dumps(extra_info)

        # 如果是编辑，调整预付账款（如果cost_price变化）
        prepayment_msg = ''
        if ref_id:
            prepayment_msg = ref.adjust_prepayment_for_cost_change(old_cost)

        db.session.commit()

        if prepayment_msg:
            flash(f'机票REF保存成功！{prepayment_msg}', 'success')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))


# 酒店REF相关函数
@project_ref.route('/hotel/create/<int:header_id>', methods=['GET'])
@login_required
@staff_only
def create_hotel_ref(header_id):
    """创建酒店REF页面"""
    try:
        from flask import current_app
        if not current_app:
            flash('应用上下文错误，请刷新页面重新操作', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        header = ProjectHeader.query.get_or_404(header_id)

        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 检查是否有人员名单
        if header.members.count() == 0:
            flash('请先在人员名单中添加人员后再创建REF', 'warning')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
        supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]
        
        # 获取项目人员列表
        from App_new.business.projects.models.project_member import ProjectMember
        members = ProjectMember.query.filter_by(header_id=header_id).order_by(ProjectMember.id).all()
    
        return render_template('business/projects/project_ref/create_hotel_ref.html', 
                        header_id=header_id,
                        header=header,
                        suppliers=suppliers,
                        supplier_types=supplier_types,
                        members=members,
                        has_invoice=False)
    except Exception as e:
        import traceback
        print(f"酒店REF创建页面加载失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/hotel/submit', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def submit_hotel_ref():
    """提交酒店REF数据"""
    try:
        # 确保在应用上下文中运行
        from flask import current_app
        if not current_app:
            flash('应用上下文错误，请刷新页面重试', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 检查是否有前端发送的完整extra_info JSON（新版per-room-per-night定价模式）
        extra_info_json = request.form.get('extra_info')
        if extra_info_json:
            try:
                extra_info = json.loads(extra_info_json)
            except json.JSONDecodeError:
                extra_info = {}
        else:
            # 回退到旧版：从单独字段构建extra_info
            pax_names = request.form.getlist('pax_names')
            pax_names = [int(x) for x in pax_names if x]
            leader_id = request.form.get('leader_id')
            leader_id = int(leader_id) if leader_id else None

            extra_info = {
                'hotel_name': request.form.get('hotel_name', ''),
                'checkin_date': request.form.get('checkin_date', ''),
                'checkout_date': request.form.get('checkout_date', ''),
                'room_type': request.form.get('room_type', ''),
                'pax_names': pax_names,
                'leader_id': leader_id,
                'pax_name': request.form.get('pax_name', ''),
                'departure_date': request.form.get('checkin_date', ''),
                'remarks': request.form.get('remarks', ''),
            }
        
        # 获取总售价和总成本（从隐藏字段或计算得出）
        selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
        cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
        
        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            # 更新REF基本信息
            ref.description = request.form.get('description', '酒店订单')
            ref.detailed_description = request.form.get('detailed_description', '酒店订单')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                'supplier_id') != '0' else None
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'confirmed')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
            ref.selling_price = selling_price
            ref.cost_price = cost_price
            ref.extra_info = json.dumps(extra_info)
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)

            try:
                ref_number = ProjectRef.generate_ref_number("")
            except Exception as e:
                print(f"生成REF编号失败: {e}")
                # 如果生成失败，使用默认编号
                ref_number = "R01"

            # 获取酒店业务类型ID
            hotel_business_type = BusinessType.query.filter_by(name='酒店').first()
            if not hotel_business_type:
                flash('未找到酒店业务类型，请先创建', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                description=request.form.get('description', '酒店订单'),
                ref_type_id=hotel_business_type.id,
                detailed_description=request.form.get('detailed_description', '酒店订单'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                    'supplier_id') != '0' else None,
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'confirmed'),
                payment_status=request.form.get('payment_status', 'unpaid'),
                selling_price=selling_price,
                cost_price=cost_price,
                extra_info=json.dumps(extra_info)
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id

        db.session.commit()
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    except Exception as e:
        import traceback
        print(f"酒店REF提交失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))


@project_ref.route('/hotel/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_hotel_ref(ref_id):
    """编辑酒店REF"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是酒店类型的REF
    business_type = BusinessType.query.get(ref.ref_type_id)
    if not business_type or business_type.name != '酒店':
        flash('只能编辑酒店类型的REF', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 检查是否有前端发送的完整extra_info JSON（新版per-room-per-night定价模式）
            extra_info_json = request.form.get('extra_info')
            if extra_info_json:
                try:
                    extra_info = json.loads(extra_info_json)
                except json.JSONDecodeError:
                    extra_info = {}
            else:
                # 回退到旧版：从单独字段构建extra_info
                pax_names = request.form.getlist('pax_names')
                pax_names = [int(x) for x in pax_names if x]
                leader_id = request.form.get('leader_id')
                leader_id = int(leader_id) if leader_id else None

                extra_info = {
                    'hotel_name': request.form.get('hotel_name', ''),
                    'checkin_date': request.form.get('checkin_date', ''),
                    'checkout_date': request.form.get('checkout_date', ''),
                    'room_type': request.form.get('room_type', ''),
                    'pax_names': pax_names,
                    'leader_id': leader_id,
                    'pax_name': request.form.get('pax_name', ''),
                    'departure_date': request.form.get('checkin_date', ''),
                    'remarks': request.form.get('remarks', ''),
                }
            
            # 获取总售价和总成本（从隐藏字段或计算得出）
            selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            
            # 更新REF数据
            ref.description = request.form.get('description', '酒店订单')
            ref.detailed_description = request.form.get('detailed_description', '酒店订单')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'confirmed')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
            ref.selling_price = selling_price
            ref.cost_price = cost_price
            ref.extra_info = json.dumps(extra_info)
            
            db.session.commit()
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    # GET请求 - 显示编辑页面
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]
    
    # 获取项目人员列表
    from App_new.business.projects.models.project_member import ProjectMember
    members = ProjectMember.query.filter_by(header_id=ref.header_id).order_by(ProjectMember.id).all()
    
    # 解析extra_info
    extra_info = None
    if ref.extra_info:
        try:
            extra_info = json.loads(ref.extra_info)
        except (json.JSONDecodeError, TypeError):
            extra_info = None
    
    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查关联的EO是否已付款（排除已取消的）
    eo_paid = False
    if ref.eos and ref.eos.status not in ['void', 'cancelled']:
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    header = ProjectHeader.query.get(ref.header_id)

    return render_template('business/projects/project_ref/create_hotel_ref.html',
                         header_id=ref.header_id,
                         header=header,
                         ref_id=ref.id,
                         ref=ref,
                         suppliers=suppliers,
                         supplier_types=supplier_types,
                         members=members,
                         extra_info=extra_info,
                         is_create=False,
                         has_invoice=has_invoice,
                         eo_paid=eo_paid)


# 签证REF相关函数
@project_ref.route('/visa/create/<int:header_id>', methods=['GET'])
@login_required
@staff_only
def create_visa_ref(header_id):
    """创建签证REF页面"""
    try:
        # 确保在应用上下文中运行
        from flask import current_app
        if not current_app:
            flash('应用上下文错误，请刷新页面重新操作', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        header = ProjectHeader.query.get_or_404(header_id)

        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 检查是否有人员名单
        if header.members.count() == 0:
            flash('请先在人员名单中添加人员后再创建REF', 'warning')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))
    
            # 获取供应商数据（按名称排序）
        from sqlalchemy import func
        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).order_by(func.lower(CustomerCompany.company_name)).all()
        supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

        countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()

        # 获取项目人员列表
        from App_new.business.projects.models.project_member import ProjectMember
        members = ProjectMember.query.filter_by(header_id=header_id).order_by(ProjectMember.id).all()

        return render_template('business/projects/project_ref/create_visa_ref.html',
                             header_id=header_id,
                             header=header,
                             suppliers=suppliers,
                             supplier_types=supplier_types,
                             countries=countries,
                             members=members,
                             extra_info=None,
                             visa_info=None,
                             is_create=True,
                             has_invoice=False)
    except Exception as e:
        import traceback
        print(f"签证REF创建页面加载失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))

@project_ref.route('/visa/submit', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def submit_visa_ref():
    """提交签证REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 检查是否有前端发送的完整extra_info JSON
        extra_info_json = request.form.get('extra_info')
        if extra_info_json:
            try:
                extra_info = json.loads(extra_info_json)
            except json.JSONDecodeError:
                extra_info = {}
        else:
            # 回退到旧版：从单独字段构建extra_info
            pax_names = request.form.getlist('pax_names')
            pax_names = [int(x) for x in pax_names if x]
            leader_id = request.form.get('leader_id')
            leader_id = int(leader_id) if leader_id else None

            extra_info = {
                'visa_name': request.form.get('visa_name', ''),
                'country': request.form.get('country', ''),
                'visa_type': request.form.get('visa_type', ''),
                'pax_names': pax_names,
                'leader_id': leader_id,
                'departure_date': request.form.get('departure_date', ''),
                'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                'child_qty': int(request.form.get('child_qty', 0) or 0),
                'child_selling': float(request.form.get('child_selling', 0) or 0),
                'child_cost': float(request.form.get('child_cost', 0) or 0),
                'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                'infant_cost': float(request.form.get('infant_cost', 0) or 0),
            }

        # 基于 extra_info 生成英文 description（确保格式正确）
        country = extra_info.get('country', '')
        visa_type = extra_info.get('visa_type', '')
        departure_date = extra_info.get('departure_date', '')

        if country and visa_type:
            description_generated = f"{country} {visa_type} VISA"
        elif country:
            description_generated = f"{country} VISA"
        elif visa_type:
            description_generated = f"{visa_type} VISA"
        else:
            description_generated = 'VISA APPLICATION'

        # 如果有出发日期，添加到 description
        if departure_date:
            description_generated += f" | {departure_date}"

        # 使用前端传的值，如果为空则使用生成的
        description = request.form.get('description') or description_generated
        detailed_description = request.form.get('detailed_description') or description

        # 生成 pax_names_display
        pax_names = extra_info.get('pax_names', [])
        if pax_names:
            from App_new.business.projects.models.project_member import ProjectMember
            pax_ids = [int(pid) for pid in pax_names if pid]
            if pax_ids:
                members = ProjectMember.query.filter(ProjectMember.id.in_(pax_ids)).all()
                pax_names_list = [f"{m.title} {m.member_name}" if m.title else m.member_name for m in members]
                extra_info['pax_names_display'] = ', '.join(pax_names_list)

        # 获取总售价和总成本
        selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0
        cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            ref.description = description
            ref.detailed_description = detailed_description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'confirmed')
            ref.selling_price = selling_price
            ref.cost_price = cost_price
            ref.extra_info = json.dumps(extra_info, ensure_ascii=False)
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")

            # 获取签证业务类型ID
            visa_business_type = BusinessType.query.filter_by(code='visa').first()
            if not visa_business_type:
                visa_business_type = BusinessType.query.filter_by(name='签证').first()
            if not visa_business_type:
                flash('Visa business type not found', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                description=description,
                ref_type_id=visa_business_type.id,
                detailed_description=detailed_description,
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None,
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'confirmed'),
                payment_status='unpaid',
                selling_price=selling_price,
                cost_price=cost_price,
                extra_info=json.dumps(extra_info, ensure_ascii=False)
            )
            db.session.add(ref)

        db.session.commit()
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

# 旅游团REF相关函数
@project_ref.route('/tour/create/<int:header_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@staff_only
def create_tour_ref(header_id):
    """创建旅游团REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 检查是否有人员名单
        if header.members.count() == 0:
            flash('请先在人员名单中添加人员后再创建REF', 'warning')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

        if request.method == 'POST':
            # 处理POST请求 - 创建旅游团REF
            try:
                import json
                ref_number = ProjectRef.generate_ref_number("")

                # 获取旅游团业务类型ID（优先按code查询，避免名称差异导致ID不一致）
                tour_business_type = BusinessType.query.filter_by(code='tour').first()
                if not tour_business_type:
                    tour_business_type = BusinessType.query.filter_by(name='旅游团').first()
                if not tour_business_type:
                    flash('未找到旅游团业务类型，请先创建', 'error')
                    return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

                # 获取团名作为描述
                tour_name = request.form.get('tour_name', '旅游团订购')
                
                # 构建 extra_info 数据
                extra_info = {
                    'tour_name': tour_name,
                    'departure_date': request.form.get('departure_date', ''),
                    'end_date': request.form.get('end_date', ''),
                    'itinerary': request.form.get('itinerary', ''),
                    'pax_names': request.form.getlist('pax_names'),
                    'leader_id': request.form.get('leader_id', ''),
                    # Pricing 信息
                    'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                    'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                    'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                    'child_qty': int(request.form.get('child_qty', 0) or 0),
                    'child_selling': float(request.form.get('child_selling', 0) or 0),
                    'child_cost': float(request.form.get('child_cost', 0) or 0),
                    'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                    'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                    'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                    # 单房差
                    'single_room_qty': int(request.form.get('single_room_qty', 0) or 0),
                    'single_room_selling': float(request.form.get('single_room_selling', 0) or 0),
                    'single_room_cost': float(request.form.get('single_room_cost', 0) or 0),
                }
                
                # 生成 pax_names_display
                from App_new.business.projects.models.project_member import ProjectMember
                pax_ids = [int(pid) for pid in extra_info['pax_names'] if pid]
                if pax_ids:
                    members = ProjectMember.query.filter(ProjectMember.id.in_(pax_ids)).all()
                    pax_names_list = [f"{m.title} {m.member_name}" if m.title else m.member_name for m in members]
                    extra_info['pax_names_display'] = ', '.join(pax_names_list)

                ref = ProjectRef(
                    header_id=header.id,
                    ref_number=ref_number,
                    description=tour_name,
                    ref_type_id=tour_business_type.id,
                    detailed_description=request.form.get('itinerary', tour_name),
                    supplier_id=(
                        request.form.get('supplier_id')
                        if request.form.get('supplier_id') and request.form.get('supplier_id') != '0'
                        else None
                    ),
                    remarks=request.form.get('remarks'),
                    status=request.form.get('status', 'confirmed'),
                    payment_status='unpaid',
                    selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0,
                    cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0,
                    extra_info=json.dumps(extra_info, ensure_ascii=False)
                )
                db.session.add(ref)
                db.session.commit()

                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

            except Exception as e:
                db.session.rollback()
                import traceback
                traceback.print_exc()
                flash(f'创建失败：{str(e)}', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

        # GET请求 - 显示创建页面
        from sqlalchemy import func
        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).order_by(func.lower(CustomerCompany.company_name)).all()
        supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

        # 获取项目成员
        from App_new.business.projects.models.project_member import ProjectMember
        members = ProjectMember.query.filter_by(header_id=header_id).all()

        return render_template('business/projects/project_ref/create_tour_ref.html',
                             header_id=header_id,
                             header=header,
                             suppliers=suppliers,
                             supplier_types=supplier_types,
                             members=members,
                             extra_info=None,
                             is_create=True,
                             has_invoice=False)
    except Exception as e:
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/tour/submit', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def submit_tour_ref():
    """提交旅游团REF数据"""
    try:
        import json
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 检查是否有前端发送的完整extra_info JSON
        extra_info_json = request.form.get('extra_info')
        if extra_info_json:
            try:
                extra_info = json.loads(extra_info_json)
            except json.JSONDecodeError:
                extra_info = {}
        else:
            # 回退到旧版：从单独字段构建extra_info
            tour_name = request.form.get('tour_name', 'Tour Booking')
            extra_info = {
                'tour_name': tour_name,
                'departure_date': request.form.get('departure_date', ''),
                'end_date': request.form.get('end_date', ''),
                'itinerary': request.form.get('itinerary', ''),
                'pax_names': request.form.getlist('pax_names'),
                'leader_id': request.form.get('leader_id', ''),
                'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                'child_qty': int(request.form.get('child_qty', 0) or 0),
                'child_selling': float(request.form.get('child_selling', 0) or 0),
                'child_cost': float(request.form.get('child_cost', 0) or 0),
                'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                # 单房差
                'single_room_qty': int(request.form.get('single_room_qty', 0) or 0),
                'single_room_selling': float(request.form.get('single_room_selling', 0) or 0),
                'single_room_cost': float(request.form.get('single_room_cost', 0) or 0),
            }

        # 获取描述字段（前端自动生成）
        description = request.form.get('description', extra_info.get('tour_name', 'Tour Booking'))
        detailed_description = request.form.get('detailed_description', description)

        # 生成 pax_names_display
        from App_new.business.projects.models.project_member import ProjectMember
        pax_ids = [int(pid) for pid in extra_info.get('pax_names', []) if pid]
        if pax_ids:
            members = ProjectMember.query.filter(ProjectMember.id.in_(pax_ids)).all()
            pax_names_list = [f"{m.title} {m.member_name}" if m.title else m.member_name for m in members]
            extra_info['pax_names_display'] = ', '.join(pax_names_list)

        # 获取总售价和总成本
        selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0
        cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            ref.description = description
            ref.detailed_description = detailed_description
            ref.supplier_id = (
                request.form.get('supplier_id')
                if request.form.get('supplier_id') and request.form.get('supplier_id') != '0'
                else None
            )
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'confirmed')
            ref.selling_price = selling_price
            ref.cost_price = cost_price
            ref.extra_info = json.dumps(extra_info, ensure_ascii=False)
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")

            # 获取旅游团业务类型ID
            tour_business_type = BusinessType.query.filter_by(code='tour').first()
            if not tour_business_type:
                tour_business_type = BusinessType.query.filter_by(name='旅游团').first()
            if not tour_business_type:
                flash('Tour business type not found', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                ref_type_id=tour_business_type.id,
                description=description,
                detailed_description=detailed_description,
                supplier_id=(
                    request.form.get('supplier_id')
                    if request.form.get('supplier_id') and request.form.get('supplier_id') != '0'
                    else None
                ),
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'confirmed'),
                payment_status='unpaid',
                selling_price=selling_price,
                cost_price=cost_price,
                extra_info=json.dumps(extra_info, ensure_ascii=False)
            )
            db.session.add(ref)

        db.session.commit()
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))


# 保险REF相关函数
@project_ref.route('/insurance/create/<int:header_id>', methods=['GET'])
@login_required
@staff_only
def create_insurance_ref(header_id):
    """创建保险REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 检查是否有人员名单
        if header.members.count() == 0:
            flash('请先在人员名单中添加人员后再创建REF', 'warning')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

        # 获取供应商数据
        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
        supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

        # 获取项目成员
        from App_new.business.projects.models.project_member import ProjectMember
        members = ProjectMember.query.filter_by(header_id=header_id).order_by(ProjectMember.id).all()

        return render_template('business/projects/project_ref/create_insurance_ref.html',
                             header_id=header_id,
                             suppliers=suppliers,
                             supplier_types=supplier_types,
                             members=members,
                             extra_info=None,
                             is_create=True,
                             has_invoice=False)
    except Exception as e:
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))

@project_ref.route('/insurance/submit', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def submit_insurance_ref():
    """提交保险REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 检查是否有前端发送的完整extra_info JSON
        extra_info_json = request.form.get('extra_info')
        if extra_info_json:
            try:
                extra_info = json.loads(extra_info_json)
            except json.JSONDecodeError:
                extra_info = {}
        else:
            # 回退到旧版：从单独字段构建extra_info
            extra_info = {
                'insurance_type': request.form.get('insurance_type', ''),
                'policy_number': request.form.get('policy_number', ''),
                'start_date': request.form.get('start_date', ''),
                'end_date': request.form.get('end_date', ''),
                'days': int(request.form.get('days', 0) or 0),
                'pax_names': request.form.getlist('pax_names'),
                'leader_id': request.form.get('leader_id', ''),
                'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                'child_qty': int(request.form.get('child_qty', 0) or 0),
                'child_selling': float(request.form.get('child_selling', 0) or 0),
                'child_cost': float(request.form.get('child_cost', 0) or 0),
                'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                'infant_cost': float(request.form.get('infant_cost', 0) or 0),
            }

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            # 更新REF基本信息
            description = request.form.get('description')
            if not description:
                description = ref.description or 'Insurance'
            ref.description = description
            ref.detailed_description = request.form.get('detailed_description', description)
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'confirmed')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            ref.extra_info = json.dumps(extra_info)
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")

            # 获取保险业务类型ID
            insurance_business_type = BusinessType.query.filter_by(name='保险').first()
            if not insurance_business_type:
                flash('未找到保险业务类型，请先创建', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

            description = request.form.get('description')
            if not description:
                description = 'Insurance'
            detailed_description = request.form.get('detailed_description', description)

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                description=description,
                ref_type_id=insurance_business_type.id,
                detailed_description=detailed_description,
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None,
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'confirmed'),
                payment_status=request.form.get('payment_status', 'unpaid'),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None,
                extra_info=json.dumps(extra_info)
            )
            db.session.add(ref)

        db.session.commit()
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

# 交通REF相关函数
@project_ref.route('/transport/create/<int:header_id>', methods=['GET'])
@login_required
@staff_only
def create_transport_ref(header_id):
    """创建交通REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 检查是否有人员名单
        if header.members.count() == 0:
            flash('请先在人员名单中添加人员后再创建REF', 'warning')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

        # 获取供应商数据（按名称排序）
        from sqlalchemy import func
        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).order_by(func.lower(CustomerCompany.company_name)).all()
        supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

        # 获取项目人员列表
        from App_new.business.projects.models.project_member import ProjectMember
        members = ProjectMember.query.filter_by(header_id=header_id).order_by(ProjectMember.id).all()

        return render_template('business/projects/project_ref/create_transport_ref.html',
                             header_id=header_id,
                             header=header,
                             suppliers=suppliers,
                             supplier_types=supplier_types,
                             members=members,
                             extra_info=None,
                             is_create=True,
                             has_invoice=False)
    except Exception as e:
        import traceback
        print(f"交通REF创建页面加载失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/transport/submit', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def submit_transport_ref():
    """提交交通REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 检查是否有前端发送的完整extra_info JSON
        extra_info_json = request.form.get('extra_info')
        if extra_info_json:
            try:
                extra_info = json.loads(extra_info_json)
            except json.JSONDecodeError:
                extra_info = {}
        else:
            # 回退到旧版：从单独字段构建extra_info
            pax_names = request.form.getlist('pax_names')
            pax_names = [int(x) for x in pax_names if x]
            leader_id = request.form.get('leader_id')
            leader_id = int(leader_id) if leader_id else None

            extra_info = {
                'transport_type': request.form.get('transport_type', ''),
                'start_point': request.form.get('start_point', ''),
                'end_point': request.form.get('end_point', ''),
                'departure_date': request.form.get('departure_date', ''),
                'departure_time': request.form.get('departure_time', ''),
                'confirmation_number': request.form.get('confirmation_number', ''),
                'pax_names': pax_names,
                'leader_id': leader_id,
                'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                'child_qty': int(request.form.get('child_qty', 0) or 0),
                'child_selling': float(request.form.get('child_selling', 0) or 0),
                'child_cost': float(request.form.get('child_cost', 0) or 0),
                'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                'infant_cost': float(request.form.get('infant_cost', 0) or 0),
            }

        # 获取description和detailed_description from frontend
        description = request.form.get('description', '').strip()
        detailed_description = request.form.get('detailed_description', '').strip()

        if not description:
            description = 'Transport'

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            ref.description = description
            ref.detailed_description = detailed_description or description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'confirmed')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0
            ref.extra_info = json.dumps(extra_info, ensure_ascii=False)
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")

            # 获取交通业务类型ID
            transport_business_type = BusinessType.query.filter_by(code='transport').first()
            if not transport_business_type:
                transport_business_type = BusinessType.query.filter_by(name='交通').first()
            if not transport_business_type:
                transport_business_type = BusinessType.query.filter_by(code='transfer').first()
            if not transport_business_type:
                transport_business_type = BusinessType(
                    code='transport',
                    name='交通',
                    description='交通服务',
                    sort_order=6,
                    is_active=True
                )
                db.session.add(transport_business_type)
                db.session.flush()

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                description=description,
                ref_type_id=transport_business_type.id,
                detailed_description=detailed_description or description,
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None,
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'confirmed'),
                payment_status='unpaid',
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0,
                extra_info=json.dumps(extra_info, ensure_ascii=False)
            )
            db.session.add(ref)

        db.session.commit()
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))


@project_ref.route('/transport/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_transport_ref(ref_id):
    """编辑交通REF"""
    ref = ProjectRef.query.get_or_404(ref_id)

    # 确保这是交通类型的REF
    business_type = BusinessType.query.get(ref.ref_type_id)
    if not business_type or (business_type.code not in ['transport', 'transfer'] and business_type.name != '交通'):
        flash('只能编辑交通类型的REF', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

    if request.method == 'POST':
        try:
            # 检查是否有前端发送的完整extra_info JSON
            extra_info_json = request.form.get('extra_info')
            if extra_info_json:
                try:
                    extra_info = json.loads(extra_info_json)
                except json.JSONDecodeError:
                    extra_info = {}
            else:
                # 回退到旧版：从单独字段构建extra_info
                pax_names = request.form.getlist('pax_names')
                pax_names = [int(x) for x in pax_names if x]
                leader_id = request.form.get('leader_id')
                leader_id = int(leader_id) if leader_id else None

                extra_info = {
                    'transport_type': request.form.get('transport_type', ''),
                    'start_point': request.form.get('start_point', ''),
                    'end_point': request.form.get('end_point', ''),
                    'departure_date': request.form.get('departure_date', ''),
                    'departure_time': request.form.get('departure_time', ''),
                    'confirmation_number': request.form.get('confirmation_number', ''),
                    'pax_names': pax_names,
                    'leader_id': leader_id,
                    'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                    'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                    'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                    'child_qty': int(request.form.get('child_qty', 0) or 0),
                    'child_selling': float(request.form.get('child_selling', 0) or 0),
                    'child_cost': float(request.form.get('child_cost', 0) or 0),
                    'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                    'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                    'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                }

            # 获取description和detailed_description from frontend
            description = request.form.get('description', '').strip()
            detailed_description = request.form.get('detailed_description', '').strip()

            if not description:
                description = ref.description or 'Transport'

            ref.description = description
            ref.detailed_description = detailed_description or description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0
            ref.status = request.form.get('status') or 'confirmed'
            ref.remarks = request.form.get('remarks', '')
            ref.extra_info = json.dumps(extra_info, ensure_ascii=False)

            db.session.commit()
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

    # 获取供应商数据（按名称排序）
    from sqlalchemy import func
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).order_by(func.lower(CustomerCompany.company_name)).all()
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

    # 解析交通专属信息
    extra_info = {}
    if ref and ref.extra_info:
        try:
            extra_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            extra_info = {}

    # 获取项目人员列表
    from App_new.business.projects.models.project_member import ProjectMember
    members = ProjectMember.query.filter_by(header_id=ref.header_id).order_by(ProjectMember.id).all()

    # 获取项目头信息
    header = ProjectHeader.query.get(ref.header_id)

    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查关联的EO是否已付款（排除已取消的）
    eo_paid = False
    if ref.eos and ref.eos.status not in ['void', 'cancelled']:
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    return render_template('business/projects/project_ref/create_transport_ref.html',
                         ref=ref,
                         header=header,
                         header_id=ref.header_id,
                         suppliers=suppliers,
                         supplier_types=supplier_types,
                         extra_info=extra_info,
                         members=members,
                         is_create=False,
                         has_invoice=has_invoice,
                         eo_paid=eo_paid)


@project_ref.route('/flight/edit/<int:ref_id>', methods=['GET'])
def edit_flight_ref(ref_id):
    """编辑机票REF页面"""
    from sqlalchemy.orm import joinedload

    # 直接查询REF，不需要预加载
    ref = ProjectRef.query.get_or_404(ref_id)

    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查关联的EO是否已付款（排除已取消的）
    eo_paid = False
    if ref.eos and ref.eos.status not in ['void', 'cancelled']:
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    # 获取供应商数据
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
    # 动态获取供应商类型（从 BusinessType 表）
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

    # 当没有乘客数据但REF有价格时，创建回退乘客
    fallback_passenger = None
    if not ref.flight_passengers and ref.selling_price:
        # 从extra_info获取客户名
        client_name = ''
        if ref.extra_info:
            try:
                extra = json.loads(ref.extra_info)
                client_name = extra.get('client_name', '')
                # 移除称谓后缀
                for suffix in [' MR', ' MS', ' MRS', ' MISS']:
                    if client_name.endswith(suffix):
                        client_name = client_name[:-len(suffix)]
                        break
            except (json.JSONDecodeError, TypeError):
                pass
        fallback_passenger = {
            'name': client_name,
            'selling_price': float(ref.selling_price) if ref.selling_price else 0,
            'cost_price': float(ref.cost_price) if ref.cost_price else 0
        }

    return render_template('business/projects/project_ref/create_flight_ref.html',
                          header_id=ref.header_id,
                          ref_id=ref.id,
                         ref=ref,
                          suppliers=suppliers,
                          supplier_types=supplier_types,
                          has_invoice=has_invoice,
                          eo_paid=eo_paid,
                          fallback_passenger=fallback_passenger)

@project_ref.route('/flight/detail/<int:ref_id>', methods=['GET'])
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
    
    return render_template('business/projects/project_ref/flight_ref_detail.html', 
                         ref=ref, 
                         prev_ref=prev_ref, 
                         next_ref=next_ref)

@project_ref.route('/hotel/detail/<int:ref_id>', methods=['GET'])
def hotel_ref_detail(ref_id):
    """酒店REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = CustomerCompany.query.get(ref.company_id or ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/hotel_ref_detail.html', 
                         ref=ref, 
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)

@project_ref.route('/visa/detail/<int:ref_id>', methods=['GET'])
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
    
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = CustomerCompany.query.get(ref.company_id or ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/visa_ref_detail.html', 
                         ref=ref, 
                         visa_info=visa_info,
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)

@project_ref.route('/visa/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_visa_ref(ref_id):
    """编辑签证REF"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是签证类型的REF
    business_type = BusinessType.query.get(ref.ref_type_id)
    if not business_type or business_type.name != '签证':
        flash('只能编辑签证类型的REF', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 检查是否有前端发送的完整extra_info JSON
            extra_info_json = request.form.get('extra_info')
            if extra_info_json:
                try:
                    extra_info = json.loads(extra_info_json)
                except json.JSONDecodeError:
                    extra_info = {}
            else:
                # 回退到旧版：从单独字段构建extra_info
                pax_names = request.form.getlist('pax_names')
                pax_names = [int(x) for x in pax_names if x]
                leader_id = request.form.get('leader_id')
                leader_id = int(leader_id) if leader_id else None

                extra_info = {
                    'visa_name': request.form.get('visa_name', ''),
                    'country': request.form.get('country', ''),
                    'visa_type': request.form.get('visa_type', ''),
                    'pax_names': pax_names,
                    'leader_id': leader_id,
                    'departure_date': request.form.get('departure_date', ''),
                    'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                    'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                    'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                    'child_qty': int(request.form.get('child_qty', 0) or 0),
                    'child_selling': float(request.form.get('child_selling', 0) or 0),
                    'child_cost': float(request.form.get('child_cost', 0) or 0),
                    'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                    'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                    'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                }

            # 获取描述字段（前端自动生成）
            description = request.form.get('description', extra_info.get('visa_name', 'Visa Application'))
            detailed_description = request.form.get('detailed_description', description)

            # 生成 pax_names_display
            pax_names = extra_info.get('pax_names', [])
            if pax_names:
                from App_new.business.projects.models.project_member import ProjectMember
                pax_ids = [int(pid) for pid in pax_names if pid]
                if pax_ids:
                    members = ProjectMember.query.filter(ProjectMember.id.in_(pax_ids)).all()
                    pax_names_list = [f"{m.title} {m.member_name}" if m.title else m.member_name for m in members]
                    extra_info['pax_names_display'] = ', '.join(pax_names_list)

            # 更新REF数据
            ref.description = description
            ref.detailed_description = detailed_description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0
            ref.status = request.form.get('status') or 'confirmed'
            ref.remarks = request.form.get('remarks', '')
            ref.extra_info = json.dumps(extra_info, ensure_ascii=False)

            # 提交数据库更改
            db.session.commit()
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    # 获取供应商数据（按名称排序）
    from sqlalchemy import func
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).order_by(func.lower(CustomerCompany.company_name)).all()
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

    # 获取所有国家数据
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()

    # 解析签证专属信息
    visa_info = {}
    if ref and ref.extra_info:
        try:
            visa_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            visa_info = {}

    # 获取项目人员列表
    from App_new.business.projects.models.project_member import ProjectMember
    members = ProjectMember.query.filter_by(header_id=ref.header_id).order_by(ProjectMember.id).all()

    # 获取项目头信息
    header = ProjectHeader.query.get(ref.header_id)

    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查关联的EO是否已付款（排除已取消的）
    eo_paid = False
    if ref.eos and ref.eos.status not in ['void', 'cancelled']:
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    # 获取预选的签证类型列表
    visa_types = []
    # 检查 country 或 visa_country 键
    country_name = visa_info.get('country') or visa_info.get('visa_country')
    if country_name:
        # 根据国家名获取国家ID
        country_obj = VisaCountries.query.filter_by(country_name_CN=country_name).first()
        if country_obj:
            from App_new.business.visa.models.Visamodels import VisaTypes
            visa_types = VisaTypes.query.filter_by(country_id=country_obj.id).all()

    return render_template('business/projects/project_ref/create_visa_ref.html',
                         ref=ref,
                         header=header,
                         header_id=ref.header_id,
                         suppliers=suppliers,
                         supplier_types=supplier_types,
                         countries=countries,
                         visa_info=visa_info,
                         extra_info=visa_info,
                         visa_types=visa_types,
                         members=members,
                         is_create=False,
                         has_invoice=has_invoice,
                         eo_paid=eo_paid)

@project_ref.route('/tour/detail/<int:ref_id>', methods=['GET'])
def tour_ref_detail(ref_id):
    """旅游团REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = CustomerCompany.query.get(ref.company_id or ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/tour_ref_detail.html', 
                         ref=ref, 
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)

@project_ref.route('/insurance/detail/<int:ref_id>', methods=['GET'])
def insurance_ref_detail(ref_id):
    """保险REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = CustomerCompany.query.get(ref.company_id or ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/insurance_ref_detail.html', 
                         ref=ref, 
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)

@project_ref.route('/transport/detail/<int:ref_id>', methods=['GET'])
def transport_ref_detail(ref_id):
    """交通REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
        
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = CustomerCompany.query.get(ref.company_id or ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/transport_ref_detail.html', 
                         ref=ref,
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)


# 景点/活动REF相关函数
@project_ref.route('/attraction/create/<int:header_id>', methods=['GET'])
@login_required
@staff_only
def create_attraction_ref(header_id):
    """创建景点/活动REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 检查是否有人员名单
        if header.members.count() == 0:
            flash('请先在人员名单中添加人员后再创建REF', 'warning')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

        # 获取供应商数据
        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
        supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

        # 获取项目人员列表
        from App_new.business.projects.models.project_member import ProjectMember
        members = ProjectMember.query.filter_by(header_id=header_id).order_by(ProjectMember.id).all()

        return render_template('business/projects/project_ref/create_attraction_ref.html',
                             header_id=header_id,
                             header=header,
                             suppliers=suppliers,
                             supplier_types=supplier_types,
                             members=members,
                             extra_info=None,
                             is_create=True,
                             has_invoice=False)
    except Exception as e:
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/attraction/submit', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def submit_attraction_ref():
    """提交景点/活动REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 检查是否有前端发送的完整extra_info JSON
        extra_info_json = request.form.get('extra_info')
        if extra_info_json:
            try:
                extra_info = json.loads(extra_info_json)
            except json.JSONDecodeError:
                extra_info = {}
        else:
            # 回退到旧版：从单独字段构建extra_info
            pax_names = request.form.getlist('pax_names')
            pax_names = [int(x) for x in pax_names if x]
            leader_id = request.form.get('leader_id')
            leader_id = int(leader_id) if leader_id else None

            extra_info = {
                'attraction_type': request.form.get('attraction_type', ''),
                'attraction_name': request.form.get('attraction_name', ''),
                'location': request.form.get('location', ''),
                'visit_date': request.form.get('visit_date', ''),
                'time_slot': request.form.get('time_slot', ''),
                'ticket_type': request.form.get('ticket_type', ''),
                'confirmation_number': request.form.get('confirmation_number', ''),
                'pax_names': pax_names,
                'leader_id': leader_id,
                'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                'child_qty': int(request.form.get('child_qty', 0) or 0),
                'child_selling': float(request.form.get('child_selling', 0) or 0),
                'child_cost': float(request.form.get('child_cost', 0) or 0),
                'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                'infant_cost': float(request.form.get('infant_cost', 0) or 0),
            }

        # 获取description和detailed_description from frontend
        description = request.form.get('description', '').strip()
        detailed_description = request.form.get('detailed_description', '').strip()

        if not description:
            description = 'Attraction'

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            ref.description = description
            ref.detailed_description = detailed_description or description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'confirmed')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0
            ref.extra_info = json.dumps(extra_info, ensure_ascii=False)
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")

            # 获取景点业务类型ID
            attraction_business_type = BusinessType.query.filter_by(code='attraction').first()
            if not attraction_business_type:
                attraction_business_type = BusinessType.query.filter_by(name='景点/活动').first()
            if not attraction_business_type:
                # 自动创建景点业务类型
                attraction_business_type = BusinessType(
                    code='attraction',
                    name='景点/活动',
                    description='景点门票和活动服务',
                    sort_order=7,
                    is_active=True
                )
                db.session.add(attraction_business_type)
                db.session.flush()

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                description=description,
                ref_type_id=attraction_business_type.id,
                detailed_description=detailed_description or description,
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None,
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'confirmed'),
                payment_status='unpaid',
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0,
                extra_info=json.dumps(extra_info, ensure_ascii=False)
            )
            db.session.add(ref)

        db.session.commit()
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))


@project_ref.route('/attraction/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_attraction_ref(ref_id):
    """编辑景点/活动REF"""
    ref = ProjectRef.query.get_or_404(ref_id)

    # 确保这是景点类型的REF
    business_type = BusinessType.query.get(ref.ref_type_id)
    if not business_type or (business_type.code != 'attraction' and business_type.name != '景点/活动'):
        flash('只能编辑景点/活动类型的REF', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

    if request.method == 'POST':
        try:
            # 检查是否有前端发送的完整extra_info JSON
            extra_info_json = request.form.get('extra_info')
            if extra_info_json:
                try:
                    extra_info = json.loads(extra_info_json)
                except json.JSONDecodeError:
                    extra_info = {}
            else:
                # 回退到旧版：从单独字段构建extra_info
                pax_names = request.form.getlist('pax_names')
                pax_names = [int(x) for x in pax_names if x]
                leader_id = request.form.get('leader_id')
                leader_id = int(leader_id) if leader_id else None

                extra_info = {
                    'attraction_type': request.form.get('attraction_type', ''),
                    'attraction_name': request.form.get('attraction_name', ''),
                    'location': request.form.get('location', ''),
                    'visit_date': request.form.get('visit_date', ''),
                    'time_slot': request.form.get('time_slot', ''),
                    'ticket_type': request.form.get('ticket_type', ''),
                    'confirmation_number': request.form.get('confirmation_number', ''),
                    'pax_names': pax_names,
                    'leader_id': leader_id,
                    'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                    'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                    'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                    'child_qty': int(request.form.get('child_qty', 0) or 0),
                    'child_selling': float(request.form.get('child_selling', 0) or 0),
                    'child_cost': float(request.form.get('child_cost', 0) or 0),
                    'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                    'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                    'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                }

            # 获取description和detailed_description from frontend
            description = request.form.get('description', '').strip()
            detailed_description = request.form.get('detailed_description', '').strip()

            if not description:
                description = ref.description or 'Attraction'

            ref.description = description
            ref.detailed_description = detailed_description or description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0
            ref.status = request.form.get('status') or 'confirmed'
            ref.remarks = request.form.get('remarks', '')
            ref.extra_info = json.dumps(extra_info, ensure_ascii=False)

            db.session.commit()
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

    # 获取供应商数据
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

    # 解析景点专属信息
    extra_info = {}
    if ref and ref.extra_info:
        try:
            extra_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            extra_info = {}

    # 获取项目人员列表
    from App_new.business.projects.models.project_member import ProjectMember
    members = ProjectMember.query.filter_by(header_id=ref.header_id).order_by(ProjectMember.id).all()

    # 获取项目头信息
    header = ProjectHeader.query.get(ref.header_id)

    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查 EO 是否已付款（排除已取消的）
    eo_paid = False
    if ref.eos and ref.eos.status not in ['void', 'cancelled']:
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    return render_template('business/projects/project_ref/create_attraction_ref.html',
                         ref=ref,
                         header=header,
                         header_id=ref.header_id,
                         suppliers=suppliers,
                         supplier_types=supplier_types,
                         extra_info=extra_info,
                         members=members,
                         is_create=False,
                         has_invoice=has_invoice,
                         eo_paid=eo_paid)


@project_ref.route('/attraction/detail/<int:ref_id>', methods=['GET'])
def attraction_ref_detail(ref_id):
    """查看景点/活动REF详情"""
    ref = ProjectRef.query.get_or_404(ref_id)

    # 解析extra_info
    extra_info = {}
    if ref.extra_info:
        try:
            extra_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            extra_info = {}

    # 获取供应商名称
    supplier_name = ''
    if ref.supplier_id:
        supplier = CustomerCompany.query.get(ref.company_id or ref.supplier_id)
        if supplier:
            supplier_name = supplier.name

    return render_template('business/projects/project_ref/ref_detail.html',
                         ref=ref,
                         extra_info=extra_info,
                         supplier_name=supplier_name)


@project_ref.route('/generate_ref_number', methods=['GET'])
def generate_ref_number():
    """生成新的REF编号"""
    try:
        ref_number = ProjectRef.generate_ref_number("")
        return jsonify({'ref_number': ref_number})
    except Exception as e:
        error_details = traceback.format_exc()
        return jsonify({
            'error': str(e),
            'details': error_details
        }), 400

@project_ref.route('/delete/<int:ref_id>', methods=['POST', 'GET'])
@login_required
@staff_only
@csrf.exempt
def delete_ref(ref_id):
    """删除REF"""
    ref = ProjectRef.query.get_or_404(ref_id)
    header_id = ref.header_id
    db.session.delete(ref)
    db.session.commit()
    return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))


@project_ref.route('/update_status', methods=['POST'])
@csrf.exempt
def update_ref_status():
    """更新REF状态"""
    try:
        data = request.get_json()
        ref_id = data.get('ref_id')
        status = data.get('status')

        if not ref_id or not status:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400

        ref = ProjectRef.query.get_or_404(ref_id)
        ref.status = status
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '状态更新成功'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }), 500

@project_ref.route('/other/create/<int:header_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@staff_only
def create_other_ref(header_id):
    """创建其他类型REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 检查是否有人员名单
        if header.members.count() == 0:
            flash('请先在人员名单中添加人员后再创建REF', 'warning')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

        if request.method == 'POST':
            try:
                # 检查是否有前端发送的完整extra_info JSON
                extra_info_json = request.form.get('extra_info')
                if extra_info_json:
                    try:
                        extra_info = json.loads(extra_info_json)
                    except json.JSONDecodeError:
                        extra_info = {}
                else:
                    # 回退到旧版：从单独字段构建extra_info
                    pax_names = request.form.getlist('pax_names')
                    pax_names = [int(x) for x in pax_names if x]
                    leader_id = request.form.get('leader_id')
                    leader_id = int(leader_id) if leader_id else None

                    extra_info = {
                        'service_date': request.form.get('service_date', ''),
                        'pax_names': pax_names,
                        'leader_id': leader_id,
                        'adult_qty': int(request.form.get('adult_qty', 1) or 1),
                        'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                        'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                        'child_qty': int(request.form.get('child_qty', 0) or 0),
                        'child_selling': float(request.form.get('child_selling', 0) or 0),
                        'child_cost': float(request.form.get('child_cost', 0) or 0),
                        'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                        'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                        'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                    }

                # 获取表单数据
                description = request.form.get('description') or 'Other Service'
                detailed_description = request.form.get('detailed_description_hidden') or request.form.get('detailed_description') or description

                # 自动设置REF类型为"其他"
                other_business_type = BusinessType.query.filter_by(name='其他').first()
                if not other_business_type:
                    other_business_type = BusinessType(name='其他', code='other', description='其他服务')
                    db.session.add(other_business_type)
                    db.session.flush()

                # 生成REF编号
                ref_number = ProjectRef.generate_ref_number("")

                # 创建REF
                ref = ProjectRef(
                    header_id=header.id,
                    ref_number=ref_number,
                    description=description,
                    ref_type_id=other_business_type.id,
                    detailed_description=detailed_description,
                    supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None,
                    selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                    cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None,
                    currency='SGD',
                    remarks=request.form.get('remarks', ''),
                    status=request.form.get('status', 'confirmed'),
                    payment_status='unpaid',
                    extra_info=json.dumps(extra_info)
                )
                db.session.add(ref)
                db.session.commit()

                return redirect(url_for('business_projects.detail.project_detail', project_id=header.id))

            except Exception as e:
                db.session.rollback()
                flash(f'创建失败：{str(e)}', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header.id))

        # GET请求 - 显示创建页面
        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
        supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

        # 获取项目人员列表
        from App_new.business.projects.models.project_member import ProjectMember
        members = ProjectMember.query.filter_by(header_id=header_id).order_by(ProjectMember.id).all()

        return render_template(
            'business/projects/project_ref/create_other_ref.html',
            ref=None,
            suppliers=suppliers,
            supplier_types=supplier_types,
            header=header,
            header_id=header_id,
            is_create=True,
            extra_info=None,
            members=members,
            has_invoice=False
        )
    except Exception as e:
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/other/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_other_ref(ref_id):
    """编辑其他类型REF"""
    ref = ProjectRef.query.get_or_404(ref_id)

    # 通用REF编辑表单 - 接受没有专用编辑器的类型
    business_type = BusinessType.query.get(ref.ref_type_id)
    # 有专用编辑器的类型应使用对应的编辑路由
    specialized_types = ['机票', '酒店', '签证', '保险', '旅游团', '交通', '景点/活动']
    if business_type and business_type.name in specialized_types:
        flash(f'请使用{business_type.name}专用编辑页面', 'warning')
        return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

    if request.method == 'POST':
        try:
            # 检查是否有前端发送的完整extra_info JSON
            extra_info_json = request.form.get('extra_info')
            if extra_info_json:
                try:
                    extra_info = json.loads(extra_info_json)
                except json.JSONDecodeError:
                    extra_info = {}
            else:
                # 回退到旧版：从单独字段构建extra_info
                pax_names = request.form.getlist('pax_names')
                pax_names = [int(x) for x in pax_names if x]
                leader_id = request.form.get('leader_id')
                leader_id = int(leader_id) if leader_id else None

                extra_info = {
                    'service_date': request.form.get('service_date', ''),
                    'pax_names': pax_names,
                    'leader_id': leader_id,
                    'adult_qty': int(request.form.get('adult_qty', 1) or 1),
                    'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                    'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                    'child_qty': int(request.form.get('child_qty', 0) or 0),
                    'child_selling': float(request.form.get('child_selling', 0) or 0),
                    'child_cost': float(request.form.get('child_cost', 0) or 0),
                    'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                    'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                    'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                }

            # 更新REF数据
            description = request.form.get('description') or ref.description or 'Other Service'
            detailed_description = request.form.get('detailed_description_hidden') or request.form.get('detailed_description') or description
            ref.description = description
            ref.detailed_description = detailed_description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            ref.status = request.form.get('status') or ref.status or 'confirmed'
            ref.remarks = request.form.get('remarks', '')
            ref.extra_info = json.dumps(extra_info)

            db.session.commit()
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

    # 获取供应商数据与项目头信息
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]
    header = ProjectHeader.query.get(ref.header_id)

    # 获取项目人员列表
    from App_new.business.projects.models.project_member import ProjectMember
    members = ProjectMember.query.filter_by(header_id=ref.header_id).order_by(ProjectMember.id).all()

    # 解析extra_info
    extra_info = None
    if ref.extra_info:
        try:
            extra_info = json.loads(ref.extra_info)
        except (json.JSONDecodeError, TypeError):
            extra_info = None

    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查 EO 是否已付款
    eo_paid = False
    if ref.eos and ref.eos.status != 'void':
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    return render_template(
        'business/projects/project_ref/create_other_ref.html',
        ref=ref,
        suppliers=suppliers,
        supplier_types=supplier_types,
        header=header,
        header_id=ref.header_id,
        is_create=False,
        extra_info=extra_info,
        members=members,
        has_invoice=has_invoice,
        eo_paid=eo_paid
    )

@project_ref.route('/insurance/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_insurance_ref(ref_id):
    """编辑保险REF"""
    from App_new.business.projects.models.project_member import ProjectMember
    from App_new.business.projects.models.invoice import InvoiceItem

    ref = ProjectRef.query.get_or_404(ref_id)

    # 确保这是保险类型的REF
    business_type = BusinessType.query.get(ref.ref_type_id)
    if not business_type or business_type.name != '保险':
        flash('只能编辑保险类型的REF', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

    if request.method == 'POST':
        try:
            # 检查是否有前端发送的完整extra_info JSON
            extra_info_json = request.form.get('extra_info')
            if extra_info_json:
                try:
                    extra_info = json.loads(extra_info_json)
                except json.JSONDecodeError:
                    extra_info = {}
            else:
                # 回退到旧版：从单独字段构建extra_info
                extra_info = {
                    'insurance_type': request.form.get('insurance_type', ''),
                    'policy_number': request.form.get('policy_number', ''),
                    'start_date': request.form.get('start_date', ''),
                    'end_date': request.form.get('end_date', ''),
                    'days': int(request.form.get('days', 0) or 0),
                    'pax_names': request.form.getlist('pax_names'),
                    'leader_id': request.form.get('leader_id', ''),
                    'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                    'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                    'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                    'child_qty': int(request.form.get('child_qty', 0) or 0),
                    'child_selling': float(request.form.get('child_selling', 0) or 0),
                    'child_cost': float(request.form.get('child_cost', 0) or 0),
                    'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                    'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                    'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                }

            # 更新REF数据
            description = request.form.get('description')
            if not description:
                description = ref.description or 'Insurance'
            ref.description = description
            ref.detailed_description = request.form.get('detailed_description', description)
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            ref.remarks = request.form.get('remarks', '')
            ref.status = request.form.get('status', 'confirmed')
            ref.extra_info = json.dumps(extra_info)

            # 提交数据库更改
            db.session.commit()
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

    # 获取供应商数据
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

    # 获取项目成员
    members = ProjectMember.query.filter_by(header_id=ref.header_id).order_by(ProjectMember.id).all()

    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查 EO 是否已付款
    eo_paid = False
    if ref.eos and ref.eos.status != 'void':
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    # 解析保险专属信息
    extra_info = {}
    if ref and ref.extra_info:
        try:
            extra_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            extra_info = {}

    return render_template('business/projects/project_ref/create_insurance_ref.html',
                         ref=ref,
                         header_id=ref.header_id,
                         suppliers=suppliers,
                         supplier_types=supplier_types,
                         extra_info=extra_info,
                         members=members,
                         has_invoice=has_invoice,
                         eo_paid=eo_paid,
                         is_create=False)

@project_ref.route('/tour/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_tour_ref(ref_id):
    """编辑旅游团REF"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是旅游团类型的REF
    business_type = BusinessType.query.get(ref.ref_type_id)
    if not business_type or business_type.name != '旅游团':
        flash('只能编辑旅游团类型的REF', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            import json

            # 检查是否有前端发送的完整extra_info JSON
            extra_info_json = request.form.get('extra_info')
            if extra_info_json:
                try:
                    extra_info = json.loads(extra_info_json)
                except json.JSONDecodeError:
                    extra_info = {}
            else:
                # 回退到旧版：从单独字段构建extra_info
                tour_name = request.form.get('tour_name', 'Tour Booking')
                extra_info = {
                    'tour_name': tour_name,
                    'departure_date': request.form.get('departure_date', ''),
                    'end_date': request.form.get('end_date', ''),
                    'itinerary': request.form.get('itinerary', ''),
                    'pax_names': request.form.getlist('pax_names'),
                    'leader_id': request.form.get('leader_id', ''),
                    'adult_qty': int(request.form.get('adult_qty', 0) or 0),
                    'adult_selling': float(request.form.get('adult_selling', 0) or 0),
                    'adult_cost': float(request.form.get('adult_cost', 0) or 0),
                    'child_qty': int(request.form.get('child_qty', 0) or 0),
                    'child_selling': float(request.form.get('child_selling', 0) or 0),
                    'child_cost': float(request.form.get('child_cost', 0) or 0),
                    'infant_qty': int(request.form.get('infant_qty', 0) or 0),
                    'infant_selling': float(request.form.get('infant_selling', 0) or 0),
                    'infant_cost': float(request.form.get('infant_cost', 0) or 0),
                    # 单房差
                    'single_room_qty': int(request.form.get('single_room_qty', 0) or 0),
                    'single_room_selling': float(request.form.get('single_room_selling', 0) or 0),
                    'single_room_cost': float(request.form.get('single_room_cost', 0) or 0),
                }

            # 获取描述字段（前端自动生成）
            description = request.form.get('description', extra_info.get('tour_name', 'Tour Booking'))
            detailed_description = request.form.get('detailed_description', description)

            # 生成 pax_names_display
            from App_new.business.projects.models.project_member import ProjectMember
            pax_ids = [int(pid) for pid in extra_info.get('pax_names', []) if pid]
            if pax_ids:
                members = ProjectMember.query.filter(ProjectMember.id.in_(pax_ids)).all()
                pax_names_list = [f"{m.title} {m.member_name}" if m.title else m.member_name for m in members]
                extra_info['pax_names_display'] = ', '.join(pax_names_list)

            # 更新REF数据
            ref.description = description
            ref.detailed_description = detailed_description
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else 0
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else 0
            ref.status = request.form.get('status') or 'confirmed'
            ref.remarks = request.form.get('remarks', '')
            ref.extra_info = json.dumps(extra_info, ensure_ascii=False)

            # 提交数据库更改
            db.session.commit()
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    # 获取供应商数据
    from sqlalchemy import func
    header = ProjectHeader.query.get(ref.header_id)
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).order_by(func.lower(CustomerCompany.company_name)).all()
    supplier_types = [bt.code for bt in BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()]

    # 获取项目成员
    from App_new.business.projects.models.project_member import ProjectMember
    members = ProjectMember.query.filter_by(header_id=ref.header_id).all()

    # 解析 extra_info
    extra_info = None
    if ref.extra_info:
        try:
            import json
            extra_info = json.loads(ref.extra_info)
        except:
            pass

    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查 EO 是否已付款（排除已取消的）
    eo_paid = False
    if ref.eos and ref.eos.status not in ['void', 'cancelled']:
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    return render_template('business/projects/project_ref/create_tour_ref.html',
                         header=header,
                         header_id=ref.header_id,
                         ref=ref,
                         suppliers=suppliers,
                         supplier_types=supplier_types,
                         members=members,
                         extra_info=extra_info,
                         is_create=False,
                         has_invoice=has_invoice,
                         eo_paid=eo_paid)

@project_ref.route('/api/get_visa_types/<int:country_id>', methods=['GET'])
def get_visa_types_by_country(country_id):
    """根据国家ID获取签证类型"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTypes
        
        # 查询指定国家的签证类型
        visa_types = VisaTypes.query.filter_by(country_id=country_id).all()
        
        # 转换为前端需要的格式
        visa_types_list = [
            {
                'visa_type': vt.visa_type,
                'country_id': vt.country_id
            }
            for vt in visa_types
        ]
        
        return jsonify({
            'success': True,
            'visa_types': visa_types_list
        })
    except Exception as e:
        print(f"获取签证类型时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@project_ref.route('/list', methods=['GET'])
def ref_list():
    """REF列表页面 - 支持筛选、搜索和分页"""
    try:
        from sqlalchemy import and_, or_, desc, asc
        from datetime import datetime, timedelta
        
        # 获取筛选参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        business_type = request.args.get('business_type', '')
        status = request.args.get('status', '')
        supplier_id = request.args.get('supplier', None, type=int)
        leader_name = request.args.get('leader_name', '')
        date_range = request.args.get('date_range', '')
        min_price = request.args.get('min_price', None, type=float)
        max_price = request.args.get('max_price', None, type=float)
        keyword = request.args.get('keyword', '')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        has_eo = request.args.get('has_eo', '')
        
        # 构建查询
        query = db.session.query(
            ProjectRef,
            BusinessType.name.label('business_type_name'),
            CustomerCompany.company_name.label('supplier_name'),
            ProjectHeader.desc.label('project_name')
        ).join(
            BusinessType, ProjectRef.ref_type_id == BusinessType.id, isouter=True
        ).join(
            CustomerCompany, ProjectRef.supplier_id == CustomerCompany.id, isouter=True
        ).join(
            ProjectHeader, ProjectRef.header_id == ProjectHeader.id, isouter=True
        )
        
        # 应用筛选条件
        filters = []
        
        if business_type:
            filters.append(BusinessType.name == business_type)
        
        if status:
            filters.append(ProjectRef.status == status)
        
        if supplier_id:
            filters.append(ProjectRef.supplier_id == supplier_id)
        
        if leader_name:
            filters.append(ProjectHeader.leader_name.ilike(f'%{leader_name}%'))
        
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
                ProjectRef.created_at >= start_date,
                ProjectRef.created_at < end_date
            ))
        
        if min_price is not None and min_price > 0:
            filters.append(ProjectRef.selling_price >= float(min_price))
        
        if max_price is not None and max_price > 0:
            filters.append(ProjectRef.selling_price <= float(max_price))
        
        if keyword:
            keyword_filter = or_(
                ProjectRef.description.ilike(f'%{keyword}%'),
                ProjectRef.detailed_description.ilike(f'%{keyword}%'),
                ProjectRef.ref_number.ilike(f'%{keyword}%'),
                ProjectHeader.leader_name.ilike(f'%{keyword}%'),
                ProjectHeader.desc.ilike(f'%{keyword}%')
            )
            filters.append(keyword_filter)

        # EO筛选条件
        if has_eo:
            from App_new.business.projects.models.eo import ProjectEO
            # 构建子查询：查找有EO的REF ID
            eo_subq = db.session.query(ProjectEO.ref_id).subquery()
            if has_eo == 'yes':
                # 有EO的REF
                filters.append(ProjectRef.id.in_(db.session.query(ProjectEO.ref_id)))
            elif has_eo == 'no':
                # 没有EO的REF
                filters.append(~ProjectRef.id.in_(db.session.query(ProjectEO.ref_id)))

        # 应用筛选条件
        if filters:
            query = query.filter(and_(*filters))
        
        # 排序
        if sort_by == 'created_at':
            order_column = ProjectRef.created_at
        elif sort_by == 'name':
            order_column = ProjectRef.description
        elif sort_by == 'selling_price':
            order_column = ProjectRef.selling_price
        elif sort_by == 'status':
            order_column = ProjectRef.status
        else:
            order_column = ProjectRef.created_at
        
        if sort_order == 'asc':
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))
        
        # 分页 - 使用新版本Flask-SQLAlchemy的方法
        try:
            # 尝试使用新版本的分页方法
            pagination = query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            print(f"使用新版本分页方法成功")
        except AttributeError as e:
            print(f"新版本分页方法失败: {e}")
            # 如果新版本方法不存在，使用旧版本
            try:
                pagination = query.paginate(
                    page=page, 
                    per_page=per_page, 
                    error_out=False
                )
                print(f"使用旧版本分页方法成功")
            except Exception as e2:
                print(f"旧版本分页方法也失败: {e2}")
                # 如果都失败了，手动创建分页对象
                total = query.count()
                pages = (total + per_page - 1) // per_page
                offset = (page - 1) * per_page
                items = query.offset(offset).limit(per_page).all()
                
                class ManualPagination:
                    def __init__(self, items, page, per_page, total, pages):
                        self.items = items
                        self.page = page
                        self.per_page = per_page
                        self.total = total
                        self.pages = pages
                        self.has_prev = page > 1
                        self.has_next = page < pages
                        self.prev_num = page - 1 if page > 1 else None
                        self.next_num = page + 1 if page < pages else None
                    
                    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
                        last = 0
                        for num in range(1, self.pages + 1):
                            if num <= left_edge or \
                               (num > self.page - left_current - 1 and \
                                num < self.page + right_current) or \
                               num > self.pages - right_edge:
                                if last + 1 != num:
                                    yield None
                                yield num
                                last = num
                
                pagination = ManualPagination(items, page, per_page, total, pages)
                print(f"使用手动分页对象成功")
        
        # 确保分页对象有必要的属性
        if not hasattr(pagination, 'has_prev'):
            # 手动添加分页属性（兼容旧版本）
            pagination.has_prev = pagination.page > 1
            pagination.has_next = pagination.page < pagination.pages
            pagination.prev_num = pagination.page - 1 if pagination.page > 1 else None
            pagination.next_num = pagination.page + 1 if pagination.page < pagination.pages else None
        
        # 确保分页对象有iter_pages方法
        if not hasattr(pagination, 'iter_pages'):
            def iter_pages(left_edge=2, left_current=2, right_current=5, right_edge=2):
                """生成分页页码"""
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
        
        # 处理REF数据，添加显示属性
        refs = []
        for ref, business_type_name, supplier_name, project_name in pagination.items:
            # 获取关联的EO信息
            eo_info = None
            if ref.eos:
                eo = ref.eos
                eo_info = {
                    'id': eo.id,
                    'eo_number': eo.eo_number,
                    'status': eo.status
                }

            ref_dict = {
                'id': ref.id,
                'ref_number': str(ref.ref_number) if ref.ref_number else '',
                'description': str(ref.description) if ref.description else '',
                'detailed_description': str(ref.detailed_description) if ref.detailed_description else '',
                'business_type_name': str(business_type_name) if business_type_name else '未知',
                'business_type_color': get_business_type_color(business_type_name),
                'header_id': ref.header_id,
                'project_name': str(project_name) if project_name else f'项目{ref.header_id}',
                'supplier_name': str(supplier_name) if supplier_name else '',
                'leader_name': str(ref.header.leader_name) if ref.header and ref.header.leader_name else '',
                'status': str(ref.status) if ref.status else 'confirmed',
                'status_display': get_status_display(ref.status),
                'status_color': get_status_color(ref.status),
                'selling_price': float(ref.selling_price) if ref.selling_price is not None else 0,
                'cost_price': float(ref.cost_price) if ref.cost_price is not None else 0,
                'created_at': ref.created_at,
                'eo': eo_info
            }
            refs.append(ref_dict)
        
        # 获取筛选选项数据
        business_types = BusinessType.query.order_by(BusinessType.name).all()
        suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).order_by(CustomerCompany.company_name).all()
        
        # 计算筛选结果数量
        filtered_count = pagination.total if any([business_type, status, supplier_id, leader_name, date_range, min_price, max_price, keyword]) else None
        
        # 添加调试信息
        print(f"分页调试信息:")
        print(f"  当前页: {pagination.page}")
        print(f"  总页数: {pagination.pages}")
        print(f"  每页数量: {pagination.per_page}")
        print(f"  总记录数: {pagination.total}")
        print(f"  是否有上一页: {pagination.has_prev}")
        print(f"  是否有下一页: {pagination.has_next}")
        print(f"  上一页页码: {pagination.prev_num}")
        print(f"  下一页页码: {pagination.next_num}")
        
        return render_template('business/projects/project_ref/ref_list.html',
                             refs=refs,
                             pagination=pagination,
                             business_types=business_types,
                             suppliers=suppliers,
                             filtered_count=filtered_count,
                             current_filters={
                                 'business_type': business_type,
                                 'status': status,
                                 'supplier': supplier_id,
                                 'leader_name': leader_name,
                                 'date_range': date_range,
                                 'min_price': min_price,
                                 'max_price': max_price,
                                 'keyword': keyword,
                                 'sort_by': sort_by,
                                 'sort_order': sort_order
                             })
                             
    except Exception as e:
        import traceback
        print(f"REF列表加载失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        flash(f'REF列表加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))

def get_status_display(status):
    """获取状态的中文显示名称"""
    if not status or not isinstance(status, str):
        return '未知'
    
    status_map = {
        'draft': '草稿',
        'processing': '进行中',
        'completed': '已完成',
        'cancelled': '已取消'
    }
    return status_map.get(status, status)

def get_status_color(status):
    """获取状态对应的Bootstrap颜色类"""
    if not status or not isinstance(status, str):
        return 'secondary'
    
    color_map = {
        'draft': 'secondary',
        'processing': 'info',
        'completed': 'success',
        'cancelled': 'danger'
    }
    return color_map.get(status, 'secondary')

def get_business_type_color(business_type_name):
    """获取业务类型对应的Bootstrap颜色类"""
    if not business_type_name or not isinstance(business_type_name, str):
        return 'secondary'
    
    color_map = {
        '机票': 'primary',
        '酒店': 'success',
        '签证': 'warning',
        '旅游团': 'info',
        '保险': 'danger',
        '交通': 'secondary',
        '其他': 'dark'
    }
    return color_map.get(business_type_name, 'secondary')


@project_ref.route('/general/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_ref(ref_id):
    """编辑通用REF - 根据业务类型路由到不同编辑页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 根据业务类型ID路由到不同的编辑页面
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 根据业务类型路由到对应的编辑页面
    if ref_type_name == '机票':
        return redirect(url_for('business_projects.project_ref.edit_flight_ref', ref_id=ref.id))
    elif ref_type_name == '酒店':
        return redirect(url_for('business_projects.project_ref.edit_hotel_ref', ref_id=ref.id))
    elif ref_type_name == '签证':
        return redirect(url_for('business_projects.project_ref.edit_visa_ref', ref_id=ref.id))
    elif ref_type_name == '旅游':
        return redirect(url_for('business_projects.project_ref.edit_tour_ref', ref_id=ref.id))
    elif ref_type_name == '保险':
        return redirect(url_for('business_projects.project_ref.edit_insurance_ref', ref_id=ref.id))
    # elif ref_type_name == '交通':
    #     # Transport ref编辑通过submit路由处理，暂时注释
    #     # return redirect(url_for('business_projects.project_ref.edit_transport_ref', ref_id=ref.id))
    #     pass
    elif ref_type_name == '其他' or ref_type_name == 'Miscellanous':
        return redirect(url_for('business_projects.project_ref.edit_other_ref', ref_id=ref.id))
    
    # 如果没有匹配的类型，继续使用通用编辑页面（向后兼容）
    if request.method == 'POST':
        try:
            # 检查是否有已付款的EO
            if ref.has_paid_eo():
                flash('此REF的EO已付款，不能编辑', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))

            # 记录旧的成本价格（用于调整预付账款）
            old_cost = ref.cost_price

            # 调试：打印所有表单数据
            print(f"DEBUG: All form data: {dict(request.form)}")

            # 更新REF数据
            ref.description = request.form.get('description', 'REF服务')
            ref.detailed_description = ref.description  # 详细描述自动同步描述内容
            supplier_id = request.form.get('supplier_id')
            print(f"DEBUG: supplier_id from form: {supplier_id}, type: {type(supplier_id)}")
            ref.supplier_id = int(supplier_id) if supplier_id and supplier_id != '0' else None
            print(f"DEBUG: ref.supplier_id after update: {ref.supplier_id}")
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None

            # 处理日期字段，空字符串转换为None

            ref.status = request.form.get('status') or 'confirmed'
            ref.remarks = request.form.get('remarks', '')

            # 处理出行人信息
            passenger_names = request.form.get('passenger_names', '')
            if passenger_names:
                from App_new.business.flight.models.flight import ProjectFlightPassenger
                # 删除现有乘客
                ProjectFlightPassenger.query.filter_by(ref_id=ref.id).delete()
                # 添加新乘客
                passenger_list = [name.strip() for name in passenger_names.split(',') if name.strip()]
                for passenger_name in passenger_list:
                    passenger = ProjectFlightPassenger(
                        ref_id=ref.id,
                        name=passenger_name,
                        passenger_type='adult'  # 默认为成人
                    )
                    db.session.add(passenger)

            # 调整预付账款（如果cost_price变化）
            prepayment_msg = ref.adjust_prepayment_for_cost_change(old_cost)

            # 提交数据库更改
            db.session.commit()

            if prepayment_msg:
                flash(f'REF更新成功！{prepayment_msg}', 'success')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    # 获取供应商数据和项目头部信息
    suppliers = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).all()
    header = ProjectHeader.query.get(ref.header_id)
    
    # 创建表单对象用于编辑模式
    from App_new.business.projects.forms.ref_forms import ProjectRefForm
    form = ProjectRefForm()
    
    # 预填充表单数据
    form.ref_number.data = ref.ref_number
    form.description.data = ref.description
    form.detailed_description.data = ref.detailed_description
    form.ref_type_id.data = ref.ref_type_id
    form.supplier_id.data = ref.supplier_id
    form.selling_price.data = ref.selling_price
    form.cost_price.data = ref.cost_price
    form.currency.data = ref.currency
    form.status.data = ref.status
    form.payment_status.data = ref.payment_status
    form.remarks.data = ref.remarks
    
    # 预填充出行人姓名
    from App_new.business.flight.models.flight import ProjectFlightPassenger
    passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).all()
    if passengers:
        passenger_names = [p.name for p in passengers]
        form.passenger_names.data = ', '.join(passenger_names)

    # 检查是否有有效的发票（使用 get_invoices 方法，更可靠）
    has_invoice = len(ref.get_invoices()) > 0

    # 检查 EO 是否已付款（排除已取消的）
    eo_paid = False
    if ref.eos and ref.eos.status not in ['void', 'cancelled']:
        if ref.eos.pay_amount or ref.eos.is_paid:
            eo_paid = True

    return render_template('business/projects/project_ref/create_ref.html',
                         ref=ref,
                         header=header,
                         suppliers=suppliers,
                         form=form,
                         is_create=False,
                         has_invoice=has_invoice,
                         eo_paid=eo_paid)
