# -*- coding: utf-8 -*-
"""
管理员认证功能路由
管理员登录等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user
from ..models import AuthUser
from ...utils.decorators import guest_only

# 创建管理员认证蓝图
admin_auth_bp = Blueprint('admin_auth', __name__)


def is_mobile_device():
    """检测是否为移动设备"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)


@admin_auth_bp.route('/login', methods=['GET', 'POST'])
@guest_only
def login():
    """管理员登录"""
    # 选择模板
    template = 'mobile/login.html' if is_mobile_device() else 'auth/admin_login.html'

    if request.method == 'POST':
        try:
            # 获取表单数据
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))
            
            # 基础验证
            if not email or not password:
                flash('请填写邮箱和密码', 'error')
                return render_template(template)

            # 查找用户
            user = AuthUser.query.filter_by(email=email).first()

            if not user:
                flash('邮箱或密码错误', 'error')
                return render_template(template)

            # 检查用户角色（管理员或员工都可以登录）
            if not user.role or user.role.name not in ['admin', 'staff']:
                flash('您没有登录权限', 'error')
                return render_template(template)

            # 检查用户状态
            if not user.is_active:
                flash('账户已被禁用，请联系系统管理员', 'error')
                return render_template(template)

            # 检查账户锁定状态
            if user.is_account_locked():
                flash('账户已被锁定，请24小时后再试或联系系统管理员', 'error')
                return render_template(template)
            
            # 验证密码
            # 检查数据库中存储的密码（支持明文密码）
            if password == user.password_hash:
                # 登录成功
                login_user(user, remember=remember)
                user.record_login_success()

                # 存储会话版本用于密码修改后强制登出其他设备
                session['session_version'] = user.session_version

                flash('登录成功！', 'success')

                # 获取重定向目标
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)

                # 根据设备类型和用户角色重定向
                if is_mobile_device():
                    return redirect(url_for('mobile.staff_dashboard'))
                elif user.role.name == 'admin':
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('staff.dashboard'))
            else:
                # 密码错误
                user.record_login_failure()
                flash('邮箱或密码错误', 'error')

        except Exception as e:
            flash(f'登录失败：{str(e)}', 'error')

    return render_template(template)
