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
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))


# 酒店REF相关函数
@project_ref.route('/hotel/create/<int:header_id>', methods=['GET'])
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
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

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
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    except Exception as e:
        import traceback
        print(f"酒店REF提交失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))


# 签证REF相关函数
@project_ref.route('/visa/create/<int:header_id>', methods=['GET'])
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
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))
            
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
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

# 旅游团REF相关函数
@project_ref.route('/tour/create/<int:header_id>', methods=['GET', 'POST'])
@csrf.exempt
def create_tour_ref(header_id):
    """创建旅游团REF页面"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)
        
        if request.method == 'POST':
            # 处理POST请求 - 创建旅游团REF
            try:
                ref_number = ProjectRef.generate_ref_number("")

                # 获取旅游团业务类型ID（优先按code查询，避免名称差异导致ID不一致）
                tour_business_type = BusinessType.query.filter_by(code='tour').first()
                if not tour_business_type:
                    tour_business_type = BusinessType.query.filter_by(name='旅游团').first()
                if not tour_business_type:
                    flash('未找到旅游团业务类型，请先创建', 'error')
                    return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

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
                db.session.commit()
                
                flash('旅游团REF创建成功', 'success')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'创建失败：{str(e)}', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))
        
        # GET请求 - 显示创建页面
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

            # 获取旅游团业务类型ID（优先按code查询，避免名称差异导致ID不一致）
            tour_business_type = BusinessType.query.filter_by(code='tour').first()
            if not tour_business_type:
                tour_business_type = BusinessType.query.filter_by(name='旅游团').first()
            if not tour_business_type:
                flash('未找到旅游团业务类型，请先创建', 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

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
        return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

    except Exception as e:
        db.session.rollback()
        flash(f'保存失败：{str(e)}', 'error')
        return redirect(url_for('business_projects.detail.project_detail', header_id=header_id))


# 保险REF相关函数
@project_ref.route('/insurance/create/<int:header_id>', methods=['GET'])
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
@project_ref.route('/transport/create/<int:header_id>', methods=['GET'])
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


@project_ref.route('/flight/edit/<int:ref_id>', methods=['GET'])
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
    supplier = Supplier.query.get(ref.supplier_id) if ref.supplier_id else None
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
    supplier = Supplier.query.get(ref.supplier_id) if ref.supplier_id else None
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
            # 更新REF数据
            ref.name = request.form.get('name', '签证服务')
            ref.description = request.form.get('description', '签证服务')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.supplier_phone = request.form.get('supplier_phone', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            
            # 处理日期字段，空字符串转换为None
            expected_date = request.form.get('expected_delivery_date')
            ref.expected_delivery_date = datetime.strptime(expected_date, '%Y-%m-%d').date() if expected_date else None
            
            actual_date = request.form.get('actual_delivery_date')
            ref.actual_delivery_date = datetime.strptime(actual_date, '%Y-%m-%d').date() if actual_date else None
            
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            # 处理签证专属字段
            visa_extra_info = {
                'country': request.form.get('country', ''),
                'visa_type': request.form.get('visa_type', ''),
                'applicant_info': request.form.get('applicant_info', '')
            }
            ref.extra_info = json.dumps(visa_extra_info)
            
            # 同步更新相关EO的价格
            from App_new.business.projects.models.eo import ProjectEO
            ProjectEO.sync_eo_prices_from_ref(ref.id, ref.cost_price, ref.currency)
            flash('签证REF更新成功', 'success')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    # 获取所有国家数据
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    
    # 解析签证专属信息
    visa_info = {}
    if ref and ref.extra_info:
        try:
            visa_info = json.loads(ref.extra_info)
        except json.JSONDecodeError:
            visa_info = {}
    
    return render_template('business/projects/project_ref/create_visa_ref.html', 
                         ref=ref, 
                         suppliers=suppliers,
                         countries=countries,
                         visa_info=visa_info,
                         is_create=False)

@project_ref.route('/tour/detail/<int:ref_id>', methods=['GET'])
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

@project_ref.route('/insurance/detail/<int:ref_id>', methods=['GET'])
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

@project_ref.route('/transport/detail/<int:ref_id>', methods=['GET'])
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

@project_ref.route('/other/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_other_ref(ref_id):
    """编辑其他类型REF"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是其他类型的REF
    business_type = BusinessType.query.get(ref.ref_type_id)
    if not business_type or business_type.name != '其他':
        flash('只能编辑其他类型的REF', 'error')
        return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 更新REF数据
            ref.name = request.form.get('name', '其他服务')
            ref.description = request.form.get('description', '其他服务')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.supplier_phone = request.form.get('supplier_phone', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            
            # 处理日期字段，空字符串转换为None
            expected_date = request.form.get('expected_delivery_date')
            ref.expected_delivery_date = datetime.strptime(expected_date, '%Y-%m-%d').date() if expected_date else None
            
            actual_date = request.form.get('actual_delivery_date')
            ref.actual_delivery_date = datetime.strptime(actual_date, '%Y-%m-%d').date() if actual_date else None
            
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            # 同步更新相关EO的价格
            from App_new.business.projects.models.eo import ProjectEO
            ProjectEO.sync_eo_prices_from_ref(ref.id, ref.cost_price, ref.currency)
            flash('其他REF更新成功', 'success')
            return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
    
    # 获取供应商数据与项目头信息（有些模板/基类可能需要 header）
    suppliers = Supplier.query.all()
    header = ProjectHeader.query.get(ref.header_id)
    
    return render_template(
        'business/projects/project_ref/create_tour_ref.html',
        ref=ref,
        suppliers=suppliers,
        header=header,
        header_id=ref.header_id,
        is_create=False
    )

@project_ref.route('/insurance/edit/<int:ref_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_insurance_ref(ref_id):
    """编辑保险REF"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    # 确保这是保险类型的REF
    business_type = BusinessType.query.get(ref.ref_type_id)
    if not business_type or business_type.name != '保险':
        flash('只能编辑保险类型的REF', 'error')
        return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 更新REF数据
            ref.name = request.form.get('name', '保险服务')
            ref.description = request.form.get('description', '保险服务')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.supplier_phone = request.form.get('supplier_phone', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            
            # 处理日期字段，空字符串转换为None
            expected_date = request.form.get('expected_delivery_date')
            ref.expected_delivery_date = datetime.strptime(expected_date, '%Y-%m-%d').date() if expected_date else None
            
            actual_date = request.form.get('actual_delivery_date')
            ref.actual_delivery_date = datetime.strptime(actual_date, '%Y-%m-%d').date() if actual_date else None
            
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            # 同步更新相关EO的价格
            from App_new.business.projects.models.eo import ProjectEO
            ProjectEO.sync_eo_prices_from_ref(ref.id, ref.cost_price, ref.currency)
            flash('保险REF更新成功', 'success')
            return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
    
    # 获取供应商数据
    suppliers = Supplier.query.all()
    
    return render_template('business/projects/project_ref/create_ref.html', 
                         ref=ref, 
                         suppliers=suppliers,
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
        return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
    
    if request.method == 'POST':
        try:
            # 更新REF数据
            ref.name = request.form.get('name', '旅游团服务')
            ref.description = request.form.get('description', '旅游团服务')
            ref.supplier_id = request.form.get('supplier_id') if request.form.get('supplier_id') and request.form.get('supplier_id') != '0' else None
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.supplier_phone = request.form.get('supplier_phone', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            
            # 处理日期字段，空字符串转换为None
            expected_date = request.form.get('expected_delivery_date')
            ref.expected_delivery_date = datetime.strptime(expected_date, '%Y-%m-%d').date() if expected_date else None
            
            actual_date = request.form.get('actual_delivery_date')
            ref.actual_delivery_date = datetime.strptime(actual_date, '%Y-%m-%d').date() if actual_date else None
            
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            # 同步更新相关EO的价格
            from App_new.business.projects.models.eo import ProjectEO
            ProjectEO.sync_eo_prices_from_ref(ref.id, ref.cost_price, ref.currency)
            flash('旅游团REF更新成功', 'success')
            return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.project_header.header_detail', header_id=ref.header_id))
    
    # 获取供应商数据
    header = ProjectHeader.query.get(ref.header_id)  # 获取header对象
    suppliers = Supplier.query.all()
    
    return render_template('business/projects/project_ref/create_tour_ref.html',
                         header=header,  # 传入header
                         header_id=ref.header_id,  # 传入header_id
                         ref=ref,
                         suppliers=suppliers,
                         is_create=False)

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
        
        # 构建查询
        query = db.session.query(
            ProjectRef,
            BusinessType.name.label('business_type_name'),
            Supplier.name.label('supplier_name'),
            ProjectHeader.desc.label('project_name')
        ).join(
            BusinessType, ProjectRef.ref_type_id == BusinessType.id, isouter=True
        ).join(
            Supplier, ProjectRef.supplier_id == Supplier.supplier_id, isouter=True
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
            filters.append(ProjectRef.leader_name.ilike(f'%{leader_name}%'))
        
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
                ProjectRef.name.ilike(f'%{keyword}%'),
                ProjectRef.description.ilike(f'%{keyword}%'),
                ProjectRef.ref_number.ilike(f'%{keyword}%'),
                ProjectRef.leader_name.ilike(f'%{keyword}%'),
                ProjectHeader.desc.ilike(f'%{keyword}%')
            )
            filters.append(keyword_filter)
        
        # 应用筛选条件
        if filters:
            query = query.filter(and_(*filters))
        
        # 排序
        if sort_by == 'created_at':
            order_column = ProjectRef.created_at
        elif sort_by == 'name':
            order_column = ProjectRef.name
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
            ref_dict = {
                'id': ref.id,
                'ref_number': str(ref.ref_number) if ref.ref_number else '',
                'name': str(ref.name) if ref.name else '',
                'description': str(ref.description) if ref.description else '',
                'business_type_name': str(business_type_name) if business_type_name else '未知',
                'business_type_color': get_business_type_color(business_type_name),
                'header_id': ref.header_id,
                'project_name': str(project_name) if project_name else f'项目{ref.header_id}',
                'supplier_name': str(supplier_name) if supplier_name else '',
                'leader_name': str(ref.leader_name) if ref.leader_name else '',
                'status': str(ref.status) if ref.status else 'draft',
                'status_display': get_status_display(ref.status),
                'status_color': get_status_color(ref.status),
                'selling_price': float(ref.selling_price) if ref.selling_price is not None else 0,
                'cost_price': float(ref.cost_price) if ref.cost_price is not None else 0,
                'created_at': ref.created_at
            }
            refs.append(ref_dict)
        
        # 获取筛选选项数据
        business_types = BusinessType.query.order_by(BusinessType.name).all()
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
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
    """编辑通用REF"""
    ref = ProjectRef.query.get_or_404(ref_id)
    
    if request.method == 'POST':
        try:
            # 调试：打印所有表单数据
            print(f"DEBUG: All form data: {dict(request.form)}")
            
            # 更新REF数据
            ref.name = request.form.get('name', 'REF服务')
            ref.description = request.form.get('description', 'REF服务')
            supplier_id = request.form.get('supplier_id')
            print(f"DEBUG: supplier_id from form: {supplier_id}, type: {type(supplier_id)}")
            ref.supplier_id = int(supplier_id) if supplier_id and supplier_id != '0' else None
            print(f"DEBUG: ref.supplier_id after update: {ref.supplier_id}")
            ref.supplier_contact = request.form.get('supplier_contact', '')
            ref.supplier_phone = request.form.get('supplier_phone', '')
            ref.leader_name = request.form.get('leader_name', '')
            ref.selling_price = float(request.form.get('selling_price', 0)) if request.form.get('selling_price') else None
            ref.cost_price = float(request.form.get('cost_price', 0)) if request.form.get('cost_price') else None
            
            # 处理日期字段，空字符串转换为None
            expected_date = request.form.get('expected_delivery_date')
            ref.expected_delivery_date = datetime.strptime(expected_date, '%Y-%m-%d').date() if expected_date else None
            
            actual_date = request.form.get('actual_delivery_date')
            ref.actual_delivery_date = datetime.strptime(actual_date, '%Y-%m-%d').date() if actual_date else None
            
            ref.status = request.form.get('status') or 'draft'
            ref.remarks = request.form.get('remarks', '')
            
            # 同步更新相关EO的价格
            from App_new.business.projects.models.eo import ProjectEO
            ProjectEO.sync_eo_prices_from_ref(ref.id, ref.cost_price, ref.currency)
            
            # 提交数据库更改
            db.session.commit()
            
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=ref.header_id))
    
    # 获取供应商数据和项目头部信息
    suppliers = Supplier.query.all()
    header = ProjectHeader.query.get(ref.header_id)
    
    # 创建表单对象用于编辑模式
    from App_new.business.projects.forms.ref_forms import ProjectRefForm
    form = ProjectRefForm()
    
    # 预填充表单数据
    form.ref_number.data = ref.ref_number
    form.name.data = ref.name
    form.description.data = ref.description
    form.ref_type_id.data = ref.ref_type_id
    form.supplier_id.data = ref.supplier_id
    form.supplier_contact.data = ref.supplier_contact
    form.supplier_phone.data = ref.supplier_phone
    form.leader_name.data = ref.leader_name
    form.selling_price.data = ref.selling_price
    form.cost_price.data = ref.cost_price
    form.currency.data = ref.currency
    form.expected_delivery_date.data = ref.expected_delivery_date
    form.actual_delivery_date.data = ref.actual_delivery_date
    form.status.data = ref.status
    form.payment_status.data = ref.payment_status
    form.remarks.data = ref.remarks
    
    return render_template('business/projects/project_ref/create_ref.html', 
                         ref=ref, 
                         header=header,
                         suppliers=suppliers,
                         form=form,
                         is_create=False)
