from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    """
    登录验证装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
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
        if not session.get('is_admin'):
            flash('需要管理员权限', 'error')
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)
    return decorated_function 