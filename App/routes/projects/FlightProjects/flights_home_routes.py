import os
import subprocess
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask import current_app as app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import NoResultFound

from App.code.FlightTicket.ConvertFlight.read_sql_data import original_airport_code_data, original_flight_timing_data

from App.models.Flightmodels import *
from App.models.Visamodels import *
from App.forms.flight_forms import FlightScheduleForm
from App.utils.decorators import login_required, admin_required

from App.code.utils.flightradar24 import get_flight_info

# 创建蓝图
flight_home = Blueprint('flight_home', __name__, url_prefix='/flight_home')


""" 航班信息录入"""

@flight_home.route('/flight_schedule', methods=['GET', 'POST'])
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


@flight_home.route('/flight_home')
def flight_home_page():
    """机票模块首页"""
    return render_template('flights/机票首页.html')

@flight_home.route('/search_flights', methods=['GET'])
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

@flight_home.route('/update_flight_timing', methods=['POST'])
def update_flight_timing_api():
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


@flight_home.route('/flight_airport_data')
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


@flight_home.route('/flight_schedule_data')
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


@flight_home.route('/open_project_folder', methods=['GET', 'POST'])
def open_project_folder():
    # 获取目标文件夹路径
    path_ = os.path.join(app.root_path, app.static_folder, "资源", "机票产品")

    # 检查路径是否有效
    if not os.path.exists(path_):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': '目标路径不存在：无法打开文件夹。'}), 404
        flash("目标路径不存在：无法打开文件夹。", category="error")
        return redirect(url_for('index.index'))

    # 尝试打开文件夹
    try:
        subprocess.Popen(f'explorer "{path_}"')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '文件夹已成功打开'})
        flash("文件夹已成功打开。", category="success")

    except Exception as e:
        error_message = f"无法打开文件夹，错误信息: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_message}), 500
        flash(error_message, category="error")

    # 只有在非AJAX请求时才重定向
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return redirect(url_for('index.index'))

@flight_home.route('/open_flight_project_folder', methods=['GET', 'POST'])
def open_flight_project_folder():
    # 获取目标文件夹路径
    path_ = os.path.join(app.root_path, app.static_folder, "资源", "Project", "机票")

    # 检查路径是否有效
    if not os.path.exists(path_):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': '项目文件夹路径不存在：无法打开文件夹。'}), 404
        flash("项目文件夹路径不存在：无法打开文件夹。", category="error")
        return redirect(url_for('index.index'))

    # 尝试打开文件夹
    try:
        subprocess.Popen(f'explorer "{path_}"')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '项目文件夹已成功打开'})
        flash("项目文件夹已成功打开。", category="success")

    except Exception as e:
        error_message = f"无法打开项目文件夹，错误信息: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_message}), 500
        flash(error_message, category="error")

    # 只有在非AJAX请求时才重定向
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return redirect(url_for('index.index'))

@flight_home.route('/open_refund_folder', methods=['GET', 'POST'])
def open_refund_folder():
    # 拼接目标文件夹路径  Project\机票\退票
    folder_path = os.path.join(app.root_path, app.static_folder, "资源", "Project","机票","退票")

    # 检查路径是否存在
    if not os.path.exists(folder_path):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': '退票文件夹路径不存在'}), 404
        flash("退票文件夹路径不存在：无法打开文件夹。", category="error")
        return redirect(url_for('index.index'))

    # 尝试打开文件夹
    try:
        subprocess.Popen(f'explorer "{folder_path}"')  # 使用 Windows 的文件资源管理器打开文件夹
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '退票文件夹已成功打开'})
        flash("退票文件夹已成功打开。", category="success")

    except Exception as e:
        error_message = f"无法打开退款政策文件夹，错误信息: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_message}), 500
        flash(error_message, category="error")

    # 只有在非AJAX请求时才重定向
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return redirect(url_for('index.index'))

@flight_home.route('/确认单详细')
def confirmation_detail():
    return render_template('flights/flight_confirmation_detail.html')

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
