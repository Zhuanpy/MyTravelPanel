# -*- coding: utf-8 -*-
"""
认证路由模块
集中管理所有认证相关的路由
"""

from .admin import admin_auth_bp

# 导出所有蓝图
__all__ = [
    'admin_auth_bp'
]

def register_auth_routes(app):
    """注册所有认证路由到应用"""
    # 注册管理员认证路由
    app.register_blueprint(admin_auth_bp, url_prefix='/auth/admin')
