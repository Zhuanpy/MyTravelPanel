from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from App.models.Flightmodels import FlightSchedule, AirportData
from App.utils.cache import cache
from App.code.FlightTicket.ConvertFlight.ConvertFlightItinerary import format_flight_info
from App.code.utils.utils import FlightData as flight
from App.exts import csrf

flights_athina = Blueprint('flights_athina', __name__, url_prefix='/flights_athina')

def init_cache(app):
    """初始化缓存"""
    cache.init_app(app, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': 'redis://localhost:6379/0',
        'CACHE_DEFAULT_TIMEOUT': 300
    })

def city_language(city_name: str):
    if not city_name:  # 检查输入是否为空
        return "未知机场", "Unknown Airport"

    try:
        # 只查询需要的列，减少查询开销
        airport = AirportData.query.with_entities(
            AirportData.airport_name_cn, AirportData.airport_name_en
        ).filter_by(airport_IATA=city_name).first()

        if not airport:  # 检查查询结果是否为空
            return "未知机场", "Unknown Airport"

        name_cn, name_en = airport  # 解包查询结果
        return name_cn, name_en
    except Exception as e:
        # 打印错误日志（可选）
        print(f"Error fetching airport data: {e}")
        return "未知机场", "Unknown Airport"

@cache.memoize(timeout=300)
def request_schedule_data(flight_number):
    """获取航班时刻表数据"""
    try:
        # 标准化航班号
        flight_number = flight_number.replace(" ", "").upper()
        # 查询数据库
        schedule = FlightSchedule.query.filter_by(flight_number=flight_number).first()

        if not schedule:
            return None

        # 转换为字典
        schedule_dict = schedule.to_dict()
        print(f"Schedule data: {schedule_dict}")  # 调试信息
        return schedule_dict

    except Exception as e:
        print(f"Error in request_schedule_data: {str(e)}")  # 调试信息
        return None


@flights_athina.route('/athina', methods=['GET'])
def flight_to_athina_page():
    """ATHINA系统航班预定代码页面"""
    return render_template('flights/flight_athina_booking_code.html')

@flights_athina.route('/athina_simple', methods=['GET'])
def athina_simple():
    """简化版ATHINA页面"""
    return render_template('flights/flight_athina.html')


@flights_athina.route('/itinerary_conversion', methods=['GET', 'POST'])
@csrf.exempt
def itinerary_conversion():
    if request.method == 'GET':
        return render_template('flights/flight_conversion.html', output_text="")

    elif request.method == 'POST':
        try:
            print(f"Received form data: {dict(request.form)}")  # 调试信息
            
            input_text = request.form.get('input_text', '')
            language = request.form.get('language', 'chinese')
            luggage = request.form.get('luggage', '')
            price = request.form.get('price', '')
            
            print(f"Parsed data - input_text: '{input_text}', language: '{language}', luggage: '{luggage}', price: '{price}'")  # 调试信息

            # 根据选择的语言进行文字转换
            output_text = ""

            if language == "chinese":
                # 中文行程转换逻辑
                output_text = format_flight_info(city_language, texts=input_text, luggage=luggage,
                                               price=price)

            elif language == "english":
                # 英文行程转换逻辑
                output_text = format_flight_info(city_language, texts=input_text, language='EN',
                                               luggage=luggage, price=price)

            print(f"Generated output_text: '{output_text}'")  # 调试信息
            return jsonify({'output_text': output_text})
            
        except Exception as e:
            print(f"Error in itinerary_conversion: {str(e)}")
            return jsonify({'error': str(e)}), 500


# 机票 行程转换
@flights_athina.route('/simplify_itinerary_by_flight_and_date', methods=['GET', 'POST'])
@csrf.exempt
def simplify_itinerary_by_flight_and_date():
    if request.method == 'GET':  # 加载页面

        return render_template('flights/flight_itinerary_simple.html', output_text="")

    if request.method == 'POST':

        try:
            data = request.get_json()
            # print(data)
            # 获取语言、行李、价格和航班信息
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

            # 生成行程信息（此处为示例，您可以根据实际需求进行生成）
            input_text = f""
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
            # print(itinerary)
            return jsonify({'itinerary': itinerary})

        except Exception as e:
            return jsonify({'error': str(e)}), 500


@flights_athina.route('/athinaPage', methods=['GET', 'POST'])
@csrf.exempt
def athina_page_handler():
    if request.method == 'GET':
        return render_template('flights/ATHINA系统航班预定代码.html')

    if request.method == 'POST':
        try:
            # 获取并验证请求数据
            data = request.get_json()
            print(f"Received data: {data}")  # 调试日志

            if not data:
                return jsonify({'error': '未提供任何订单数据'}), 400

            itinerary = ""
            num = 1

            for entry in data:
                try:
                    # 获取并验证航班信息
                    flight_number = entry.get('flightNumber', '').strip().replace(" ", "").upper()
                    flight_date = entry.get('flightDate', '').strip().replace(" ", "").upper()

                    print(f"Processing flight {num}: {flight_number} on {flight_date}")  # 调试日志

                    if not flight_number or not flight_date:
                        return jsonify({'error': f'订单条目 {num} 缺少航班号或日期'}), 400

                    # 获取航班时刻表数据
                    schedule_dic = request_schedule_data(flight_number)
                    print(f"Schedule data for {flight_number}: {schedule_dic}")  # 调试日志

                    if not schedule_dic:
                        return jsonify({
                            'error': f'未找到航班号 {flight_number} 的时刻表数据。请先在航班时刻表中添加该航班信息。'
                        }), 404

                    try:
                        # 生成预订代码
                        r = flight.athina_booking_code(num, schedule_dic, flight_date)
                        print(f"Generated booking code: {r}")  # 调试日志

                        if r.startswith("An error occurred") or r.startswith("Database error"):
                            return jsonify({'error': r}), 500
                        itinerary += f"{r}\n"
                        num += 1
                    except Exception as e:
                        print(f"Error generating booking code: {str(e)}")  # 调试日志
                        import traceback
                        print(f"Traceback for booking code generation: {traceback.format_exc()}")  # 打印完整的错误堆栈
                        return jsonify({
                            'error': f'生成航班 {flight_number} 的预订代码时出错：{str(e)}'
                        }), 500

                except Exception as e:
                    print(f"Error processing entry {num}: {str(e)}")  # 调试日志
                    import traceback
                    print(f"Traceback for entry processing: {traceback.format_exc()}")  # 打印完整的错误堆栈
                    return jsonify({
                        'error': f'处理航班信息时出错：{str(e)}'
                    }), 500

            return jsonify({'itinerary': itinerary})

        except Exception as e:
            print(f"Error in flight_to_athina_page: {str(e)}")  # 调试日志
            import traceback
            print(f"Traceback: {traceback.format_exc()}")  # 打印完整的错误堆栈
            return jsonify({'error': str(e)}), 500

