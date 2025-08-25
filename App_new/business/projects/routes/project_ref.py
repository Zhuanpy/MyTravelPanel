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
from App_new.exts import csrf, db
from App_new.shared.models.Suppliers import Supplier
from App_new.business.visa.models.Visamodels import VisaCountries
from App_new.shared.models.business_types import BusinessType
from App_new.business.projects.forms.ref_forms import ProjectRefForm
from App_new.utils.decorators import staff_only, admin_only
from datetime import datetime
import traceback
import json

project_ref = Blueprint('project_ref', __name__)

@project_ref.route('/general/create/<int:header_id>', methods=['GET', 'POST'])
def create_ref(header_id):
    """创建REF"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)
        form = ProjectRefForm()
        form.header_id.data = header_id
        
        if form.validate_on_submit():
            try:
                # 在应用上下文中生成REF编号
                ref_number = ProjectRef.generate_ref_number("")
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
        suppliers = Supplier.query.all()
        
        return render_template('business/projects/project_ref/create_ref.html',
                           form=form, 
                           header=header, 
                           ref_number=ref_number,
                         business_types=business_types,
                         suppliers=suppliers)
    except Exception as e:
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/detail/<int:ref_id>')
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


@project_ref.route('/flight/create/<int:header_id>')
def create_flight_ref(header_id):
    """创建机票REF页面"""
    header = ProjectHeader.query.get_or_404(header_id)
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
    
    return render_template('business/projects/project_ref/create_flight_ref.html', 
                        header_id=header_id,
                        suppliers=suppliers,
                        supplier_types=supplier_types)


@project_ref.route('/flight/submit', methods=['POST'])
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
            ref.name = '机票订单'
            ref.description = '机票订单'
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                'supplier_id') != '0' else None
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
                name='机票订单',
                ref_type_id=flight_business_type.id,
                description='机票订单',
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                    'supplier_id') != '0' else None,
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

        # 生成基于航段信息的名称
        def generate_flight_ref_name(departure_airports, arrival_airports, departure_dates):
            """根据航段信息生成REF名称：支持多航段"""
            if not departure_airports or not arrival_airports or not departure_dates:
                return '机票订单'

            # 收集所有有效的航段信息
            valid_segments = []
            first_dep_date = None

            for i, (dep_airport, arr_airport, dep_date) in enumerate(
                    zip(departure_airports, arrival_airports, departure_dates)):
                if dep_airport and arr_airport and dep_date:
                    if first_dep_date is None:
                        first_dep_date = dep_date
                    valid_segments.append((dep_airport, arr_airport))

            if not valid_segments or not first_dep_date:
                return '机票订单'

            # 格式化日期为 DDMON 格式 (例如: 12AUG)
            try:
                date_obj = datetime.strptime(first_dep_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d%b').upper()
            except ValueError:
                formatted_date = first_dep_date

            # 根据航段数量和类型生成不同的名称格式
            if len(valid_segments) == 1:
                # 单航段：出发日期 + 出发机场-到达机场
                dep_airport, arr_airport = valid_segments[0]
                ref_name = f"{formatted_date} {dep_airport}-{arr_airport}"

            elif len(valid_segments) == 2:
                # 双航段：检查是否为往返
                dep1, arr1 = valid_segments[0]
                dep2, arr2 = valid_segments[1]

                if dep1 == arr2 and arr1 == dep2:
                    # 往返：出发日期 + 出发机场-到达机场-出发机场
                    ref_name = f"{formatted_date} {dep1}-{arr1}-{dep1}"
                else:
                    # 非往返：出发日期 + 出发机场-到达机场-最终到达机场
                    ref_name = f"{formatted_date} {dep1}-{arr1}-{arr2}"

            else:
                # 多航段：构建完整的航线路径
                route_parts = []
                for i, (dep_airport, arr_airport) in enumerate(valid_segments):
                    if i == 0:
                        # 第一个航段：包含出发机场
                        route_parts.append(f"{dep_airport}-{arr_airport}")
                    else:
                        # 后续航段：只包含到达机场
                        route_parts.append(arr_airport)

                # 检查是否为往返
                first_dep, first_arr = valid_segments[0]
                last_dep, last_arr = valid_segments[-1]

                if first_dep == last_arr and first_arr == last_dep:
                    # 往返：出发日期 + 完整路径
                    ref_name = f"{formatted_date} {'-'.join(route_parts)}"
                else:
                    # 非往返：出发日期 + 完整路径
                    ref_name = f"{formatted_date} {'-'.join(route_parts)}"

            return ref_name

        # 生成REF名称并更新
        generated_name = generate_flight_ref_name(departure_airports, arrival_airports, departure_dates)
        ref.name = generated_name
        ref.description = generated_name

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
            # 允许保存空航段，不强制要求航班号不为空
            try:
                # 安全获取日期和时间，提供默认值
                dep_date = departure_dates[i] if i < len(departure_dates) and departure_dates[
                    i] else datetime.now().strftime('%Y-%m-%d')
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
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))


# 酒店REF相关函数
@project_ref.route('/hotel/create/<int:header_id>')
def create_hotel_ref(header_id):
    """创建酒店REF页面"""
    try:
        from flask import current_app
        if not current_app:
            flash('应用上下文错误，请刷新页面重新操作', 'error')
            return redirect(url_for('business_projects.list.list_projects'))
        
        header = ProjectHeader.query.get_or_404(header_id)
    
        suppliers = Supplier.query.all()
        supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
    
        return render_template('business/projects/project_ref/create_hotel_ref.html', 
                        header_id=header_id,
                        suppliers=suppliers,
                        supplier_types=supplier_types)
    except Exception as e:
        import traceback
        print(f"酒店REF创建页面加载失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/hotel/submit', methods=['POST'])
@csrf.exempt
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

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            # 更新REF基本信息
            ref.name = request.form.get('name', '酒店订单')
            ref.description = request.form.get('description', '酒店订单')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                'supplier_id') != '0' else None
            ref.leader_name = request.form.get('leader_name', '')
            ref.contact_name = request.form.get('contact_name')
            ref.contact_phone = request.form.get('contact_phone')
            ref.contact_email = request.form.get('contact_email')
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'draft')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get(
                'selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
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
                return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '酒店订单'),
                ref_type_id=hotel_business_type.id,
                description=request.form.get('description', '酒店订单'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                    'supplier_id') != '0' else None,
                leader_name=request.form.get('leader_name', ''),
                contact_name=request.form.get('contact_name'),
                contact_phone=request.form.get('contact_phone'),
                contact_email=request.form.get('contact_email'),
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'draft'),
                payment_status=request.form.get('payment_status', 'unpaid'),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get(
                    'selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id

        db.session.commit()
        flash('酒店REF保存成功', 'success')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))

    except Exception as e:
        import traceback
        print(f"酒店REF提交失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))


# 签证REF相关函数
@project_ref.route('/visa/create/<int:header_id>')
def create_visa_ref(header_id):
    """创建签证REF页面"""
    try:
        # 确保在应用上下文中运行
        from flask import current_app
        if not current_app:
            flash('应用上下文错误，请刷新页面重新操作', 'error')
            return redirect(url_for('business_projects.list.list_projects'))
        
        header = ProjectHeader.query.get_or_404(header_id)
    
        # 获取供应商数据
        suppliers = Supplier.query.all()
        supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
    
        countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
        return render_template('business/projects/project_ref/create_visa_ref.html', 
                             header_id=header_id,
                             suppliers=suppliers, 
                             supplier_types=supplier_types,
                             countries=countries)
    except Exception as e:
        import traceback
        print(f"签证REF创建页面加载失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))

@project_ref.route('/visa/submit', methods=['POST'])
@csrf.exempt
def submit_visa_ref():
    """提交签证REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')
        
        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            # 更新REF基本信息
            ref.name = request.form.get('name', '签证订单')
            ref.description = request.form.get('description', '签证订单')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.leader_name = request.form.get('leader_name', '')
            ref.contact_name = request.form.get('contact_name')
            ref.contact_phone = request.form.get('contact_phone')
            ref.contact_email = request.form.get('contact_email')
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'draft')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")
            
            # 获取签证业务类型ID
            visa_business_type = BusinessType.query.filter_by(name='签证').first()
            if not visa_business_type:
                flash('未找到签证业务类型，请先创建', 'error')
                return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))
            
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '签证订单'),
                ref_type_id=visa_business_type.id,
                description=request.form.get('description', '签证订单'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None,
                leader_name=request.form.get('leader_name', ''),
                contact_name=request.form.get('contact_name'),
                contact_phone=request.form.get('contact_phone'),
                contact_email=request.form.get('contact_email'),
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'draft'),
                payment_status=request.form.get('payment_status', 'unpaid'),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id
        
            db.session.commit()
        flash('签证REF保存成功', 'success')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))

# 旅游团REF相关函数
@project_ref.route('/tour/create/<int:header_id>')
def create_tour_ref(header_id):
    """创建旅游团REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)
    
        # 获取供应商数据
        suppliers = Supplier.query.all()
        supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
        
        return render_template('business/projects/project_ref/create_tour_ref.html', 
                             header_id=header_id,
                             suppliers=suppliers,
                             supplier_types=supplier_types)
    except Exception as e:
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/tour/submit', methods=['POST'])
@csrf.exempt
def submit_tour_ref():
    """提交旅游团REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            # 更新REF基本信息
            ref.name = request.form.get('name', '旅游团订购')
            ref.description = request.form.get('description', '旅游团订购')
            ref.supplier_id = (
                request.form.get('supplier_id')
                if request.form.get('supplier_id') and request.form.get('supplier_id') != '0'
                else None
            )
            ref.leader_name = request.form.get('leader_name', '')
            ref.contact_name = request.form.get('contact_name')
            ref.contact_phone = request.form.get('contact_phone')
            ref.contact_email = request.form.get('contact_email')
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'draft')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get(
                'selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")

            # 获取旅游团业务类型ID
            tour_business_type = BusinessType.query.filter_by(name='旅游团').first()
            if not tour_business_type:
                flash('未找到旅游团业务类型，请先创建', 'error')
                return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '旅游团订购'),
                ref_type_id=tour_business_type.id,
                description=request.form.get('description', '旅游团订购'),
                supplier_id=(
                    request.form.get('supplier_id')
                    if request.form.get('supplier_id') and request.form.get('supplier_id') != '0'
                    else None
                ),
                leader_name=request.form.get('leader_name', ''),
                contact_name=request.form.get('contact_name'),
                contact_phone=request.form.get('contact_phone'),
                contact_email=request.form.get('contact_email'),
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'draft'),
                payment_status=request.form.get('payment_status', 'unpaid'),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get(
                    'selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id

            db.session.commit()
        flash('旅游团REF保存成功', 'success')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))

    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))


# 保险REF相关函数
@project_ref.route('/insurance/create/<int:header_id>')
def create_insurance_ref(header_id):
    """创建保险REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)
    
        # 获取供应商数据
        suppliers = Supplier.query.all()
        supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
        
        return render_template('business/projects/project_ref/create_insurance_ref.html', 
                             header_id=header_id,
                             suppliers=suppliers, 
                             supplier_types=supplier_types)
    except Exception as e:
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))

@project_ref.route('/insurance/submit', methods=['POST'])
@csrf.exempt
def submit_insurance_ref():
    """提交保险REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')
        
        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            # 更新REF基本信息
            ref.name = request.form.get('name', '保险订单')
            ref.description = request.form.get('description', '保险订单')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.leader_name = request.form.get('leader_name', '')
            ref.contact_name = request.form.get('contact_name')
            ref.contact_phone = request.form.get('contact_phone')
            ref.contact_email = request.form.get('contact_email')
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'draft')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")
            
            # 获取保险业务类型ID
            insurance_business_type = BusinessType.query.filter_by(name='保险').first()
            if not insurance_business_type:
                flash('未找到保险业务类型，请先创建', 'error')
                return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))
            
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '保险订单'),
                ref_type_id=insurance_business_type.id,
                description=request.form.get('description', '保险订单'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None,
                leader_name=request.form.get('leader_name', ''),
                contact_name=request.form.get('contact_name'),
                contact_phone=request.form.get('contact_phone'),
                contact_email=request.form.get('contact_email'),
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'draft'),
                payment_status=request.form.get('payment_status', 'unpaid'),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id
        
            db.session.commit()
        flash('保险REF保存成功', 'success')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))

# 交通REF相关函数
@project_ref.route('/transport/create/<int:header_id>')
def create_transport_ref(header_id):
    """创建交通REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)
    
        # 获取供应商数据
        suppliers = Supplier.query.all()
        supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
        is_create = True
        transport_info = {}
    
        return render_template('business/projects/project_ref/create_transport_ref.html', 
                             header_id=header_id,
                             suppliers=suppliers,
                             supplier_types=supplier_types,
                             is_create=is_create,
                             transport_info=transport_info)
    except Exception as e:
        import traceback
        print(f"交通REF创建页面加载失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        flash(f'页面加载失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))


@project_ref.route('/transport/submit', methods=['POST'])
@csrf.exempt
def submit_transport_ref():
    """提交交通REF数据"""
    try:
        header_id = request.form.get('header_id')
        ref_id = request.form.get('ref_id')

        # 如果是编辑现有REF
        if ref_id:
            ref = ProjectRef.query.get_or_404(ref_id)
            # 更新REF基本信息
            ref.name = request.form.get('name', '交通订单')
            ref.description = request.form.get('description', '交通订单')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                'supplier_id') != '0' else None
            ref.leader_name = request.form.get('leader_name', '')
            ref.contact_name = request.form.get('contact_name')
            ref.contact_phone = request.form.get('contact_phone')
            ref.contact_email = request.form.get('contact_email')
            ref.remarks = request.form.get('remarks')
            ref.status = request.form.get('status', 'draft')
            ref.payment_status = request.form.get('payment_status', 'unpaid')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get(
                'selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
        else:
            # 创建新的REF
            header = ProjectHeader.query.get_or_404(header_id)
            ref_number = ProjectRef.generate_ref_number("")

            # 获取交通业务类型ID
            transport_business_type = BusinessType.query.filter_by(name='交通').first()
            if not transport_business_type:
                flash('未找到交通业务类型，请先创建', 'error')
                return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))

            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=request.form.get('name', '交通订单'),
                ref_type_id=transport_business_type.id,
                description=request.form.get('description', '交通订单'),
                supplier_id=request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get(
                    'supplier_id') != '0' else None,
                leader_name=request.form.get('leader_name', ''),
                contact_name=request.form.get('contact_name'),
                contact_phone=request.form.get('contact_phone'),
                contact_email=request.form.get('contact_email'),
                remarks=request.form.get('remarks'),
                status=request.form.get('status', 'draft'),
                payment_status=request.form.get('payment_status', 'unpaid'),
                selling_price=float(request.form.get('selling_price', 0)) if request.form.get(
                    'selling_price') else None,
                cost_price=float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id

        db.session.commit()
        flash('交通REF保存成功', 'success')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))

    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))


@project_ref.route('/flight/edit/<int:ref_id>')
def edit_flight_ref(ref_id):
    """编辑机票REF页面"""
    from sqlalchemy.orm import joinedload
    
    # 直接查询REF，不需要预加载
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    supplier_types = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
    
    return render_template('business/projects/project_ref/create_flight_ref.html', 
                          header_id=ref.header_id,
                          ref_id=ref.id,
                         ref=ref, 
                          suppliers=suppliers,
                          supplier_types=supplier_types)

@project_ref.route('/flight/detail/<int:ref_id>')
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

@project_ref.route('/hotel/detail/<int:ref_id>')
def hotel_ref_detail(ref_id):
    """酒店REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = Supplier.query.get(ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/hotel_ref_detail.html', 
                         ref=ref, 
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)

@project_ref.route('/visa/detail/<int:ref_id>')
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
    supplier = Supplier.query.get(ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/visa_ref_detail.html', 
                         ref=ref, 
                         visa_info=visa_info,
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)

@project_ref.route('/tour/detail/<int:ref_id>')
def tour_ref_detail(ref_id):
    """旅游团REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = Supplier.query.get(ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/tour_ref_detail.html', 
                         ref=ref, 
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)

@project_ref.route('/insurance/detail/<int:ref_id>')
def insurance_ref_detail(ref_id):
    """保险REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = Supplier.query.get(ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/insurance_ref_detail.html', 
                         ref=ref, 
                         ref_type_name=ref_type_name,
                         supplier_name=supplier_name)

@project_ref.route('/transport/detail/<int:ref_id>')
def transport_ref_detail(ref_id):
    """交通REF详情页面"""
    ref = ProjectRef.query.get_or_404(ref_id)
        
    # 获取业务类型名称
    business_type = BusinessType.query.get(ref.ref_type_id)
    ref_type_name = business_type.name if business_type else None
    
    # 获取供应商名称
    supplier = Supplier.query.get(ref.supplier_id) if ref.supplier_id else None
    supplier_name = supplier.name if supplier else None
    
    return render_template('business/projects/project_ref/transport_ref_detail.html', 
                         ref=ref,
                         ref_type_name=ref_type_name,
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
