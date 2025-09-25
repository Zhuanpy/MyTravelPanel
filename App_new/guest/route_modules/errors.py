# -*- coding: utf-8 -*-
"""
错误处理相关路由
"""

from flask import Blueprint, render_template

# 创建错误处理蓝图
errors_bp = Blueprint('errors', __name__)

@errors_bp.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return render_template('guest/shared/404.html', message='页面未找到'), 404

@errors_bp.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return render_template('guest/shared/404.html', message='服务器内部错误'), 500
