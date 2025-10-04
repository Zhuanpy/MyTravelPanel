# -*- coding: utf-8 -*-
"""
认证路由模块
集中管理所有认证相关的路由
"""

from .member import member_auth_bp
from .staff import staff_auth_bp
from .admin import admin_auth_bp
from .api import auth_api_bp
from .common import common_auth_bp

# 导出所有蓝图
__all__ = [
    'member_auth_bp',
    'staff_auth_bp', 
    'admin_auth_bp',
    'auth_api_bp',
    'common_auth_bp'
]

def register_auth_routes(app):
    """注册所有认证路由到应用"""
    # 注册会员认证路由
    app.register_blueprint(member_auth_bp, url_prefix='/auth/member')
    
    # 注册员工认证路由
    app.register_blueprint(staff_auth_bp, url_prefix='/auth/staff')
    
    # 注册管理员认证路由
    app.register_blueprint(admin_auth_bp, url_prefix='/auth/admin')
    
    # 注册认证API路由
    app.register_blueprint(auth_api_bp, url_prefix='/auth')
    
    # 注册通用认证路由
    app.register_blueprint(common_auth_bp, url_prefix='/auth')
