# -*- coding: utf-8 -*-
"""权限装饰器"""

from functools import wraps
from flask import redirect, url_for

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 登录验证逻辑
        return f(*args, **kwargs)
    return decorated_function
