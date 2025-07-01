from datetime import datetime, timedelta
from flask import request, render_template
from App.models.Flightmodels import FlightOrder
from sqlalchemy import and_, or_

@flight_routes.route('/order/list')
def order_list():
    # 获取筛选参数
    departure_filter = request.args.get('departure_filter')
    
    # 基础查询
    query = FlightOrder.query
    
    # 根据出发日期筛选
    today = datetime.now().date()
    if departure_filter == 'today':
        # 今日出发
        query = query.filter(FlightOrder.departure_date == today)
    elif departure_filter == 'upcoming':
        # 未来3天内出发
        three_days_later = today + timedelta(days=3)
        query = query.filter(and_(
            FlightOrder.departure_date >= today,
            FlightOrder.departure_date <= three_days_later
        ))
    
    # 获取订单列表
    orders = query.order_by(FlightOrder.departure_date).all()
    
    return render_template('flights/order_list.html', 
                         orders=orders,
                         departure_filter=departure_filter) 