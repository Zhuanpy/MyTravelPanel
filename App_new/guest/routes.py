# -*- coding: utf-8 -*-
"""
访客/公开页面路由主文件
整合所有子路由模块
"""

from flask import Blueprint

# 创建主访客蓝图
guest_bp = Blueprint('guest', __name__, 
                     template_folder='templates',
                     static_folder='../static/guest')

# 导入所有子蓝图
from .route_modules import visa, tour, api, main, debug, errors

# 注册所有子蓝图到主蓝图
guest_bp.register_blueprint(visa.visa_bp)
guest_bp.register_blueprint(tour.tour_bp)
guest_bp.register_blueprint(api.api_bp)
guest_bp.register_blueprint(main.main_bp)
guest_bp.register_blueprint(debug.debug_bp)
guest_bp.register_blueprint(errors.errors_bp)
