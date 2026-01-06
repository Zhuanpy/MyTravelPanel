# -*- coding: utf-8 -*-
"""
设备检测工具
用于判断用户访问设备类型，自动路由到移动端或桌面端
"""

from flask import request, redirect, url_for
from functools import wraps


def is_mobile():
    """
    检测当前请求是否来自移动设备

    Returns:
        bool: True 如果是移动设备，False 如果是桌面设备
    """
    user_agent = request.headers.get('User-Agent', '').lower()

    # 移动设备关键词
    mobile_keywords = [
        'mobile',
        'android',
        'iphone',
        'ipad',
        'ipod',
        'windows phone',
        'blackberry',
        'opera mini',
        'opera mobi',
        'iemobile',
        'webos',
        'palm',
        'symbian'
    ]

    # 检查是否包含移动设备关键词
    return any(keyword in user_agent for keyword in mobile_keywords)


def is_tablet():
    """
    检测当前请求是否来自平板设备

    Returns:
        bool: True 如果是平板设备
    """
    user_agent = request.headers.get('User-Agent', '').lower()

    # 平板设备特征
    tablet_keywords = ['ipad', 'tablet', 'kindle', 'playbook']

    # iPad 或其他平板
    if any(keyword in user_agent for keyword in tablet_keywords):
        return True

    # Android 平板通常不包含 'mobile'
    if 'android' in user_agent and 'mobile' not in user_agent:
        return True

    return False


def get_device_type():
    """
    获取设备类型

    Returns:
        str: 'mobile', 'tablet', 或 'desktop'
    """
    if is_tablet():
        return 'tablet'
    elif is_mobile():
        return 'mobile'
    else:
        return 'desktop'


def mobile_redirect(mobile_endpoint):
    """
    装饰器：如果是移动设备，重定向到移动端页面

    用法:
        @mobile_redirect('mobile.dashboard')
        def dashboard():
            return render_template('staff/dashboard.html')

    Args:
        mobile_endpoint: 移动端路由端点名称
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 检查是否有强制桌面版参数
            force_desktop = request.args.get('desktop', '').lower() == 'true'

            if is_mobile() and not force_desktop:
                # 传递原始参数到移动端路由
                return redirect(url_for(mobile_endpoint, **kwargs))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def desktop_redirect(desktop_endpoint):
    """
    装饰器：如果是桌面设备，重定向到桌面端页面

    用法:
        @desktop_redirect('staff.dashboard')
        def mobile_dashboard():
            return render_template('mobile/dashboard.html')

    Args:
        desktop_endpoint: 桌面端路由端点名称
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 检查是否有强制移动版参数
            force_mobile = request.args.get('mobile', '').lower() == 'true'

            if not is_mobile() and not force_mobile:
                return redirect(url_for(desktop_endpoint, **kwargs))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# 注入模板上下文
def inject_device_context():
    """
    注入设备信息到模板上下文
    在 app 初始化时调用: app.context_processor(inject_device_context)
    """
    return {
        'is_mobile': is_mobile(),
        'is_tablet': is_tablet(),
        'device_type': get_device_type()
    }
