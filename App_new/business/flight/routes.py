import os
import subprocess
import re
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask import current_app as app
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import NoResultFound
from flask_caching import Cache
from sqlalchemy import text

from ..code.FlightTicket.ConvertFlight.ConvertFlightItinerary import format_flight_info
from ..code.FlightTicket.ConvertFlight.read_sql_data import original_airport_code_data, original_flight_timing_data
from ..code.utils.utils import FlightData as flight
from ..models.Flightmodels import *
from ..models.Visamodels import *
from ..services.flight_service import FlightService
from ..forms.flight_forms import FlightScheduleForm
from ..utils.decorators import login_required, admin_required
from ..utils.cache import cache

# 创建蓝图
flight_blue = Blueprint('flight_blue', __name__)

def init_cache(app):
    """初始化缓存"""
    cache.init_app(app, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': 'redis://localhost:6379/0',
        'CACHE_DEFAULT_TIMEOUT': 300
    })

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

@flight_blue.route('/conversion', methods=['GET', 'POST'])
def itinerary_conversion():
    if request.method == 'GET':
        return render_template('flights/conversion.html', output_text="")

    elif request.method == 'POST':
        input_text = request.form['input_text']
        language = request.form['language']
        luggage = request.form['luggage']
        price = request.form['price']

        # 根据选择的语言进行文字转换
        output_text = ""

        if language == "chinese":
            # 中文行程转换逻辑
            output_text = format_flight_info(city_language=city_language, texts=input_text, luggage=luggage, price=price)

        elif language == "english":
            # 英文行程转换逻辑
            output_text = format_flight_info(city_language=city_language, texts=input_text, language='EN', luggage=luggage, price=price)

        return render_template('flights/conversion.html', output_text=output_text)


# 机票 行程转换
@flight_blue.route('/simplify_itinerary_by_flight_and_date', methods=['GET', 'POST'])
def simplify_itinerary_by_flight_and_date():

    if request.method == 'GET':  # 加载页面

        return render_template('flights/简化行程_日期-航班号.html', output_text="")

    if request.method == 'POST':

        try:
            data = request.get_json()
            print(data)
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

            if not price :
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
                itinerary = format_flight_info(city_language=city_language,
                                               texts=input_text,
                                               luggage=baggage,
                                               price=price)

            elif language == "英文":
                # 英文行程转换逻辑
                itinerary = format_flight_info(city_language=city_language,
                                               texts=input_text,
                                               language='EN',
                                               luggage=baggage,
                                               price=price)
            print(itinerary)
            return jsonify({'itinerary': itinerary})

        except Exception as e:
            return jsonify({'error': str(e)}), 500


@flight_blue.route('/athinaPage', methods=['GET', 'POST'])
def flight_to_athina_page():
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
                    flight_date = entry.get('flightDate', '').strip()
                    
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


""" 航班信息录入"""


@login_required
@admin_required
@flight_blue.route('/flight_schedule', methods=['GET', 'POST'])
def input_flight_schedule_info():
    form = FlightScheduleForm()
    
    # 获取分页数据
    page = request.args.get('page', 1, type=int)
    flights = FlightSchedule.query.paginate(page=page, per_page=10)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            flight_numbers = request.form.getlist('flight_number[]')
            schedule_cities = request.form.getlist('schedule_city[]')
            schedule_timings = request.form.getlist('schedule_timing[]')
            
            # 验证数据
            if not all([flight_numbers, schedule_cities, schedule_timings]):
                flash('请填写所有必要的字段', 'error')
                return render_template('flights/录入航班时刻表.html', form=form, flights=flights)
            
            if len(flight_numbers) != len(schedule_cities) or len(flight_numbers) != len(schedule_timings):
                flash('数据格式错误', 'error')
                return render_template('flights/录入航班时刻表.html', form=form, flights=flights)
            
            # 处理每个航班信息
            for flight_number, schedule_city, schedule_timing in zip(flight_numbers, schedule_cities, schedule_timings):
                if not all([flight_number.strip(), schedule_city.strip(), schedule_timing.strip()]):
                    continue
                    
                # 检查是否已存在相同航班号
                existing_flight = FlightSchedule.query.filter_by(flight_number=flight_number.strip()).first()
                
                if existing_flight:
                    # 更新现有记录
                    existing_flight.schedule_city = schedule_city.strip()
                    existing_flight.schedule_timing = schedule_timing.strip()
                
                else:
                    # 创建新记录
                    new_flight = FlightSchedule(
                        flight_number=flight_number.strip(),
                        schedule_city=schedule_city.strip(),
                        airline_code=flight_number.strip()[:2],
                        airline_num = flight_number.strip()[2:],
                        schedule_timing=schedule_timing.strip()
                    )
                    db.session.add(new_flight)
            
            db.session.commit()
            flash('航班信息保存成功！', 'success')
            return redirect(url_for('flight_blue.input_flight_schedule_info'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'保存失败：{str(e)}', 'error')
            return render_template('flights/录入航班时刻表.html', form=form, flights=flights)
    
    return render_template('flights/录入航班时刻表.html', form=form, flights=flights)


@flight_blue.route('/search_flights', methods=['GET'])
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


@flight_blue.route('/update_flight_timing', methods=['POST'])
def update_flight_timing():
    try:
        data = request.get_json()
        flight_id = data.get("flight_id")
        new_timing = data.get("schedule_timing")

        # 查询数据库中对应的航班记录
        flight = FlightSchedule.query.get(flight_id)

        if not flight:
            return jsonify({"success": False, "error": "航班未找到"}), 404

        # 更新航班时间
        flight.schedule_timing = new_timing
        db.session.commit()

        return jsonify({"success": True, "message": "航班时间更新成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500



@flight_blue.route('/flight_airport_data')
def flight_airport_data():
    original_data = original_airport_code_data()
    airport_list = []

    for index, row in original_data.iterrows():
        airport = AirportData()
        # 检查数据库中是否已有此记录
        try:
            airport.query.filter_by(airport_IATA=row["机场三字码"]).one()
            # 如果找到，则更新字段

        except NoResultFound:
            airport.airport_IATA = row["机场三字码"]
            airport.city_name = row["城市名"]
            airport.airport_name_cn = row["机场名称"]
            airport.airport_name_en = row["英文名称"]

            airport = AirportData(airport_IATA=row["机场三字码"],
                                  city_name=row["城市名"],
                                  airport_name_cn=row["机场名称"],
                                  airport_name_en=row["英文名称"]
                                  )

            # 保存到列表（或者直接提交数据库）
            airport_list.append(airport)

    db.session.add_all(airport_list)

    db.session.commit()

    return 'Success add airport data ！'


@flight_blue.route('/flight_schedule_data')
def flight_schedule_data():
    schedule_list = []

    original = original_flight_timing_data()

    for index, row in original.iterrows():

        try:
            # 检查数据库中是否已有此记录
            schedule = FlightSchedule()
            schedule.query.filter_by(flight_number=row["flight_number"]).one()
            # 如果找到，则不更新

        except NoResultFound:
            # 如果没找到，则更新
            schedule = FlightSchedule(flight_number=row["航班ID"],
                                      airline_code=row["航司"],
                                      airline_num=row["航班号"],
                                      schedule_city=row["起始城市"],
                                      schedule_timing=row["起始时间"]
                                      )

            # 保存到列表（或者直接提交数据库）
            schedule_list.append(schedule)

    db.session.add_all(schedule_list)
    db.session.commit()

    return 'Success add flight schedule data ！'


@flight_blue.route('/input_airport_code_info', methods=['GET', 'POST'])
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
            return redirect(url_for('flight_blue.input_airport_code_info'))

        except Exception as e:
            db.session.rollback()
            flash(f'保存数据时出错：{str(e)}', 'error')
            return render_template('flights/录入机场代码.html')

    # GET 请求时渲染页面
    return render_template('flights/录入机场代码.html')


@flight_blue.route('/open_project_folder', methods=['GET', 'POST'])
def open_project_folder():
    # 获取目标文件夹路径
    path_ = os.path.join(app.root_path, app.static_folder, "资源", "机票产品")

    # 检查路径是否有效
    if not os.path.exists(path_):
        flash("目标路径不存在：无法打开文件夹。", category="error")
        return redirect(url_for('index.index'))

    # 尝试打开文件夹
    try:
        subprocess.Popen(f'explorer "{path_}"')
        flash("文件夹已成功打开。", category="success")

    except Exception as e:
        flash(f"无法打开文件夹，错误信息: {str(e)}", category="error")

    return redirect(url_for('index.index'))

@flight_blue.route('/open_refund_folder', methods=['GET', 'POST'])
def open_refund_folder():
    # 拼接目标文件夹路径  Project\机票\退票
    folder_path = os.path.join(app.root_path, app.static_folder, "资源", "Project","机票","退票")

    # 检查路径是否存在
    if not os.path.exists(folder_path):
        flash("退票文件夹路径不存在：无法打开文件夹。", category="error")
        return redirect(url_for('index.index'))

    # 尝试打开文件夹
    try:
        subprocess.Popen(f'explorer "{folder_path}"')  # 使用 Windows 的文件资源管理器打开文件夹
        flash("退票文件夹已成功打开。", category="success")

    except Exception as e:
        flash(f"无法打开退款政策文件夹，错误信息: {str(e)}", category="error")

    return redirect(url_for('index.index'))

def convert_date_format(date_str):
    if not date_str:
        return ''
    try:
        day, month, year = date_str.split('/')
        months = {
            '01': 'JAN', '02': 'FEB', '03': 'MAR', '04': 'APR',
            '05': 'MAY', '06': 'JUN', '07': 'JUL', '08': 'AUG',
            '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC'
        }
        return f"{day}{months[month]}{year}"
    except:
        return ''


@flight_blue.route('/search_airports')
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

@flight_blue.route('/update_airport', methods=['POST'])
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
            existing_airport = AirportData.query.with_entities(AirportData.id, AirportData.airport_IATA).filter_by(airport_IATA=data['iata']).first()
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

@flight_blue.route('/flight_home')
def flight_home():
    """机票首页路由"""
    return render_template('business/flight/flight_home.html')

@flight_blue.route('/flight_orders')
def flight_orders():
    """机票订单管理页面"""
    # 获取排序和筛选参数
    sort_by = request.args.get('sort_by', 'created_date')
    order_by = request.args.get('order_by', 'desc')
    status_filter = request.args.get('status', 'all')
    
    # 基础查询
    query = FlightOrder.query
    
    # 根据员工等级过滤订单
    if current_user.is_authenticated and current_user.role and current_user.role.name == 'staff':
        # 检查用户资料中的员工等级
        staff_level = 1  # 默认等级
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1
        
        if staff_level == 1:
            # 1级员工只能看到自己创建的订单
            # 通过关联的ProjectHeader表进行过滤
            from App_new.business.projects.models.project import ProjectHeader
            query = query.join(ProjectHeader, FlightOrder.project_header_id == ProjectHeader.id)\
                         .filter(ProjectHeader.staff_name == current_user.username)
        # 2级员工可以看到所有订单，不需要额外过滤
    
    # 应用筛选条件
    if status_filter and status_filter != 'all':
        query = query.filter_by(order_status=status_filter)
    
    # 应用排序
    if sort_by == 'created_date':
        if order_by == 'desc':
            query = query.order_by(FlightOrder.created_date.desc())
        else:
            query = query.order_by(FlightOrder.created_date)
    elif sort_by == 'departure_date':
        if order_by == 'desc':
            query = query.order_by(FlightOrder.departure_date.desc())
        else:
            query = query.order_by(FlightOrder.departure_date)
    
    # 执行查询
    orders = query.all()
    
    return render_template('flights/机票订单管理.html', 
                          orders=orders, 
                          sort_by=sort_by, 
                          order_by=order_by,
                          status_filter=status_filter)


@flight_blue.route('/add_flight_order', methods=['GET', 'POST'])
def add_flight_order():
    """添加机票订单"""
    if request.method == 'GET':
        return render_template('flights/添加机票订单.html')
    
    elif request.method == 'POST':
        try:
            # 从表单获取数据
            data = request.form
            
            # 生成订单号 (可自定义生成规则)
            current_date = datetime.now().strftime('%Y%m%d')
            order_count = FlightOrder.query.filter(
                FlightOrder.order_number.like(f"F{current_date}%")
            ).count()
            
            order_number = f"F{current_date}{str(order_count + 1).zfill(3)}"
            
            # 创建新订单
            new_order = FlightOrder(
                order_number=order_number,
                hid_number=data.get('hid_number'),
                passenger_name=data.get('passenger_name'),
                contact_person=data.get('contact_person'),
                contact_phone=data.get('contact_phone'),
                departure_date=datetime.strptime(data.get('departure_date'), '%Y-%m-%d').date() if data.get('departure_date') else None,
                itinerary=data.get('itinerary'),
                departure_city=data.get('departure_city'),
                arrival_city=data.get('arrival_city'),
                airline=data.get('airline'),
                flight_number=data.get('flight_number'),
                departure_time=datetime.strptime(f"{data.get('departure_date')} {data.get('departure_time')}", '%Y-%m-%d %H:%M') if data.get('departure_date') and data.get('departure_time') else None,
                arrival_time=datetime.strptime(f"{data.get('arrival_date')} {data.get('arrival_time')}", '%Y-%m-%d %H:%M') if data.get('arrival_date') and data.get('arrival_time') else None,
                cabin_class=data.get('cabin_class'),
                is_transit=True if data.get('is_transit') == 'on' else False,
                transit_info=data.get('transit_info'),
                order_status=data.get('order_status', '待出票'),
                payment_status=data.get('payment_status', '待支付'),
                payment_method=data.get('payment_method'),
                total_price=float(data.get('total_price')) if data.get('total_price') else None,
                tax_fee=float(data.get('tax_fee')) if data.get('tax_fee') else None,
                actual_payment=float(data.get('actual_payment')) if data.get('actual_payment') else None,
                operator=data.get('operator'),
                refund_change_policy=data.get('refund_change_policy'),
                baggage_allowance=data.get('baggage_allowance'),
                pnr_code=data.get('pnr_code'),
                e_ticket_number=data.get('e_ticket_number'),
                client_type=data.get('client_type', '个人'),
                remarks=data.get('remarks')
            )
            
            db.session.add(new_order)
            db.session.commit()
            
            flash('机票订单添加成功！', 'success')
            return redirect(url_for('flight_blue.flight_orders'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'添加订单失败: {str(e)}', 'error')
            return redirect(url_for('flight_blue.add_flight_order'))


@flight_blue.route('/flight_order/<int:order_id>')
def view_flight_order(order_id):
    """查看机票订单详情"""
    order = FlightOrder.query.get_or_404(order_id)
    return render_template('flights/机票订单详情.html', order=order)


@flight_blue.route('/flight_order/<int:order_id>/edit', methods=['GET', 'POST'])
def edit_flight_order(order_id):
    """编辑机票订单"""
    order = FlightOrder.query.get_or_404(order_id)
    
    if request.method == 'GET':
        return render_template('flights/编辑机票订单.html', order=order)
    
    elif request.method == 'POST':
        try:
            # 从表单获取数据
            data = request.form
            
            # 更新订单信息
            order.hid_number = data.get('hid_number')
            order.passenger_name = data.get('passenger_name')
            order.contact_person = data.get('contact_person')
            order.contact_phone = data.get('contact_phone')
            order.departure_date = datetime.strptime(data.get('departure_date'), '%Y-%m-%d').date() if data.get('departure_date') else None
            order.itinerary = data.get('itinerary')
            order.departure_city = data.get('departure_city')
            order.arrival_city = data.get('arrival_city')
            order.airline = data.get('airline')
            order.flight_number = data.get('flight_number')
            order.departure_time = datetime.strptime(f"{data.get('departure_date')} {data.get('departure_time')}", '%Y-%m-%d %H:%M') if data.get('departure_date') and data.get('departure_time') else None
            order.arrival_time = datetime.strptime(f"{data.get('arrival_date')} {data.get('arrival_time')}", '%Y-%m-%d %H:%M') if data.get('arrival_date') and data.get('arrival_time') else None
            order.cabin_class = data.get('cabin_class')
            order.is_transit = True if data.get('is_transit') == 'on' else False
            order.transit_info = data.get('transit_info')
            order.order_status = data.get('order_status')
            order.payment_status = data.get('payment_status')
            order.payment_method = data.get('payment_method')
            order.total_price = float(data.get('total_price')) if data.get('total_price') else None
            order.tax_fee = float(data.get('tax_fee')) if data.get('tax_fee') else None
            order.actual_payment = float(data.get('actual_payment')) if data.get('actual_payment') else None
            order.operator = data.get('operator')
            order.refund_change_policy = data.get('refund_change_policy')
            order.baggage_allowance = data.get('baggage_allowance')
            order.pnr_code = data.get('pnr_code')
            order.e_ticket_number = data.get('e_ticket_number')
            order.client_type = data.get('client_type')
            order.remarks = data.get('remarks')
            
            # 如果订单状态为已出票，且出票时间为空，则设置当前时间为出票时间
            if order.order_status == '已出票' and not order.ticket_issue_time:
                order.ticket_issue_time = datetime.now()
            
            db.session.commit()
            
            flash('机票订单更新成功！', 'success')
            return redirect(url_for('flight_blue.view_flight_order', order_id=order.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新订单失败: {str(e)}', 'error')
            return redirect(url_for('flight_blue.edit_flight_order', order_id=order.id))


@flight_blue.route('/flight_order/<int:order_id>/delete', methods=['POST'])
def delete_flight_order(order_id):
    """删除机票订单"""
    order = FlightOrder.query.get_or_404(order_id)
    
    try:
        db.session.delete(order)
        db.session.commit()
        flash('机票订单已删除！', 'success')
        return redirect(url_for('flight_blue.flight_orders'))
    except Exception as e:
        db.session.rollback()
        flash(f'删除订单失败: {str(e)}', 'error')
        return redirect(url_for('flight_blue.view_flight_order', order_id=order.id))


@flight_blue.route('/flight_order/<int:order_id>/update_status', methods=['POST'])
def update_flight_order_status(order_id):
    """更新机票订单状态"""
    order = FlightOrder.query.get_or_404(order_id)
    
    try:
        new_status = request.form.get('order_status')
        if new_status:
            order.order_status = new_status
            
            # 如果订单状态为已出票，且出票时间为空，则设置当前时间为出票时间
            if new_status == '已出票' and not order.ticket_issue_time:
                order.ticket_issue_time = datetime.now()
                
            db.session.commit()
            flash('订单状态已更新！', 'success')
        else:
            flash('请提供有效的状态值！', 'error')
            
        return redirect(url_for('flight_blue.view_flight_order', order_id=order.id))
    except Exception as e:
        db.session.rollback()
        flash(f'更新状态失败: {str(e)}', 'error')
        return redirect(url_for('flight_blue.view_flight_order', order_id=order.id))
