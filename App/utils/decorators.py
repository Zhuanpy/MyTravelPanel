from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user
from .exceptions import AuthenticationError, AuthorizationError

def login_required(f):
    """
    登录验证装饰器 - 支持API和Web请求
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                raise AuthenticationError("Authentication required")
            else:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    管理员权限验证装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                raise AuthenticationError("Authentication required")
            else:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))

        if current_user.role != 'admin':
            if request.is_json:
                raise AuthorizationError("Admin privileges required")
            else:
                flash('需要管理员权限', 'error')
                return redirect(url_for('index.index'))

        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """
    角色权限验证装饰器
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    raise AuthenticationError("Authentication required")
                else:
                    flash('请先登录', 'warning')
                    return redirect(url_for('auth.login'))

            if current_user.role not in roles:
                if request.is_json:
                    raise AuthorizationError(f"Required roles: {', '.join(roles)}")
                else:
                    flash('权限不足', 'error')
                    return redirect(url_for('index.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission):
    """
    权限验证装饰器（为未来扩展准备）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    raise AuthenticationError("Authentication required")
                else:
                    flash('请先登录', 'warning')
                    return redirect(url_for('auth.login'))

            # 这里可以实现更复杂的权限检查逻辑
            # 例如检查用户是否有特定的权限

            return f(*args, **kwargs)
        return decorated_function
    return decorator