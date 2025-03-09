import os
import subprocess
import re

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask import current_app as app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import NoResultFound
from flask_caching import Cache

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
    """
    合并 Athina 机票订单页面加载和处理逻辑。
    """
    if request.method == 'GET':
        # 返回 Athina 机票订单输入页面
        return render_template('flights/ATHINA系统航班预定代码.html')

    if request.method == 'POST':
        try:
            # 解析请求数据
            data = request.json

            if not data:
                return jsonify({'error': '未提供任何订单数据'}), 400

            itinerary = ""
            num = 1  # 订单编号

            # 处理每个订单条目
            for entry in data:
                flight_number = entry.get('flightNumber', '').replace(" ", "").upper()
                flight_date = entry.get('flightDate', '')
                
                if not flight_number or not flight_date:
                    return jsonify({'error': f'订单条目 {num} 缺少航班号或日期'}), 400

                # 获取航班时刻表信息
                schedule_dic = request_schedule_data(flight_number)

                if not schedule_dic:
                    return jsonify({
                        'error': f'未找到航班号 {flight_number} 的时刻表数据。请先在航班时刻表中添加该航班信息。'
                    }), 404

                try:
                    # 使用航班工具生成预订代码并添加到行程
                    r = flight.athina_booking_code(num, schedule_dic, flight_date)

                    if r.startswith("An error occurred") or r.startswith("Database error"):
                        return jsonify({'error': r}), 500
                    itinerary += f"{r}\n"
                    num += 1
                except Exception as e:
                    return jsonify({
                        'error': f'生成航班 {flight_number} 的预订代码时出错：{str(e)}'
                    }), 500

            return jsonify({'itinerary': itinerary})

        except Exception as e:
            print(f"Error in flight_to_athina_page: {str(e)}")  # 调试信息
            return jsonify({'error': str(e)}), 500


""" 航班信息录入"""


@login_required
@admin_required
@flight_blue.route('/flight_schedule', methods=['GET', 'POST'])
def input_flight_schedule_info():
    form = FlightScheduleForm()
    if form.validate_on_submit():
        try:
            flight_service = FlightService()
            result = flight_service.create_or_update_schedule(form.data)
            flash(result['message'], 'success')
            return redirect(url_for('flight_routes.input_flight_schedule_info'))
        except Exception as e:
            flash(str(e), 'error')
            return render_template('flights/schedule_form.html', form=form)
    return render_template('flights/schedule_form.html', form=form)


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
        iata_list = request.form.getlist('iata[]')
        city_list = request.form.getlist('city[]')

        airport_name_cn_list = request.form.getlist('airportNameCN[]')
        airport_name_en_list = request.form.getlist('airportNameEN[]')

        # 简单验证
        for iata, city, name_cn, name_en in zip(iata_list, city_list, airport_name_cn_list, airport_name_en_list):

            if not iata or not city or not name_cn or not name_en:
                flash('所有字段都是必填项。', 'error')
                return render_template('flights/录入机场代码.html')

            if len(iata) != 3:
                flash(f'IATA 代码 "{iata}" 必须是3个字符。', 'error')
                return render_template('flights/录入机场代码.html')

            # 检查 IATA 是否已存在
            existing_airport = AirportData.query.filter_by(airport_IATA=iata.upper()).first()
            if existing_airport:
                flash(f'IATA 代码 "{iata}" 已存在。', 'error')
                return render_template('flights/录入机场代码.html')

        # 成功处理后可以执行后续操作，如保存数据等
        return redirect(url_for('flight_routes.input_airport_code_info'))

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

@flight_blue.route('/确认单详细')
def confirmation_detail():
    return render_template('flights/确认单详细.html')

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

@flight_blue.route('/generate_filename', methods=['POST'])
def generate_filename():
    try:
        data = request.get_json()
        required_fields = ['hid', 'surname', 'given_name']
        
        # 检查必要字段
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'缺少必要字段：{", ".join(missing_fields)}'
            }), 400

        # 转换日期格式
        formatted_date = convert_date_format(data.get('date', ''))

        return jsonify({
            'status': 'success',
            'data': {
                'etk_filename': f"HID{data['hid']}_ETK_{data['surname']} {data['given_name']}",
                'inv_filename': f"HID{data['hid']}_INV_{data['surname']} {data['given_name']}",
                'email_subject': f"HID{data['hid']} {formatted_date} {data.get('airline_code', '')} {data.get('dep_city', '')} {data.get('arr_city', '')} ( {data['surname']} {data['given_name']} )".strip()
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@flight_blue.route('/generate_docs', methods=['POST'])
def generate_docs():
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['surname', 'given_name', 'passport', 'nationality', 'passport_expiry', 'birth_date', 'airline_code', 'sex']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'缺少必要字段：{", ".join(missing_fields)}'
            }), 400

        # 验证日期格式
        date_pattern = r'^\d{2}/\d{2}/\d{4}$'
        if not re.match(date_pattern, data['passport_expiry']) or not re.match(date_pattern, data['birth_date']):
            return jsonify({
                'status': 'error',
                'message': '日期格式不正确，请使用 DD/MM/YYYY 格式'
            }), 400

        # 日期格式转换函数
        def convert_date_format(date_str):
            day, month, year = date_str.split('/')
            month_map = {
                '01': 'JAN', '02': 'FEB', '03': 'MAR', '04': 'APR',
                '05': 'MAY', '06': 'JUN', '07': 'JUL', '08': 'AUG',
                '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC'
            }
            return f"{(day)}{month_map[month]}{year[2:]}"

        # 转换日期格式
        birth_date = convert_date_format(data['birth_date'])
        passport_expiry = convert_date_format(data['passport_expiry'])

        # 验证国籍代码长度
        if len(data['nationality']) != 3:
            return jsonify({
                'status': 'error',
                'message': '国籍代码必须是3个字符'
            }), 400

        # 验证航司代码长度
        if len(data['airline_code']) != 2:
            return jsonify({
                'status': 'error',
                'message': '航司代码必须是2个字符'
            }), 400

        # 验证性别
        if data['sex'] not in ['M', 'F']:
            return jsonify({
                'status': 'error',
                'message': '性别必须是 M 或 F'
            }), 400

        # 生成 DOCS 代码
        # SI.P1/SSRDOCSMFHK1/P/CHN/S12345678/CHN/12JUL76/M/23OCT16/SMITH
        docs_code = f"SI.P1/SSRDOCS{data['airline_code']}HK1/P/{data['nationality']}/{data['passport']}/{data['nationality']}/{birth_date}/{data['sex']}/{passport_expiry}/{data['surname']}/{data['given_name']}"
        return jsonify({
            'status': 'success',
            'data': {
                'docs_code': docs_code
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@flight_blue.route('/some_protected_route')
@login_required
def protected_view():
    return "只有登录用户才能看到这个页面"

@flight_blue.route('/admin_only_route')
@login_required
@admin_required
def admin_view():
    return "只有管理员才能看到这个页面"

@flight_blue.route('/company_header')
def company_header():
    return render_template('company/company_header.html')
