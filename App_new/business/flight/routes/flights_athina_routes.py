from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.models import FlightSchedule, AirportData
from App_new.utils.cache import cache
from App_new.utils.ConvertFlightItinerary import format_flight_info
from App_new.utils.utils import FlightData as flight
from App_new.exts import csrf
from App_new.utils.decorators import staff_only

flights_athina = Blueprint('flights_athina', __name__, url_prefix='/flights_athina')

def init_cache(app):
    """初始化缓存"""
    # 暂时使用简单缓存，避免Redis连接问题
    cache.init_app(app, config={
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300
    })

def city_language(city_name: str):
    if not city_name:  # 检查输入是否为空
        print(f"city_language called with empty city_name")
        return "未知机场", "Unknown Airport"

    try:
        print(f"city_language called with city_name: {city_name}")
        # 只查询需要的列，减少查询开销
        airport = AirportData.query.with_entities(
            AirportData.airport_name_cn, AirportData.airport_name_en
        ).filter_by(airport_IATA=city_name).first()

        if not airport:  # 检查查询结果是否为空
            print(f"No airport data found for IATA code: {city_name}")
            return "未知机场", "Unknown Airport"

        name_cn, name_en = airport  # 解包查询结果
        print(f"Found airport data: {name_cn}, {name_en}")
        return name_cn, name_en
    except Exception as e:
        # 打印错误日志（可选）
        print(f"Error fetching airport data for {city_name}: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return "未知机场", "Unknown Airport"

@cache.memoize(timeout=300)
def request_schedule_data(flight_number):
    """获取航班时刻表数据"""
    try:
        # 标准化航班号
        flight_number = flight_number.replace(" ", "").upper()
        # 查询数据库
        schedule = FlightSchedule.query.filter_by(flight_number=flight_number).first()
        
        if schedule:
            return {
                'flight_number': schedule.flight_number,
                'airline_code': schedule.airline_code,
                'airline_num': schedule.airline_num,
                'schedule_city': schedule.schedule_city,
                'schedule_timing': schedule.schedule_timing
            }
        return None
    except Exception as e:
        print(f"Error fetching schedule data for {flight_number}: {e}")
        return None

@flights_athina.route('/athina', methods=['GET'])
@login_required
@staff_only
def athina():
    """Athina页面"""
    return render_template('flights/flight_athina.html')

@flights_athina.route('/athina_simple', methods=['GET'])
@login_required
@staff_only
def athina_simple():
    """简化的Athina页面"""
    return render_template('flights/flight_athina.html')

@flights_athina.route('/conversion', methods=['GET'])
@login_required
@staff_only
def athina_conversion():
    """Athina机票工具整合页面"""
    return render_template('flights/flight_athina_conversion.html', output_text="")

@flights_athina.route('/itinerary_conversion', methods=['GET', 'POST'])
@login_required
@staff_only
def itinerary_conversion():
    """行程转换功能"""
    if request.method == 'POST':
        try:
            # 获取提交的行程数据
            input_text = request.form.get('input_text', '')
            language = request.form.get('language', 'chinese')
            luggage = request.form.get('luggage', '')
            price = request.form.get('price', '')
            
            if not input_text.strip():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': '请输入行程数据'}), 400
                else:
                    flash('请输入行程数据', 'error')
                    return render_template('flights/flight_conversion.html', output_text="")
            
            # 处理行程数据
            try:
                # 使用ConvertFlightItinerary模块处理数据
                if language == "chinese":
                    output_text = format_flight_info(city_language, texts=input_text, luggage=luggage, price=price)
                elif language == "english":
                    output_text = format_flight_info(city_language, texts=input_text, language='EN', luggage=luggage, price=price)
                else:
                    output_text = format_flight_info(city_language, texts=input_text, luggage=luggage, price=price)
                
                # 检查是否是AJAX请求
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True,
                        'output_text': output_text,
                        'input_text': input_text,
                        'language': language,
                        'luggage': luggage,
                        'price': price
                    })
                else:
                    return render_template('flights/flight_conversion.html', 
                                         input_text=input_text,
                                         output_text=output_text,
                                         language=language,
                                         luggage=luggage,
                                         price=price)
                                     
            except Exception as format_error:
                error_msg = f'行程数据格式错误：{str(format_error)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': error_msg}), 400
                else:
                    flash(error_msg, 'error')
                    return render_template('flights/flight_conversion.html',
                                         input_text=input_text,
                                         output_text="")
                
        except Exception as e:
            error_msg = f'处理失败：{str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 500
            else:
                flash(error_msg, 'error')
                return render_template('flights/flight_conversion.html', output_text="")
    
    # GET请求返回行程转换页面
    return render_template('flights/flight_conversion.html', output_text="")

@flights_athina.route('/simplify_itinerary_by_flight_and_date', methods=['GET', 'POST'])
@login_required
@staff_only
def simplify_itinerary_by_flight_and_date():
    """
    通过航班号和日期简化行程
    """
    if request.method == 'POST':
        try:
            # 获取提交的数据
            data = request.get_json()
            language = data.get('language', '中文')
            baggage = data.get('baggage', '')
            price = data.get('price', 0)
            flights = data.get('flights', [])
            
            # 简单验证
            if not flights:
                return jsonify({'error': '没有提供航班信息。'}), 400

            if not baggage:
                return jsonify({'error': '没有提供行李信息。'}), 400

            if not price:
                return jsonify({'error': '没有提供价格信息。'}), 400

            # 生成行程信息
            input_text = ""
            start_num = 1

            for idx, f in enumerate(flights, start=1):
                flight_number = f.get('flightNumber').upper().replace(' ', '')
                flight_date = f.get('flightDate').upper().replace(' ', '')
                schedule_dic = request_schedule_data(flight_number)
                r = flight.athina_booking_code(start_num, schedule_dic, flight_date)
                input_text += f'{r}\n\n'
                start_num += 1

            if language == "中文":
                # 中文行程转换逻辑
                itinerary = format_flight_info(city_language,
                                               texts=input_text,
                                               luggage=baggage,
                                               price=price)

            elif language == "英文":
                # 英文行程转换逻辑
                itinerary = format_flight_info(city_language,
                                               texts=input_text,
                                               language='EN',
                                               luggage=baggage,
                                               price=price)
            
            return jsonify({'itinerary': itinerary})
                                 
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET请求返回页面
    return render_template('flights/flight_itinerary_simple.html', output_text="")

@flights_athina.route('/athinaPage', methods=['GET', 'POST'])
@login_required
@staff_only
def athina_page():
    """
    Athina主页面处理
    """
    if request.method == 'POST':
        try:
            # 获取并验证请求数据
            data = request.get_json()
            
            if not data:
                return jsonify({'error': '未提供任何订单数据'}), 400

            itinerary = ""
            num = 1

            for entry in data:
                try:
                    # 获取并验证航班信息
                    flight_number = entry.get('flightNumber', '').strip().replace(" ", "").upper()
                    flight_date = entry.get('flightDate', '').strip().replace(" ", "").upper()

                    if not flight_number or not flight_date:
                        return jsonify({'error': f'订单条目 {num} 缺少航班号或日期'}), 400

                    # 获取航班时刻表数据
                    schedule_dic = request_schedule_data(flight_number)

                    if not schedule_dic:
                        return jsonify({
                            'error': f'未找到航班号 {flight_number} 的时刻表数据。请先在航班时刻表中添加该航班信息。'
                        }), 404

                    try:
                        # 生成预订代码
                        r = flight.athina_booking_code(num, schedule_dic, flight_date)

                        if r.startswith("An error occurred") or r.startswith("Database error"):
                            return jsonify({'error': r}), 500
                        itinerary += f"{r}\n"
                        num += 1
                    except Exception as e:
                        return jsonify({
                            'error': f'生成航班 {flight_number} 的预订代码时出错：{str(e)}'
                        }), 500

                except Exception as e:
                    return jsonify({
                        'error': f'处理航班信息时出错：{str(e)}'
                    }), 500

            return jsonify({'itinerary': itinerary})
                                 
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET请求返回页面
    return render_template('flights/flight_athina_booking_code.html')

