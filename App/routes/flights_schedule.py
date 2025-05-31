from flask import request, jsonify, render_template, Blueprint
from App.models.flight_schedule import FlightSchedule
from App import db

# 创建Blueprint
flights_schedule = Blueprint('flights_schedule', __name__, url_prefix='/flight_schedule')

@flights_schedule.route('/input_flight_schedule_info', methods=['GET', 'POST'])
def input_flight_schedule_info():
    """处理航班时刻表信息输入"""
    if request.method == 'GET':
        # 获取搜索参数
        search_flight_number = request.args.get('search_flight_number', '')
        page = request.args.get('page', 1, type=int)
        
        # 构建查询
        query = FlightSchedule.query
        if search_flight_number:
            query = query.filter(FlightSchedule.flight_number.ilike(f'%{search_flight_number}%'))
        
        # 分页
        flights = query.order_by(FlightSchedule.flight_number).paginate(
            page=page, per_page=10, error_out=False)
        
        return render_template('flights/flight_schedule_input.html',
                             flights=flights,
                             search_flight_number=search_flight_number)
    
    elif request.method == 'POST':
        # 处理POST请求的逻辑保持不变
        # ... 原有的POST处理代码 ...
        pass

@flights_schedule.route('/get-flight-info')
def get_flight_info():
    """获取航班信息"""
    flight_number = request.args.get('flight_number')
    if not flight_number:
        return jsonify({
            'success': False,
            'message': '请提供航班号'
        }), 400
        
    try:
        # 从数据库查询航班信息
        flight = FlightSchedule.query.filter_by(flight_number=flight_number).first()
        
        if flight:
            return jsonify({
                'success': True,
                'data': {
                    'schedule_city': flight.schedule_city,
                    'schedule_timing': flight.schedule_timing
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '未找到航班信息'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def search_flight_in_database(flight_number):
    """在数据库中搜索航班信息"""
    # 这里实现您的航班搜索逻辑
    # 返回航班信息或None
    return None  # 临时返回None，您需要实现实际的搜索逻辑 