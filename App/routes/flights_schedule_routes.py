from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from App.models.Flightmodels import FlightSchedule, AirportData
from sqlalchemy.exc import IntegrityError
from ..exts import db
from sqlalchemy import text
import re

flights_schedule = Blueprint('flights_schedule', __name__, url_prefix='/flights_schedule')

@flights_schedule.route('/input_airport_code', methods=['GET'])
def input_airport_code():
    """机场代码输入页面"""
    # 获取机场数据列表（加入分页）
    page = request.args.get('page', 1, type=int)
    per_page = 10
    airports = AirportData.query.order_by(AirportData.airport_IATA).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('flights/录入机场代码.html', airports=airports)

@flights_schedule.route('/itinerary_conversion', methods=['GET', 'POST'])
def itinerary_conversion():
    """行程转换功能"""
    if request.method == 'POST':
        # 这里处理行程转换的POST请求逻辑
        # 简单返回一个JSON响应作为示例
        return jsonify({'success': True, 'message': '行程转换处理成功'})
    
    # GET请求返回行程转换页面
    return render_template('flights/conversion.html')

@flights_schedule.route('/confirmation_detail/<int:order_id>', methods=['GET'])
def confirmation_detail(order_id):
    """显示机票确认单详细信息"""
    # 在实际应用中，这里应该从数据库中获取确认单信息
    # 目前只是返回一个带有订单ID的模板
    return render_template('flights/确认单详细.html', order_id=order_id)

@flights_schedule.route('/confirmation_detail', methods=['GET'])
def confirmation_detail_default():
    """显示默认的确认单页面（无订单ID）"""
    return render_template('flights/确认单详细.html')

@flights_schedule.route('/simple_itinerary', methods=['GET'])
def simple_itinerary():
    """简化行程页面"""
    return render_template('flights/简化行程_日期-航班号.html')

@flights_schedule.route('/simplify_itinerary', methods=['POST'])
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
        return render_template('flights/简化行程_日期-航班号.html', 
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

@flights_schedule.route('/input_flight_schedule', methods=['GET'])
def input_flight_schedule():
    """航班时刻表输入页面"""
    search_flight_number = request.args.get('search_flight_number', '')
    # 获取航班列表（加入分页）
    page = request.args.get('page', 1, type=int)
    per_page = 10
    flights = FlightSchedule.query.order_by(FlightSchedule.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('flights/录入航班时刻表.html', 
                           search_flight_number=search_flight_number,
                           flights=flights)

@flights_schedule.route('/input_flight_schedule_info', methods=['POST'])
def input_flight_schedule_info():
    """处理航班时刻表表单提交"""
    try:
        flight_numbers = request.form.getlist('flight_number[]')
        schedule_cities = request.form.getlist('schedule_city[]')
        schedule_timings = request.form.getlist('schedule_timing[]')
        
        # 验证数据
        if not flight_numbers or len(flight_numbers) != len(schedule_cities) or len(flight_numbers) != len(schedule_timings):
            flash('提交的数据不完整或格式错误', 'error')
            return redirect(url_for('flights_schedule.input_flight_schedule'))
        
        # 保存到数据库
        success_count = 0
        for i in range(len(flight_numbers)):
            if flight_numbers[i] and schedule_cities[i] and schedule_timings[i]:
                flight_number = flight_numbers[i].strip().upper()
                
                # 解析航班号为航司代码和航班编号
                airline_code = ""
                airline_num = ""
                match = re.match(r'^([A-Z]{2})(\d+)$', flight_number.replace(' ', ''))
                if match:
                    airline_code, airline_num = match.groups()
                
                # 检查是否已存在相同航班号的记录
                existing = FlightSchedule.query.filter_by(flight_number=flight_number).first()
                if existing:
                    # 更新现有记录
                    existing.schedule_city = schedule_cities[i]
                    existing.schedule_timing = schedule_timings[i]
                    if airline_code and airline_num:
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
        
        return redirect(url_for('flights_schedule.input_flight_schedule'))
        
    except Exception as e:
        # 回滚事务
        db.session.rollback()
        flash(f'保存航班信息时出错: {str(e)}', 'error')
        return redirect(url_for('flights_schedule.input_flight_schedule'))

@flights_schedule.route('/get-flight-info')
def get_flight_info_route():
    """获取航班信息的API端点"""
    flight_number = request.args.get('flight_number')
    if not flight_number:
        return jsonify({'error': '请提供航班号'}), 400
    
    from App.code.utils.flightradar24 import get_flight_info as get_flight_data
    flight_info = get_flight_data(flight_number)
    if flight_info:
        return jsonify({
            'schedule_city': flight_info['schedule_city'],
            'schedule_timing': flight_info['schedule_timing']
        })
    else:
        return jsonify({'error': '未找到航班信息'}), 404

@flights_schedule.route('/api/flight_info/<flight_number>', methods=['GET'])
def get_flight_info_api(flight_number):
    """获取航班信息API接口"""
    try:
        # 使用flightradar24模块获取航班信息
        from App.code.utils.flightradar24 import get_flight_info
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

@flights_schedule.route('/search_flights', methods=['GET'])
def search_flights():
    """
    搜索航班功能，通过航班号查询航班信息。
    """
    search_flight_number = request.args.get('search_flight_number', '').strip()

    # 如果没有输入搜索关键词，返回所有航班信息
    if not search_flight_number:
        flights = FlightSchedule.query.paginate(page=request.args.get('page', 1, type=int), per_page=10)
        return render_template('flights/录入航班时刻表.html', flights=flights)

    # 搜索数据库，匹配航班号（支持部分匹配）
    flights = FlightSchedule.query.filter(FlightSchedule.flight_number.like(f"%{search_flight_number}%")) \
        .paginate(page=request.args.get('page', 1, type=int), per_page=10)

    # 渲染模板，显示搜索结果
    return render_template('flights/录入航班时刻表.html', flights=flights)

@flights_schedule.route('/search_airports')
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


@flights_schedule.route('/update_airport', methods=['POST'])
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
def input_airport_code_info():
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
                    return render_template('flights/录入机场代码.html')

                if len(iata) != 3:
                    flash(f'IATA 代码 "{iata}" 必须是3个字符。', 'error')
                    return render_template('flights/录入机场代码.html')

                if not iata.isalpha() or not iata.isupper():
                    flash(f'IATA 代码 "{iata}" 必须是3位大写字母。', 'error')
                    return render_template('flights/录入机场代码.html')

                existing_airport = AirportData.query.filter_by(airport_IATA=iata.upper()).first()
                if existing_airport:
                    flash(f'IATA 代码 "{iata}" 已存在。', 'error')
                    return render_template('flights/录入机场代码.html')

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
            return render_template('flights/录入机场代码.html')

    # GET 请求时渲染页面
    return render_template('flights/录入机场代码.html')


