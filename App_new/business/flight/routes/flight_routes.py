from datetime import datetime, timedelta
from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from ..models.models import FlightOrder
from App_new.business.projects.models.project import ProjectHeader
from App_new.utils.decorators import staff_only
from sqlalchemy import and_, or_

# 创建蓝图
flight_routes = Blueprint('flight_routes', __name__, url_prefix='/flight_routes')

@flight_routes.route('/order/list')
@login_required
@staff_only
def order_list():
    # 获取筛选参数
    departure_filter = request.args.get('departure_filter')
    
    # 基础查询
    query = FlightOrder.query
    
    # 根据员工等级过滤订单
    if current_user.role and current_user.role.name == 'staff':
        # 检查用户资料中的员工等级
        staff_level = 1  # 默认等级
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1
        
        if staff_level == 1:
            # 1级员工只能看到自己创建的订单
            # 通过关联的ProjectHeader表进行过滤
            query = query.join(ProjectHeader, FlightOrder.project_header_id == ProjectHeader.id)\
                         .filter(ProjectHeader.staff_name == current_user.username)
        # 2级员工可以看到所有订单，不需要额外过滤
    
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