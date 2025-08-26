"""
权限检查装饰器
"""
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user
from App.utils.permissions import has_permission, has_role


def require_permission(permission):
    """
    要求特定权限的装饰器

    Args:
        permission: 权限名称

    Returns:
        decorator: 装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))

            if not has_permission(current_user, permission):
                flash('您没有权限访问此页面', 'error')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(role_name):
    """
    要求特定角色的装饰器

    Args:
        role_name: 角色名称

    Returns:
        decorator: 装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))

            if not has_role(current_user, role_name):
                flash('您没有权限访问此页面', 'error')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_any_role(*role_names):
    """
    要求任意一个角色的装饰器

    Args:
        *role_names: 角色名称列表

    Returns:
        decorator: 装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))

            # 检查用户是否有任意一个指定角色
            user_has_role = any(has_role(current_user, role_name) for role_name in role_names)

            if not user_has_role:
                flash('您没有权限访问此页面', 'error')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_any_permission(*permissions):
    """
    要求任意一个权限的装饰器

    Args:
        *permissions: 权限名称列表

    Returns:
        decorator: 装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))

            # 检查用户是否有任意一个指定权限
            user_has_permission = any(has_permission(current_user, permission) for permission in permissions)

            if not user_has_permission:
                flash('您没有权限访问此页面', 'error')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def guest_only(f):
    """
    仅访客可访问的装饰器

    Args:
        f: 视图函数

    Returns:
        decorated_function: 装饰后的函数
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            flash('您已登录，无法访问此页面', 'info')
            # 根据用户角色重定向到相应的仪表板
            if current_user.role and current_user.role.name == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role and current_user.role.name == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif current_user.role and current_user.role.name == 'member':
                return redirect(url_for('member.dashboard'))
            else:
                return redirect(url_for('public.index'))

        return f(*args, **kwargs)
    return decorated_function


def admin_only(f):
    """
    仅管理员可访问的装饰器

    Args:
        f: 视图函数

    Returns:
        decorated_function: 装饰后的函数
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))

        if not has_role(current_user, 'admin'):
            flash('仅管理员可访问此页面', 'error')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def staff_only(f):
    """
    仅员工可访问的装饰器

    Args:
        f: 视图函数

    Returns:
        decorated_function: 装饰后的函数
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))

        if not has_role(current_user, 'staff') and not has_role(current_user, 'admin'):
            flash('仅员工可访问此页面', 'error')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def member_only(f):
    """
    仅会员可访问的装饰器

    Args:
        f: 视图函数

    Returns:
        decorated_function: 装饰后的函数
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))

        if not (has_role(current_user, 'member') or has_role(current_user, 'staff') or has_role(current_user, 'admin')):
            flash('仅会员可访问此页面', 'error')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function
