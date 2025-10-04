# -*- coding: utf-8 -*-
"""
管理员认证功能路由
管理员登录等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user
from ..models import AuthUser
from ...utils.decorators import guest_only

# 创建管理员认证蓝图
admin_auth_bp = Blueprint('admin_auth', __name__)

@admin_auth_bp.route('/login', methods=['GET', 'POST'])
@guest_only
def login():
    """管理员登录"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))
            
            # 基础验证
            if not email or not password:
                flash('请填写邮箱和密码', 'error')
                return render_template('auth/admin_login.html')
            
            # 查找用户
            user = AuthUser.query.filter_by(email=email).first()
            
            if not user:
                flash('邮箱或密码错误', 'error')
                return render_template('auth/admin_login.html')
            
            # 检查用户角色
            if not user.role or user.role.name != 'admin':
                flash('您没有管理员权限', 'error')
                return render_template('auth/admin_login.html')
            
            # 检查用户状态
            if not user.is_active:
                flash('账户已被禁用，请联系系统管理员', 'error')
                return render_template('auth/admin_login.html')
            
            # 检查账户锁定状态
            if user.is_account_locked():
                flash('账户已被锁定，请24小时后再试或联系系统管理员', 'error')
                return render_template('auth/admin_login.html')
            
            # 验证密码
            # 检查数据库中存储的密码（支持明文密码）
            if password == user.password_hash:
                # 登录成功
                login_user(user, remember=remember)
                user.record_login_success()
                flash('登录成功！', 'success')
                
                # 获取重定向目标
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/admin/'):
                    return redirect(next_page)
                return redirect(url_for('admin.dashboard'))
            else:
                # 密码错误
                user.record_login_failure()
                flash('邮箱或密码错误', 'error')
                
        except Exception as e:
            flash(f'登录失败：{str(e)}', 'error')
    
    return render_template('auth/admin_login.html')
