import re
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.models import FlightSchedule, AirportData
# 使用轻量 simple_cache 避免未初始化的 Cache.app 错误
from App_new.utils.cache import simple_cache
from App_new.utils.ConvertFlightItinerary import format_flight_info
from App_new.utils.utils import FlightData as flight
from App_new.exts import csrf, db
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

def request_schedule_data(flight_number):
    """获取航班时刻表数据"""
    try:
        # 标准化航班号
        flight_number = flight_number.replace(" ", "").upper()
        # 查询数据库
        # 简单缓存键 - 已禁用缓存以保证数据实时性
        # cache_key = f"schedule:{flight_number}"
        # cached = simple_cache.get(cache_key)
        # if cached is not None:
        #     return cached

        schedule = FlightSchedule.query.filter_by(flight_number=flight_number).first()
        
        if schedule:
            result = {
                'flight_number': schedule.flight_number,
                'airline_code': schedule.airline_code,
                'airline_num': schedule.airline_num,
                'schedule_city': schedule.schedule_city,
                'schedule_timing': schedule.schedule_timing
            }
            # simple_cache.set(cache_key, result, expire_minutes=5)
            return result
        return None
    except Exception as e:
        print(f"Error fetching schedule data for {flight_number}: {e}")
        return None

@flights_athina.route('/athina', methods=['GET'])
@login_required
@staff_only
def athina():
    """Athina页面"""
    return render_template('business/flight/flight_athina.html')

@flights_athina.route('/athina_simple', methods=['GET'])
@login_required
@staff_only
def athina_simple():
    """简化的Athina页面"""
    return render_template('business/flight/flight_athina.html')

# 页面内三个工具标签：parse=航班解析 / itinerary=机票行程转换 / athina=ATHINA代码生成
_CONVERSION_TABS = ('parse', 'itinerary', 'athina')


@flights_athina.route('/conversion', methods=['GET'])
@login_required
@staff_only
def athina_conversion():
    """Athina机票工具整合页面

    通过 ?tab= 参数区分当前激活的标签页，便于刷新/收藏/分享时保留标签状态。
    非法或缺省值一律回退到 parse。
    """
    tab = request.args.get('tab', 'parse')
    if tab not in _CONVERSION_TABS:
        tab = 'parse'
    return render_template('business/flight/flight_athina_conversion.html',
                           output_text="", active_tab=tab)

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
                    return render_template('business/flight/flight_conversion.html', output_text="")
            
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

@flights_athina.route('/api/convert_itinerary', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def api_convert_itinerary():
    """机票行程转换（干净 JSON 版，供 Hermes/脚本调用）

    与 /itinerary_conversion 同一套格式化逻辑，但只收 JSON、只回 JSON，
    无需伪造 X-Requested-With 头。

    请求体：
        {"text": "<行程文本>", "language": "chinese|english",
         "luggage": "<行李，可选>", "price": "<价格，可选>"}
    返回：
        {"success": true, "output_text": "...", "language": "..."}
        {"success": false, "error": "..."}
    """
    data = request.get_json(silent=True) or {}
    input_text = (data.get('text') or '').strip()
    language = (data.get('language') or 'chinese').strip().lower()
    luggage = data.get('luggage') or ''
    price = data.get('price') or ''

    if not input_text:
        return jsonify({'success': False, 'error': '请提供行程文本 text'}), 400

    try:
        if language == 'english':
            output_text = format_flight_info(city_language, texts=input_text,
                                              language='EN', luggage=luggage, price=price)
        else:
            output_text = format_flight_info(city_language, texts=input_text,
                                              luggage=luggage, price=price)
        return jsonify({
            'success': True,
            'output_text': output_text,
            'language': language,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'行程转换失败：{str(e)}'}), 500


@flights_athina.route('/generate_booking_code', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def generate_booking_code():
    """
    生成Athina预订代码API
    """
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


@flights_athina.route('/parse_flights', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def parse_flights_api():
    """解析航班信息API - 支持 Trip.com / Ctrip / Google Flights / Scoot / 手动输入格式"""
    try:
        from App_new.utils.parse_flights import parse_flights, resolve_airport_codes, format_segments
        from App_new.business.flight.models.models import AirportData

        data = request.get_json()
        if not data:
            return jsonify({'error': '未提供数据'}), 400

        input_text = data.get('text', '')
        if not input_text.strip():
            return jsonify({'error': '请输入航班信息'}), 400

        result = parse_flights(input_text)

        if not result['success']:
            return jsonify({
                'error': '未能识别航班信息格式。支持的格式：Trip.com、携程、Google Flights、酷航、航空公司官网（土耳其航空等）、手动输入'
            }), 400

        # 如果是手动输入格式，需要查找IATA代码
        if result['format_detected'] == '手动输入':
            def lookup_iata(name):
                """根据城市/机场名称查找IATA代码"""
                # 去掉括号内容，如 "新加坡（樟宜机场）" → "新加坡" 和 "樟宜机场"
                clean_name = re.sub(r'[（(][^）)]*[）)]', '', name).strip()
                paren_content = re.search(r'[（(]([^）)]*)[）)]', name)

                # 搜索列表：先原名，再去括号名，再括号内容
                search_names = [name.strip()]
                if clean_name != name.strip():
                    search_names.append(clean_name)
                if paren_content:
                    search_names.append(paren_content.group(1).strip())

                for search_name in search_names:
                    sn = search_name.upper()
                    # 精确匹配城市名或机场名
                    airport = AirportData.query.filter(
                        db.or_(
                            db.func.upper(AirportData.city_name) == sn,
                            db.func.upper(AirportData.city_name_en) == sn,
                            db.func.upper(AirportData.airport_name_cn) == sn,
                            db.func.upper(AirportData.airport_name_en) == sn,
                        )
                    ).first()
                    if airport:
                        return airport.airport_IATA

                    # 模糊匹配
                    airport = AirportData.query.filter(
                        db.or_(
                            AirportData.city_name.ilike(f'%{search_name}%'),
                            AirportData.city_name_en.ilike(f'%{search_name}%'),
                            AirportData.airport_name_cn.ilike(f'%{search_name}%'),
                            AirportData.airport_name_en.ilike(f'%{search_name}%'),
                        )
                    ).first()
                    if airport:
                        return airport.airport_IATA

                return None

            resolve_airport_codes(result['flights'], lookup_iata)
            # 重新格式化segments
            result['segments'] = format_segments(result['flights'])

            # 检查是否有未识别的机场
            unknown = []
            for f in result['flights']:
                if f['dep_code'] == '???':
                    unknown.append(f.get('_original_dep', f['dep_code']))
                if f['arr_code'] == '???':
                    unknown.append(f.get('_original_arr', f['arr_code']))

            if unknown:
                result['warning'] = f'以下城市/机场未找到IATA代码: {", ".join(set(unknown))}，显示为???'

        return jsonify({
            'success': True,
            'segments': result['segments'],
            'format_detected': result['format_detected'],
            'flight_count': len(result['flights']),
            'warning': result.get('warning')
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'解析失败：{str(e)}'}), 500

