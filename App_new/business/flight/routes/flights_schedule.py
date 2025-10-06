from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from ..models.models import FlightSchedule, AirportData
from sqlalchemy.exc import IntegrityError
from App_new.exts import db
from App_new.utils.decorators import staff_only
from sqlalchemy import text
import re

flights_schedule = Blueprint('flights_schedule', __name__)


def _enrich_with_airport_scrapers(payload: dict, dep_iata: str = None, arr_iata: str = None, flight_number: str = None, flight_date: str = None) -> dict:
    """使用机场官网抓取器补全 terminal/gate（仅在字段为 Unknown 时尝试）。"""
    try:
        if not payload:
            return payload

        # 解析 IATA
        dep = (dep_iata or '').upper() if dep_iata else None
        arr = (arr_iata or '').upper() if arr_iata else None

        # 若仍未知，从 schedule_city 拆分
        if (not dep or not arr) and payload.get('schedule_city'):
            parts = payload['schedule_city'].split()
            if len(parts) >= 2:
                dep = dep or parts[0].upper()
                arr = arr or parts[1].upper()

        # SIN 抓取
        try:
            from App_new.utils.scrapers.sin_changi import fetch_terminal_gate as sin_fetch
            if dep == 'SIN' and (payload.get('departure_terminal') == 'Unknown' or payload.get('departure_gate') == 'Unknown'):
                res = sin_fetch(flight_number or payload.get('flight_number', ''), flight_date, 'departures')
                if res:
                    if payload.get('departure_terminal') == 'Unknown' and res.get('departure_terminal'):
                        payload['departure_terminal'] = res['departure_terminal']
                    if payload.get('departure_gate') == 'Unknown' and res.get('departure_gate'):
                        payload['departure_gate'] = res['departure_gate']
            if arr == 'SIN' and (payload.get('arrival_terminal') == 'Unknown' or payload.get('arrival_gate') == 'Unknown'):
                res = sin_fetch(flight_number or payload.get('flight_number', ''), flight_date, 'arrivals')
                if res:
                    if payload.get('arrival_terminal') == 'Unknown' and res.get('arrival_terminal'):
                        payload['arrival_terminal'] = res['arrival_terminal']
                    if payload.get('arrival_gate') == 'Unknown' and res.get('arrival_gate'):
                        payload['arrival_gate'] = res['arrival_gate']
        except Exception:
            pass

        # PVG 抓取
        try:
            from App_new.utils.scrapers.pvg_pudong import fetch_terminal_gate as pvg_fetch
            if dep == 'PVG' and (payload.get('departure_terminal') == 'Unknown' or payload.get('departure_gate') == 'Unknown'):
                res = pvg_fetch(flight_number or payload.get('flight_number', ''), flight_date, 'departures')
                if res:
                    if payload.get('departure_terminal') == 'Unknown' and (res.get('departure_terminal') or res.get('terminal')):
                        payload['departure_terminal'] = res.get('departure_terminal') or res.get('terminal')
                    if payload.get('departure_gate') == 'Unknown' and (res.get('departure_gate') or res.get('gate')):
                        payload['departure_gate'] = res.get('departure_gate') or res.get('gate')
            if arr == 'PVG' and (payload.get('arrival_terminal') == 'Unknown' or payload.get('arrival_gate') == 'Unknown'):
                res = pvg_fetch(flight_number or payload.get('flight_number', ''), flight_date, 'arrivals')
                if res:
                    if payload.get('arrival_terminal') == 'Unknown' and (res.get('arrival_terminal') or res.get('terminal')):
                        payload['arrival_terminal'] = res.get('arrival_terminal') or res.get('terminal')
                    if payload.get('arrival_gate') == 'Unknown' and (res.get('arrival_gate') or res.get('gate')):
                        payload['arrival_gate'] = res.get('arrival_gate') or res.get('gate')
        except Exception:
            pass

        return payload
    except Exception:
        return payload

@flights_schedule.route('/input_airport_code', methods=['GET'])
@login_required
@staff_only
def input_airport_code():
    """机场代码输入页面"""
    # 获取机场数据列表（加入分页）
    page = request.args.get('page', 1, type=int)
    per_page = 10
    airports = AirportData.query.order_by(AirportData.airport_IATA).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('business/flight/flight_airport_code_input.html', airports=airports)

@flights_schedule.route('/itinerary_conversion', methods=['GET', 'POST'])
@login_required
@staff_only
def itinerary_conversion():
    """行程转换功能"""
    if request.method == 'POST':
        # 这里处理行程转换的POST请求逻辑
        # 简单返回一个JSON响应作为示例
        return jsonify({'success': True, 'message': '行程转换处理成功'})
    
    # GET请求返回行程转换页面
    return render_template('business/flight/flight_conversion.html')

@flights_schedule.route('/confirmation_detail/<int:order_id>', methods=['GET'])
@login_required
@staff_only
def confirmation_detail(order_id):
    """显示机票确认单详细信息"""
    # 在实际应用中，这里应该从数据库中获取确认单信息
    # 目前只是返回一个带有订单ID的模板
    return render_template('business/flight/flight_confirmation_detail.html', order_id=order_id)

@flights_schedule.route('/confirmation_detail', methods=['GET'])
@login_required
@staff_only
def confirmation_detail_default():
    """显示默认的确认单页面（无订单ID）"""
    return render_template('business/flight/flight_confirmation_detail.html')

@flights_schedule.route('/simple_itinerary', methods=['GET'])
@login_required
@staff_only
def simple_itinerary():
    """简化行程页面"""
    return render_template('business/flight/flight_itinerary_simple.html')

@flights_schedule.route('/simplify_itinerary', methods=['POST'])
@login_required
@staff_only
def simplify_itinerary_by_flight_and_date():
    """处理简化行程表单提交"""
    try:
        # 获取表单数据
        itinerary_text = request.form.get('itinerary_text', '')
        
        if not itinerary_text:
            flash('请输入需要简化的行程信息', 'error')
            return redirect(url_for('flights_schedule.simple_itinerary'))
        
        # 这里应该有处理行程简化的逻辑
        # 实际项目中这里可能有更复杂的处理逻辑
        simplified_text = process_itinerary(itinerary_text)
        
        # 返回结果到模板
        return render_template('business/flight/flight_itinerary_simple.html', 
                               original_text=itinerary_text,
                               simplified_text=simplified_text)
        
    except Exception as e:
        flash(f'处理行程时出错: {str(e)}', 'error')
        return redirect(url_for('flights_schedule.simple_itinerary'))
        
def process_itinerary(text):
    """简单处理行程文本的函数"""
    # 这只是一个占位实现，实际项目中应该有更复杂的逻辑
    # 例如提取日期、航班号等信息，并按特定格式重新组织
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        # 简单处理：尝试提取日期和航班号
        # 实际应用中可能需要更复杂的正则表达式和处理逻辑
        line = line.strip()
        if line:
            processed_lines.append(f"处理后: {line}")
    
    return '\n'.join(processed_lines)

@flights_schedule.route('/input_flight_schedule', methods=['GET', 'POST'])
@login_required
@staff_only
def input_flight_schedule():
    """航班时刻表输入页面"""
    if request.method == 'GET':
        search_flight_number = request.args.get('search_flight_number', '')
        search_airline_code = request.args.get('search_airline_code', '')
        search_airline_num = request.args.get('search_airline_num', '')
        search_schedule_city = request.args.get('search_schedule_city', '')
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 构建查询
        query = FlightSchedule.query
        
        # 如果有搜索条件，添加过滤
        if search_flight_number:
            query = query.filter(FlightSchedule.flight_number.like(f"%{search_flight_number}%"))
        if search_airline_code:
            query = query.filter(FlightSchedule.airline_code.like(f"%{search_airline_code}%"))
        if search_airline_num:
            query = query.filter(FlightSchedule.airline_num.like(f"%{search_airline_num}%"))
        if search_schedule_city:
            query = query.filter(FlightSchedule.schedule_city.like(f"%{search_schedule_city}%"))
        
        # 添加排序并分页
        flights = query.order_by(FlightSchedule.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        
        return render_template('business/flight/flight_schedule_input.html',
                               search_flight_number=search_flight_number,
                               search_airline_code=search_airline_code,
                               search_airline_num=search_airline_num,
                               search_schedule_city=search_schedule_city,
                               flights=flights)
    
    elif request.method == 'POST':
        try:
            flight_numbers = request.form.getlist('flight_number[]')
            airline_codes = request.form.getlist('airline_code[]')
            airline_nums = request.form.getlist('airline_num[]')
            schedule_cities = request.form.getlist('schedule_city[]')
            schedule_timings = request.form.getlist('schedule_timing[]')
            # 新增字段
            departure_terminals = request.form.getlist('departure_terminal[]')
            departure_gates = request.form.getlist('departure_gate[]')
            arrival_terminals = request.form.getlist('arrival_terminal[]')
            arrival_gates = request.form.getlist('arrival_gate[]')
            aircrafts = request.form.getlist('aircraft[]')
            statuses = request.form.getlist('status[]')
            
            # 验证数据
            if not flight_numbers or len(flight_numbers) != len(schedule_cities) or len(flight_numbers) != len(schedule_timings):
                flash('提交的数据不完整或格式错误', 'error')
                return redirect(url_for('flights_schedule.input_flight_schedule'))
            
            # 保存到数据库
            success_count = 0
            for i in range(len(flight_numbers)):
                if flight_numbers[i] and schedule_cities[i] and schedule_timings[i]:
                    flight_number = flight_numbers[i].strip().upper()
                    airline_code = airline_codes[i].strip().upper() if airline_codes and i < len(airline_codes) else flight_number[:2]
                    airline_num = airline_nums[i].strip() if airline_nums and i < len(airline_nums) else flight_number[2:]
                    # 安全获取新增字段
                    dep_terminal = (departure_terminals[i].strip() if departure_terminals and i < len(departure_terminals) and departure_terminals[i] else 'Unknown')
                    dep_gate = (departure_gates[i].strip() if departure_gates and i < len(departure_gates) and departure_gates[i] else 'Unknown')
                    arr_terminal = (arrival_terminals[i].strip() if arrival_terminals and i < len(arrival_terminals) and arrival_terminals[i] else 'Unknown')
                    arr_gate = (arrival_gates[i].strip() if arrival_gates and i < len(arrival_gates) and arrival_gates[i] else 'Unknown')
                    aircraft = (aircrafts[i].strip() if aircrafts and i < len(aircrafts) and aircrafts[i] else 'Unknown')
                    status = (statuses[i].strip() if statuses and i < len(statuses) and statuses[i] else 'Unknown')
                    
                    # 检查是否已存在相同航班号的记录
                    existing = FlightSchedule.query.filter_by(flight_number=flight_number).first()
                    if existing:
                        # 更新现有记录
                        existing.schedule_city = schedule_cities[i]
                        existing.schedule_timing = schedule_timings[i]
                        existing.airline_code = airline_code
                        existing.airline_num = airline_num
                        existing.departure_terminal = dep_terminal
                        existing.departure_gate = dep_gate
                        existing.arrival_terminal = arr_terminal
                        existing.arrival_gate = arr_gate
                        existing.aircraft = aircraft
                        existing.status = status
                    else:
                        # 创建新记录
                        new_flight = FlightSchedule(
                            flight_number=flight_number,
                            airline_code=airline_code,
                            airline_num=airline_num,
                            schedule_city=schedule_cities[i],
                            schedule_timing=schedule_timings[i],
                            departure_terminal=dep_terminal,
                            departure_gate=dep_gate,
                            arrival_terminal=arr_terminal,
                            arrival_gate=arr_gate,
                            aircraft=aircraft,
                            status=status
                        )
                        db.session.add(new_flight)
                    
                    success_count += 1
            
            # 提交事务
            db.session.commit()
            flash(f'成功保存 {success_count} 条航班信息', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'保存失败: {str(e)}', 'error')
            current_app.logger.error(f'保存航班信息失败: {str(e)}')
        
        return redirect(url_for('flights_schedule.input_flight_schedule'))

@flights_schedule.route('/input_flight_schedule_info', methods=['GET', 'POST'])
@login_required
@staff_only
def input_flight_schedule_info():
    """航班时刻表输入页面"""
    if request.method == 'GET':
        search_flight_number = request.args.get('search_flight_number', '')
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        query = FlightSchedule.query
        
        # 如果有搜索条件，添加过滤
        if search_flight_number:
            query = query.filter(FlightSchedule.flight_number.like(f"%{search_flight_number}%"))
            
        # 添加排序并分页
        flights = query.order_by(FlightSchedule.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        
        return render_template('business/flight/flight_schedule_input.html',
                           search_flight_number=search_flight_number,
                           flights=flights)
    
    elif request.method == 'POST':
        try:
            flight_numbers = request.form.getlist('flight_number[]')
            airline_codes = request.form.getlist('airline_code[]')
            airline_nums = request.form.getlist('airline_num[]')
            schedule_cities = request.form.getlist('schedule_city[]')
            schedule_timings = request.form.getlist('schedule_timing[]')
            
            # 验证数据
            if not flight_numbers or len(flight_numbers) != len(schedule_cities) or len(flight_numbers) != len(schedule_timings):
                flash('提交的数据不完整或格式错误', 'error')
                return redirect(url_for('flights_schedule.input_flight_schedule_info'))
            
            # 保存到数据库
            success_count = 0
            for i in range(len(flight_numbers)):
                if flight_numbers[i] and schedule_cities[i] and schedule_timings[i]:
                    flight_number = flight_numbers[i].strip().upper()
                    airline_code = airline_codes[i].strip().upper() if airline_codes and i < len(airline_codes) else flight_number[:2]
                    airline_num = airline_nums[i].strip() if airline_nums and i < len(airline_nums) else flight_number[2:]
                    
                    # 检查是否已存在相同航班号的记录
                    existing = FlightSchedule.query.filter_by(flight_number=flight_number).first()
                    if existing:
                        # 更新现有记录
                        existing.schedule_city = schedule_cities[i]
                        existing.schedule_timing = schedule_timings[i]
                        existing.airline_code = airline_code
                        existing.airline_num = airline_num
                        db.session.add(existing)
                    else:
                        # 创建新记录
                        flight_schedule = FlightSchedule(
                            flight_number=flight_number,
                            airline_code=airline_code,
                            airline_num=airline_num,
                            schedule_city=schedule_cities[i],
                            schedule_timing=schedule_timings[i]
                        )
                        db.session.add(flight_schedule)
                    
                    success_count += 1
            
            # 提交事务
            db.session.commit()
            
            if success_count > 0:
                flash(f'成功保存了 {success_count} 条航班信息', 'success')
            else:
                flash('没有有效的航班信息被保存', 'warning')
            
            # 保持搜索条件
            search_flight_number = request.form.get('search_flight_number', '')
            return redirect(url_for('flights_schedule.input_flight_schedule_info', 
                                  search_flight_number=search_flight_number))
            
        except Exception as e:
            # 回滚事务
            db.session.rollback()
            flash(f'保存航班信息时出错: {str(e)}', 'error')
            return redirect(url_for('flights_schedule.input_flight_schedule_info'))

@flights_schedule.route('/get-flight-info', methods=['GET'])
@login_required
@staff_only
def get_flight_info():
    """获取航班信息"""
    flight_number = request.args.get('flight_number', '').strip().upper()
    source = request.args.get('source', '').strip().lower()  # 可选：指定数据源 ('aviationstack' / 'fr24')
    # 可选：增强查询参数
    dep_iata = request.args.get('dep_iata', '').strip().upper() or None
    arr_iata = request.args.get('arr_iata', '').strip().upper() or None
    flight_date = request.args.get('flight_date', '').strip() or None
    schedule_city = request.args.get('schedule_city', '').strip().upper()
    if (not dep_iata or not arr_iata) and schedule_city:
        parts = schedule_city.split()
        if len(parts) >= 2:
            dep_iata = dep_iata or parts[0]
            arr_iata = arr_iata or parts[1]

    # 若未显式提供日期：默认使用 “今天+1天”
    if not flight_date:
        try:
            from datetime import datetime, timedelta
            flight_date = (datetime.utcnow().date() + timedelta(days=1)).isoformat()
        except Exception:
            flight_date = None
    
    if not flight_number:
        return jsonify({
            'success': False,
            'message': '请提供航班号',
            'data': None
        })
    
    try:
        # 如果没有提供IATA代码，尝试从航班号推断
        if not dep_iata or not arr_iata:
            # 常见航班的航线映射
            flight_routes = {
                'TR156': {'dep_iata': 'SIN', 'arr_iata': 'SHE'},
                'SQ876': {'dep_iata': 'SIN', 'arr_iata': 'TPE'},
                'MU544': {'dep_iata': 'SIN', 'arr_iata': 'PVG'},
                'CA976': {'dep_iata': 'PEK', 'arr_iata': 'FRA'},
                'CZ3001': {'dep_iata': 'CAN', 'arr_iata': 'PVG'},
            }
            
            if flight_number in flight_routes:
                route = flight_routes[flight_number]
                dep_iata = dep_iata or route['dep_iata']
                arr_iata = arr_iata or route['arr_iata']
                print(f"DEBUG: 从航班号推断航线 {flight_number}: {dep_iata} -> {arr_iata}")
        
        # 只使用Aerodatabox作为唯一数据源
        from App_new.utils.flightaerodatabox import get_flight_info_aerodatabox
        from datetime import datetime, timedelta
        
        aero_data = None
        dates_to_try = []
        
        # 如果指定了日期，先尝试该日期
        if flight_date:
            dates_to_try.append(flight_date)
        
        # 添加今天、昨天、明天作为备选
        today = datetime.utcnow().strftime('%Y-%m-%d')
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        for date in [today, yesterday, tomorrow]:
            if date not in dates_to_try:
                dates_to_try.append(date)
        
        # 尝试不同日期
        for date_to_try in dates_to_try:
            print(f"DEBUG: 尝试日期 {date_to_try}")
            aero_data = get_flight_info_aerodatabox(
                flight_number,
                dep_iata=dep_iata,
                arr_iata=arr_iata,
                flight_date=date_to_try,
                use_rapidapi=True,
            )
            if aero_data:
                print(f"DEBUG: 在日期 {date_to_try} 找到航班数据")
                break
        
        if not aero_data:
            print(f"DEBUG: 在所有尝试的日期中都未找到航班数据: {dates_to_try}")
        
        if aero_data:
            payload = {
                'flight_number': flight_number,
                'airline_code': flight_number[:2] if len(flight_number) >= 2 else '',
                'airline_num': flight_number[2:] if len(flight_number) >= 2 else '',
                'schedule_city': aero_data.get('schedule_city', ''),
                'schedule_timing': aero_data.get('schedule_timing', ''),
                'departure_terminal': aero_data.get('departure_terminal', 'Unknown'),
                'departure_gate': aero_data.get('departure_gate', 'Unknown'),
                'arrival_terminal': aero_data.get('arrival_terminal', 'Unknown'),
                'arrival_gate': aero_data.get('arrival_gate', 'Unknown'),
                'aircraft': aero_data.get('aircraft', 'Unknown'),
                'status': aero_data.get('status', 'Unknown')
            }
            payload = _enrich_with_airport_scrapers(payload, dep_iata, arr_iata, flight_number, flight_date)
            return jsonify({'success': True, 'message': '从Aerodatabox获取到最新航班信息', 'data': payload})
        else:
            # Aerodatabox未找到数据，尝试从数据库获取历史数据作为备用
            flight = FlightSchedule.query.filter_by(flight_number=flight_number).first()
            
            if flight:
                return jsonify({
                    'success': True,
                    'message': 'Aerodatabox未找到，返回数据库中的历史信息',
                    'data': {
                        'flight_number': flight.flight_number,
                        'airline_code': flight.airline_code,
                        'airline_num': flight.airline_num,
                        'schedule_city': flight.schedule_city,
                        'schedule_timing': flight.schedule_timing,
                        'departure_terminal': getattr(flight, 'departure_terminal', 'Unknown'),
                        'departure_gate': getattr(flight, 'departure_gate', 'Unknown'),
                        'arrival_terminal': getattr(flight, 'arrival_terminal', 'Unknown'),
                        'arrival_gate': getattr(flight, 'arrival_gate', 'Unknown'),
                        'aircraft': getattr(flight, 'aircraft', 'Unknown'),
                        'status': getattr(flight, 'status', 'Unknown')
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Aerodatabox和数据库中均未找到航班信息，请检查航班号是否正确',
                    'data': None
                })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查询出错：{str(e)}',
            'data': None
        })

@flights_schedule.route('/api/flight_info/<flight_number>', methods=['GET'])
@login_required
@staff_only
def get_flight_info_api(flight_number):
    """获取航班信息API接口"""
    try:
        # 使用flightradar24模块获取航班信息
        from App_new.utils.flightradar24 import get_flight_info
        flight_info = get_flight_info(flight_number)

        if flight_info:
            return jsonify({
                'success': True,
                'flight_info': flight_info
            })
        else:
            return jsonify({
                'success': False,
                'message': f'未找到航班 {flight_number} 的信息'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查询航班信息时发生错误: {str(e)}'
        }), 500

@flights_schedule.route('/update_flight_timing', methods=['POST'])
@login_required
@staff_only
def update_flight_timing():
    """更新航班时刻表的时间信息和状态"""
    try:
        data = request.get_json()
        flight_id = data.get('flight_id')
        schedule_timing = data.get('schedule_timing')
        status = data.get('status', 'Unknown')
        
        if not flight_id:
            return jsonify({'success': False, 'error': '航班ID不能为空'})
        
        # 查找并更新记录
        flight = FlightSchedule.query.get(flight_id)
        if not flight:
            return jsonify({'success': False, 'error': '找不到指定的航班'})
        
        # 更新时间和状态
        if schedule_timing:
            flight.schedule_timing = schedule_timing
        if status:
            flight.status = status
            
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@flights_schedule.route('/search_flights', methods=['GET'])
@login_required
@staff_only
def search_flights():
    """
    搜索航班功能，通过航班号查询航班信息。
    """
    search_flight_number = request.args.get('search_flight_number', '').strip()

    # 如果没有输入搜索关键词，返回所有航班信息
    if not search_flight_number:
        flights = FlightSchedule.query.paginate(page=request.args.get('page', 1, type=int), per_page=10)
        return render_template('business/flight/flight_schedule_input.html', flights=flights)

    # 搜索数据库，匹配航班号（支持部分匹配）
    flights = FlightSchedule.query.filter(FlightSchedule.flight_number.like(f"%{search_flight_number}%")) \
        .paginate(page=request.args.get('page', 1, type=int), per_page=10)

    # 渲染模板，显示搜索结果
    return render_template('business/flight/flight_schedule_input.html', flights=flights)

@flights_schedule.route('/search_airports')
@login_required
@staff_only
def search_airports():
    """搜索机场信息"""
    try:
        iata = request.args.get('iata', '').strip().upper()
        city = request.args.get('city', '').strip()

        # 构建查询，只查询存在的列
        query = AirportData.query.with_entities(
            AirportData.id,
            AirportData.airport_IATA,
            AirportData.city_name,
            AirportData.airport_name_cn,
            AirportData.airport_name_en
        )

        # 添加搜索条件
        if iata:
            query = query.filter(AirportData.airport_IATA.like(f'%{iata}%'))
        if city:
            query = query.filter(AirportData.city_name.like(f'%{city}%'))

        # 执行查询
        airports = query.all()

        # 转换为JSON格式
        airports_data = []
        for airport in airports:
            airports_data.append({
                'id': airport.id,
                'iata': airport.airport_IATA,
                'city': airport.city_name,
                'airport_name_cn': airport.airport_name_cn,
                'airport_name_en': airport.airport_name_en
            })

        return jsonify({
            'status': 'success',
            'airports': airports_data
        })

    except Exception as e:
        print(f"Search error: {str(e)}")  # 添加错误日志
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@flights_schedule.route('/ocr_flight_info', methods=['POST'])
@login_required
@staff_only
def ocr_flight_info():
    """上传图片，OCR提取航班信息。"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '未找到文件字段 file'}), 400
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'success': False, 'message': '未选择文件'}), 400

        from App_new.utils.ocr_extract import extract_flight_info_from_image
        res = extract_flight_info_from_image(file)
        if not res.get('success'):
            return jsonify({'success': False, 'message': res.get('message', 'OCR失败')})

        data = res.get('data') or {}
        return jsonify({'success': True, 'message': 'OK', 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@flights_schedule.route('/update_airport', methods=['POST'])
@login_required
@staff_only
def update_airport():
    """更新机场信息"""
    try:
        data = request.get_json()

        if not data or not all(key in data for key in ['id', 'iata', 'city', 'airport_name_cn', 'airport_name_en']):
            return jsonify({
                'status': 'error',
                'message': '请提供所有必要的信息'
            }), 400

        # 验证ID格式
        try:
            airport_id = int(data['id'])
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'ID格式无效'
            }), 400

        # 验证IATA代码格式
        if not data['iata'] or len(data['iata']) != 3 or not data['iata'].isalpha() or not data['iata'].isupper():
            return jsonify({
                'status': 'error',
                'message': 'IATA代码必须是3位大写字母'
            }), 400

        # 查找机场信息 - 使用with_entities避免查询模型中不存在的列
        airport = AirportData.query.with_entities(
            AirportData.id,
            AirportData.airport_IATA,
            AirportData.city_name,
            AirportData.airport_name_cn,
            AirportData.airport_name_en
        ).filter_by(id=airport_id).first()

        if not airport:
            return jsonify({
                'status': 'error',
                'message': '未找到该机场信息'
            }), 404

        # 如果IATA代码已更改，检查新代码是否已存在
        if airport.airport_IATA != data['iata']:
            existing_airport = AirportData.query.with_entities(AirportData.id, AirportData.airport_IATA).filter_by(
                airport_IATA=data['iata']).first()
            if existing_airport and existing_airport.id != airport_id:
                return jsonify({
                    'status': 'error',
                    'message': f'IATA代码 "{data["iata"]}" 已被使用'
                }), 400

        # 直接使用原始SQL更新避免加载完整模型
        try:
            sql = text("UPDATE airport_data SET airport_IATA = :iata, city_name = :city, "
                       "airport_name_cn = :name_cn, airport_name_en = :name_en WHERE id = :id")

            db.session.execute(
                sql,
                {
                    "iata": data['iata'],
                    "city": data['city'],
                    "name_cn": data['airport_name_cn'],
                    "name_en": data['airport_name_en'],
                    "id": airport_id
                }
            )
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': '机场信息已成功更新'
            })
        except IntegrityError:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': '数据库错误，可能是IATA代码重复'
            }), 400

    except Exception as e:
        db.session.rollback()
        print(f"Update airport error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@flights_schedule.route('/input_airport_code_info', methods=['GET', 'POST'])
@login_required
@staff_only
def input_airport_code_info():
    # 处理URL中的CSRF token
    if request.method == 'GET' and request.args.get('csrf_token'):
        # 将URL中的CSRF token设置到session中
        session['csrf_token'] = request.args.get('csrf_token')
    
    if request.method == 'POST':
        try:
            iata_list = request.form.getlist('iata[]')
            city_list = request.form.getlist('city[]')
            airport_name_cn_list = request.form.getlist('airportNameCN[]')
            airport_name_en_list = request.form.getlist('airportNameEN[]')

            # 验证所有输入
            for iata, city, name_cn, name_en in zip(iata_list, city_list, airport_name_cn_list, airport_name_en_list):
                if not iata or not city or not name_cn or not name_en:
                    flash('所有字段都是必填项。', 'error')
                    return render_template('business/flight/flight_airport_code_input.html')

                if len(iata) != 3:
                    flash(f'IATA 代码 "{iata}" 必须是3个字符。', 'error')
                    return render_template('business/flight/flight_airport_code_input.html')

                if not iata.isalpha() or not iata.isupper():
                    flash(f'IATA 代码 "{iata}" 必须是3位大写字母。', 'error')
                    return render_template('business/flight/flight_airport_code_input.html')

                existing_airport = AirportData.query.filter_by(airport_IATA=iata.upper()).first()
                if existing_airport:
                    flash(f'IATA 代码 "{iata}" 已存在。', 'error')
                    return render_template('business/flight/flight_airport_code_input.html')

            # 批量创建机场数据
            airports_to_add = []
            for iata, city, name_cn, name_en in zip(iata_list, city_list, airport_name_cn_list, airport_name_en_list):
                airport = AirportData(
                    airport_IATA=iata.upper(),
                    city_name=city.strip(),
                    airport_name_cn=name_cn.strip(),
                    airport_name_en=name_en.strip()
                )
                airports_to_add.append(airport)

            # 批量添加到数据库
            db.session.add_all(airports_to_add)
            db.session.commit()

            flash(f'成功添加 {len(airports_to_add)} 个机场信息。', 'success')
            return redirect(url_for('flights_schedule.input_airport_code_info'))

        except Exception as e:
            db.session.rollback()
            flash(f'保存数据时出错：{str(e)}', 'error')
            return render_template('business/flight/flight_airport_code_input.html')

    # GET 请求时渲染页面
    return render_template('business/flight/flight_airport_code_input.html')

@flights_schedule.route('/delete_flight/<int:flight_id>', methods=['DELETE'])
@login_required
@staff_only
def delete_flight(flight_id):
    """删除航班信息"""
    try:
        flight = FlightSchedule.query.get_or_404(flight_id)
        db.session.delete(flight)
        db.session.commit()
        return jsonify({'success': True, 'message': '航班信息删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'})


@flights_schedule.route('/update_flight_info', methods=['POST'])
@login_required
@staff_only
def update_flight_info():
    """更新航班信息"""
    try:
        # 支持表单数据和JSON数据
        if request.is_json:
            data = request.get_json()
            flight_id = data.get('flight_id')
            airline_code = data.get('airline_code', '').strip()
            airline_num = data.get('airline_num', '').strip()
            schedule_city = data.get('schedule_city', '').strip()
            schedule_timing = data.get('schedule_timing', '').strip()
            departure_terminal = data.get('departure_terminal', '').strip()
            departure_gate = data.get('departure_gate', '').strip()
            arrival_terminal = data.get('arrival_terminal', '').strip()
            arrival_gate = data.get('arrival_gate', '').strip()
            aircraft = data.get('aircraft', '').strip()
        else:
            flight_id = request.form.get('flight_id')
            airline_code = request.form.get('airline_code', '').strip()
            airline_num = request.form.get('airline_num', '').strip()
            schedule_city = request.form.get('schedule_city', '').strip()
            schedule_timing = request.form.get('schedule_timing', '').strip()
            departure_terminal = request.form.get('departure_terminal', '').strip()
            departure_gate = request.form.get('departure_gate', '').strip()
            arrival_terminal = request.form.get('arrival_terminal', '').strip()
            arrival_gate = request.form.get('arrival_gate', '').strip()
            aircraft = request.form.get('aircraft', '').strip()
        
        if not flight_id:
            return jsonify({'success': False, 'message': '航班ID不能为空'}), 400
        
        # 获取航班记录
        flight = FlightSchedule.query.get_or_404(flight_id)
        
        # 更新字段
        flight.airline_code = airline_code
        flight.airline_num = airline_num
        flight.schedule_city = schedule_city
        flight.schedule_timing = schedule_timing
        flight.departure_terminal = departure_terminal
        flight.departure_gate = departure_gate
        flight.arrival_terminal = arrival_terminal
        flight.arrival_gate = arrival_gate
        flight.aircraft = aircraft
        
        # 保存到数据库
        db.session.commit()
        
        flash('航班信息更新成功！', 'success')
        return jsonify({'success': True, 'message': '航班信息更新成功'})
        
    except Exception as e:
        db.session.rollback()
        flash(f'更新失败：{str(e)}', 'error')
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


