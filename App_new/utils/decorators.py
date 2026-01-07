# -*- coding: utf-8 -*-
"""
装饰器模块
提供各种权限控制和功能装饰器
"""

from functools import wraps
from flask import request, redirect, url_for, flash, current_app
from flask_login import current_user


def guest_only(f):
    """
    访客专用装饰器
    只允许未登录用户访问，已登录用户会被重定向
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            # 根据用户角色重定向到相应的仪表板
            if hasattr(current_user, 'role'):
                if current_user.role.name == 'member':
                    return redirect(url_for('member.dashboard'))
                elif current_user.role.name == 'staff':
                    return redirect(url_for('staff.dashboard'))
                elif current_user.role.name == 'admin':
                    return redirect(url_for('admin.dashboard'))
            # 默认重定向到首页
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    """
    登录必需装饰器
    要求用户必须登录才能访问（重定向到会员登录）
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth_profile.member_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(role_name):
    """
    角色权限装饰器
    要求用户具有指定角色才能访问
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth_profile.member_login', next=request.url))

            if not hasattr(current_user, 'role') or current_user.role.name != role_name:
                flash('您没有权限访问此页面', 'error')
                return redirect(url_for('public.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_only(f):
    """管理员专用装饰器"""
    return role_required('admin')(f)


def staff_only(f):
    """员工专用装饰器"""
    return role_required('staff')(f)


def member_only(f):
    """会员专用装饰器"""
    return role_required('member')(f)


def staff_level_required(min_level=1):
    """
    员工等级权限装饰器
    要求员工具有指定等级或更高等级才能访问
    min_level: 最低要求的员工等级 (1-普通员工, 2-高级员工)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth_profile.staff_login', next=request.url))

            # 检查用户是否为员工
            if not hasattr(current_user, 'role') or current_user.role.name != 'staff':
                flash('此功能仅限员工使用', 'error')
                return redirect(url_for('public.index'))

            # 检查员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1

            if staff_level < min_level:
                flash(f'此功能需要员工等级{min_level}或以上，您当前的等级为{staff_level}', 'error')
                return redirect(url_for('public.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def staff_level_2_only(f):
    """仅限2级员工（高级员工）访问的装饰器"""
    return staff_level_required(2)(f)


def permission_required(permission):
    """
    权限检查装饰器
    检查用户是否具有指定权限
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth_profile.member_login', next=request.url))

            if not hasattr(current_user, 'has_permission') or not current_user.has_permission(permission):
                flash('您没有权限执行此操作', 'error')
                return redirect(request.referrer or url_for('public.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def api_key_required(f):
    """
    API密钥验证装饰器
    用于API接口的认证
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return {'error': 'API key is required'}, 401
        
        # TODO: 验证API密钥的有效性
        # 这里可以从数据库或配置文件中验证API密钥
        
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(max_requests=100, per_seconds=3600):
    """
    速率限制装饰器
    限制用户在指定时间内的请求次数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # TODO: 实现速率限制逻辑
            # 可以使用Redis或内存缓存来跟踪请求频率
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def cache_result(timeout=300):
    """
    结果缓存装饰器
    缓存函数的返回结果
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # TODO: 实现缓存逻辑
            # 可以使用Flask-Cache或Redis来缓存结果
            return f(*args, **kwargs)
        return decorated_function
    return decorator