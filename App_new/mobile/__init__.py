# -*- coding: utf-8 -*-
"""
移动端模块
提供针对手机优化的简化版界面
"""

from flask import Blueprint

mobile_bp = Blueprint('mobile', __name__, url_prefix='/m')

from . import routes
