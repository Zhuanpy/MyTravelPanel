from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from App.models.Flightmodels import FlightSchedule, AirportData
from ..utils.date_utils import get_date_by_day_delta
from App.code.utils.flightradar24 import search_flight
import datetime
from ..exts import db

flight_blue = Blueprint('flight_blue', __name__, url_prefix='/flights')

@flight_blue.route('/', methods=['GET'])
def flight_home():
    """机票模块首页"""
    return render_template('flights/机票首页.html')

@flight_blue.route('/athina', methods=['GET'])
def flight_to_athina_page():
    """ATHINA系统航班预定代码页面"""
    return render_template('flights/ATHINA系统航班预定代码.html')

@flight_blue.route('/athina_simple', methods=['GET'])
def athina_simple():
    """简化版ATHINA页面"""
    return render_template('flights/athina.html')

@flight_blue.route('/input_airport_code', methods=['GET'])
def input_airport_code():
    """机场代码输入页面"""
    # 获取机场数据列表（加入分页）
    page = request.args.get('page', 1, type=int)
    per_page = 10
    airports = AirportData.query.order_by(AirportData.airport_IATA).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('flights/录入机场代码.html', airports=airports)

@flight_blue.route('/input_airport_code_info', methods=['POST'])
def input_airport_code_info():
    """处理机场代码表单提交"""
    try:
        # 获取表单数据
        airport_iata = request.form.get('airport_iata', '').strip().upper()
        city_name = request.form.get('city_name', '').strip()
        airport_name_cn = request.form.get('airport_name_cn', '').strip()
        airport_name_en = request.form.get('airport_name_en', '').strip()
        
        # 验证数据
        if not airport_iata or not city_name or not airport_name_cn or not airport_name_en:
            flash('请填写所有必填字段', 'error')
            return redirect(url_for('flight_blue.input_airport_code'))
        
        # 验证IATA代码格式
        if not AirportData.validate_iata(airport_iata):
            flash('IATA代码必须是3个大写字母', 'error')
            return redirect(url_for('flight_blue.input_airport_code'))
        
        # 保存或更新机场信息
        AirportData.create_or_update(
            iata=airport_iata,
            city=city_name,
            name_cn=airport_name_cn,
            name_en=airport_name_en
        )
        
        # 提交数据库事务
        db.session.commit()
        
        flash(f'机场代码 {airport_iata} 保存成功', 'success')
        return redirect(url_for('flight_blue.input_airport_code'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'保存机场代码时出错: {str(e)}', 'error')
        return redirect(url_for('flight_blue.input_airport_code'))

@flight_blue.route('/itinerary_conversion', methods=['GET', 'POST'])
def itinerary_conversion():
    """行程转换功能"""
    if request.method == 'POST':
        # 这里处理行程转换的POST请求逻辑
        # 简单返回一个JSON响应作为示例
        return jsonify({'success': True, 'message': '行程转换处理成功'})
    
    # GET请求返回行程转换页面
    return render_template('flights/conversion.html')

@flight_blue.route('/confirmation_detail/<int:order_id>', methods=['GET'])
def confirmation_detail(order_id):
    """显示机票确认单详细信息"""
    # 在实际应用中，这里应该从数据库中获取确认单信息
    # 目前只是返回一个带有订单ID的模板
    return render_template('flights/确认单详细.html', order_id=order_id)

@flight_blue.route('/confirmation_detail', methods=['GET'])
def confirmation_detail_default():
    """显示默认的确认单页面（无订单ID）"""
    return render_template('flights/确认单详细.html')

@flight_blue.route('/simple_itinerary', methods=['GET'])
def simple_itinerary():
    """简化行程页面"""
    return render_template('flights/简化行程_日期-航班号.html')

@flight_blue.route('/simplify_itinerary', methods=['POST'])
def simplify_itinerary_by_flight_and_date():
    """处理简化行程表单提交"""
    try:
        # 获取表单数据
        itinerary_text = request.form.get('itinerary_text', '')
        
        if not itinerary_text:
            flash('请输入需要简化的行程信息', 'error')
            return redirect(url_for('flight_blue.simple_itinerary'))
        
        # 这里应该有处理行程简化的逻辑
        # 实际项目中这里可能有更复杂的处理逻辑
        simplified_text = process_itinerary(itinerary_text)
        
        # 返回结果到模板
        return render_template('flights/简化行程_日期-航班号.html', 
                               original_text=itinerary_text,
                               simplified_text=simplified_text)
        
    except Exception as e:
        flash(f'处理行程时出错: {str(e)}', 'error')
        return redirect(url_for('flight_blue.simple_itinerary'))
        
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

@flight_blue.route('/input_flight_schedule', methods=['GET'])
def input_flight_schedule():
    """航班时刻表输入页面"""
    search_flight_number = request.args.get('search_flight_number', '')
    # 获取航班列表（加入分页）
    page = request.args.get('page', 1, type=int)
    per_page = 10
    flights = FlightSchedule.query.order_by(FlightSchedule.create_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('flights/录入航班时刻表.html', 
                           search_flight_number=search_flight_number,
                           flights=flights)

@flight_blue.route('/input_flight_schedule_info', methods=['POST'])
def input_flight_schedule_info():
    """处理航班时刻表表单提交"""
    try:
        flight_numbers = request.form.getlist('flight_number[]')
        schedule_cities = request.form.getlist('schedule_city[]')
        schedule_timings = request.form.getlist('schedule_timing[]')
        
        # 验证数据
        if not flight_numbers or len(flight_numbers) != len(schedule_cities) or len(flight_numbers) != len(schedule_timings):
            flash('提交的数据不完整或格式错误', 'error')
            return redirect(url_for('flight_blue.input_flight_schedule'))
        
        # 保存到数据库
        success_count = 0
        for i in range(len(flight_numbers)):
            if flight_numbers[i] and schedule_cities[i] and schedule_timings[i]:
                # 检查是否已存在相同航班号的记录
                existing = FlightSchedule.query.filter_by(flight_number=flight_numbers[i]).first()
                if existing:
                    # 更新现有记录
                    existing.schedule_city = schedule_cities[i]
                    existing.schedule_timing = schedule_timings[i]
                    db.session.add(existing)
                else:
                    # 创建新记录
                    flight_schedule = FlightSchedule(
                        flight_number=flight_numbers[i],
                        schedule_city=schedule_cities[i],
                        schedule_timing=schedule_timings[i],
                        create_time=datetime.datetime.now()
                    )
                    db.session.add(flight_schedule)
                
                success_count += 1
        
        # 提交事务
        db.session.commit()
        
        if success_count > 0:
            flash(f'成功保存了 {success_count} 条航班信息', 'success')
        else:
            flash('没有有效的航班信息被保存', 'warning')
        
        return redirect(url_for('flight_blue.input_flight_schedule'))
        
    except Exception as e:
        # 回滚事务
        db.session.rollback()
        flash(f'保存航班信息时出错: {str(e)}', 'error')
        return redirect(url_for('flight_blue.input_flight_schedule'))

@flight_blue.route('/api/flight_info/<flight_number>', methods=['GET'])
def get_flight_info(flight_number):
    """获取航班信息API接口"""
    try:
        # 使用flightradar24模块获取航班信息
        flight_info = search_flight(flight_number)
        
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

@flight_blue.route('/update_flight_timing', methods=['POST'])
def update_flight_timing():
    """更新航班时刻表的时间信息"""
    try:
        data = request.get_json()
        flight_id = data.get('flight_id')
        schedule_timing = data.get('schedule_timing')
        
        if not flight_id or not schedule_timing:
            return jsonify({'success': False, 'error': '数据不完整'})
        
        # 查找并更新记录
        flight = FlightSchedule.query.get(flight_id)
        if not flight:
            return jsonify({'success': False, 'error': '找不到指定的航班'})
        
        flight.schedule_timing = schedule_timing
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}) 