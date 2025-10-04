# -*- coding: utf-8 -*-
"""
认证模块
"""

from .routes import register_auth_routes

def init_auth(app):
    """初始化认证模块"""
    register_auth_routes(app)
