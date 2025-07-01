from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from App.models.Flightmodels import FlightOrder, Passenger, FlightSegment, FlightSchedule, AirportData
from App.models.Suppliers import Supplier
from App.models.Visamodels import VisaCountries
from datetime import datetime, timedelta
from App.exts import db, cache
import random
import string

flights_booking = Blueprint('flights_booking', __name__, url_prefix='/flights_booking')

def generate_order_number():
    """生成订单编号：TP + 年月日 + 6位随机数"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.digits, k=6))
    return f'TP{date_str}{random_str}'

@flights_booking.route('/create_order', methods=['GET'])
def create_order():
    """创建订单页面"""
    # 获取所有活跃的供应商
    suppliers = Supplier.query.filter_by(status='active').all()
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_types()
    return render_template('flights/order_create.html', 
                         suppliers=suppliers,
                         supplier_types=supplier_types)

@flights_booking.route('/submit_order', methods=['POST'])
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
        
        # 2. 创建订单主表记录
        passenger_names = request.form.getlist('passenger_name[]')
        if not passenger_names:
            raise ValueError("未提供乘客姓名")
            
        order = FlightOrder(
            order_number=generate_order_number(),
            contact_name=request.form['contact_name'],
            contact_person=request.form['contact_name'],  # 使用联系人姓名作为联系人
            contact_phone=request.form.get('contact_phone', ''),  # 修改为get方法，允许为空
            supplier_name=request.form['supplier_name'],  # Added supplier name
            passenger_name=passenger_names[0],  # 确保使用第一个乘客姓名
            departure_date=first_departure_time.date(),
            departure_city=first_departure_airport,
            arrival_city=last_arrival_airport,
            flight_number=first_flight_number,
            departure_time=first_departure_time,
            status='pending',
            order_status='pending',
            payment_status='unpaid',
            remarks=request.form.get('remarks', '')
        )
        
        print(f"订单基本信息: {order.order_number}")  # 调试日志
        db.session.add(order)
        db.session.flush()  # 获取order.id

        # 3. 处理乘客信息
        total_selling_price = 0
        total_cost_price = 0
        
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

        flash('订单创建成功！', 'success')
        return redirect(url_for('flights_booking.order_detail', order_id=order.id))

    except Exception as e:
        db.session.rollback()
        print(f"订单创建失败: {str(e)}")  # 调试日志
        flash(f'订单创建失败：{str(e)}', 'error')
        return redirect(url_for('flights_booking.create_order'))

@flights_booking.route('/order_detail/<int:order_id>')
def order_detail(order_id):
    """订单详情页面"""
    order = FlightOrder.query.get_or_404(order_id)
    return render_template('flights/order_detail.html', order=order)

@flights_booking.route('/search_flights', methods=['POST'])
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
def order_list():
    """订单列表页面"""
    # 获取搜索参数
    order_number = request.args.get('order_number', '')
    contact_name = request.args.get('contact_name', '')
    order_status = request.args.get('order_status', '')
    payment_status = request.args.get('payment_status', '')
    supplier_name = request.args.get('supplier_name', '')
    departure_filter = request.args.get('departure_filter', '')
    page = request.args.get('page', 1, type=int)

    # 获取所有国家信息
    countries = VisaCountries.query.all()

    # 构建查询
    query = FlightOrder.query
    
    # 处理出发日期过滤
    today = datetime.now().date()
    if departure_filter == 'today':
        # 今日出发
        query = query.filter(FlightOrder.departure_date == today)
    elif departure_filter == 'upcoming':
        # 未来3天内出发
        three_days_later = today + timedelta(days=3)
        query = query.filter(FlightOrder.departure_date.between(today, three_days_later))
    
    if order_number:
        query = query.filter(FlightOrder.order_number.like(f'%{order_number}%'))
    if contact_name:
        query = query.filter(FlightOrder.contact_person.like(f'%{contact_name}%'))
    
    # 修复订单状态筛选逻辑
    if order_status and order_status != 'all':
        # 用户选择了特定的订单状态
        query = query.filter(FlightOrder.order_status == order_status)
    elif 'order_status' not in request.args or request.args.get('order_status') == '':
        # 如果URL中没有order_status参数或者参数为空值，应用默认过滤（排除已取消订单）
        query = query.filter(FlightOrder.order_status != 'cancelled')
    
    if payment_status:
        query = query.filter(FlightOrder.payment_status == payment_status)
    if supplier_name:
        query = query.filter(FlightOrder.supplier_name == supplier_name)

    # 获取所有活跃的供应商列表供筛选使用
    suppliers = Supplier.query.filter_by(status='active').all()

    # 按创建时间倒序排序并分页
    orders = query.order_by(FlightOrder.created_date.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    return render_template('flights/order_list.html', 
                         orders=orders, 
                         suppliers=suppliers,
                         countries=countries)

@flights_booking.route('/edit_order/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    """编辑订单"""
    order = FlightOrder.query.get_or_404(order_id)
    
    if request.method == 'POST':
        try:
            print("=== Starting order edit process ===")
            print("Original order data:")
            print(f"Order ID: {order.id}")
            print(f"Original supplier: {order.supplier_name}")
            
            # 更新订单基本信息
            order.contact_name = request.form['contact_name']
            order.contact_person = request.form['contact_name']
            order.contact_phone = request.form['contact_phone']
            
            # 更新供应商名称
            supplier_name = request.form.get('supplier_name')
            print(f"Received supplier name: {supplier_name}")
            if supplier_name:
                order.supplier_name = supplier_name
                print(f"Setting supplier name to: {supplier_name}")
            
            order.remarks = request.form.get('remarks', '')
            
            # 更新乘客信息
            print("Updating passenger information...")
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

            # 计算总价
            total_selling_price = 0
            total_cost_price = 0

            # 确保所有列表长度一致
            if not (len(passenger_names) == len(passenger_types) == 
                   len(selling_prices) == len(cost_prices)):
                raise ValueError("乘客信息数据不完整")

            # 更新现有乘客信息
            for i, passenger in enumerate(order.passengers):
                if i < len(passenger_names):
                    print(f"Updating passenger {i+1}: {passenger_names[i]}")
                    passenger.name = passenger_names[i]
                    passenger.passenger_type = passenger_types[i]
                    passenger.selling_price = float(selling_prices[i])
                    passenger.cost_price = float(cost_prices[i])
                    passenger.ticket_number = ticket_numbers[i] if ticket_numbers[i] else None
                    passenger.pnr = pnrs[i] if pnrs[i] else None
                    total_selling_price += float(selling_prices[i])
                    total_cost_price += float(cost_prices[i])
                else:
                    # 如果提交的乘客数量少于原有数量，删除多余的乘客
                    print(f"Removing excess passenger: {passenger.name}")
                    db.session.delete(passenger)

            # 添加新增的乘客
            for i in range(len(order.passengers), len(passenger_names)):
                print(f"Adding new passenger: {passenger_names[i]}")
                new_passenger = Passenger(
                    order_id=order.id,
                    name=passenger_names[i],
                    passenger_type=passenger_types[i],
                    selling_price=float(selling_prices[i]),
                    cost_price=float(cost_prices[i]),
                    ticket_number=ticket_numbers[i] if ticket_numbers[i] else None,
                    pnr=pnrs[i] if pnrs[i] else None
                )
                db.session.add(new_passenger)
                total_selling_price += float(selling_prices[i])
                total_cost_price += float(cost_prices[i])

            # 更新订单总价
            print(f"Updating order prices - Selling: {total_selling_price}, Cost: {total_cost_price}")
            order.selling_price = total_selling_price
            order.cost_price = total_cost_price
            
            # 提交事务
            print("Committing transaction...")
            db.session.commit()
            print("Transaction committed successfully")
            
            flash('订单更新成功！', 'success')
            return redirect(url_for('flights_booking.order_list'))

        except Exception as e:
            print(f"Error during order update: {str(e)}")
            db.session.rollback()
            flash(f'订单更新失败：{str(e)}', 'error')
            return redirect(url_for('flights_booking.edit_order', order_id=order.id))

    # GET 请求，显示编辑表单
    airports = AirportData.query.all()
    suppliers = Supplier.query.filter_by(status='active').all()
    supplier_types = dict(Supplier.get_supplier_type_choices())  # 获取供应商类型选项
    return render_template('flights/order_edit.html', 
                         order=order, 
                         airports=airports, 
                         suppliers=suppliers,
                         supplier_types=supplier_types)

@flights_booking.route('/update_order_status/<int:order_id>', methods=['POST'])
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