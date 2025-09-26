# -*- coding: utf-8 -*-
"""
认证功能路由
用户注册、登录、登出等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from .models import AuthUser, Role
from ..utils.decorators import guest_only
from ..exts import db, csrf
import re

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth', template_folder='templates')

@auth_bp.route('/member/login', methods=['GET', 'POST'])
@guest_only
def member_login():
    """会员登录"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))
            
            # 基础验证
            if not email or not password:
                flash('请填写邮箱和密码', 'error')
                return render_template('auth/member_login.html')
            
            # 查找用户
            user = AuthUser.query.filter_by(email=email).first()
            
            if not user:
                flash('邮箱或密码错误', 'error')
                return render_template('auth/member_login.html')
            
            # 检查用户状态
            if not user.is_active:
                flash('账户已被禁用，请联系管理员', 'error')
                return render_template('auth/member_login.html')
            
            # 检查账户锁定状态
            if user.is_account_locked():
                flash('账户已被锁定，请24小时后再试或联系管理员', 'error')
                return render_template('auth/member_login.html')
            
            # 验证密码
            if user.check_password(password):
                # 检查用户角色
                if user.role.name != 'member':
                    flash('请使用正确的登录入口', 'error')
                    return render_template('auth/member_login.html')
                
                # 登录成功
                login_user(user, remember=remember)
                user.record_login_success()
                flash('登录成功！', 'success')
                
                # 重定向到会员仪表板
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/member/'):
                    return redirect(next_page)
                
                return redirect(url_for('member.dashboard'))
            else:
                # 登录失败，记录失败次数
                user.record_login_failure()
                
                # 根据失败次数显示不同的提示信息
                remaining_attempts = 5 - user.login_attempts
                if remaining_attempts > 0:
                    flash(f'邮箱或密码错误，还剩{remaining_attempts}次尝试机会', 'error')
                else:
                    flash('登录失败次数过多，账户已被锁定24小时', 'error')
                
        except Exception as e:
            flash(f'登录失败：{str(e)}', 'error')
    
    return render_template('auth/member_login.html')

@auth_bp.route('/member/register', methods=['GET', 'POST'])
@guest_only
def member_register():
    """会员注册"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # 基础验证
            if not all([username, email, password, confirm_password]):
                flash('请填写所有必填字段', 'error')
                return render_template('auth/member_register.html')
            
            # 用户名验证
            if len(username) < 3:
                flash('用户名长度至少为3位', 'error')
                return render_template('auth/member_register.html')
            
            # 邮箱格式验证
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                flash('请输入有效的邮箱地址', 'error')
                return render_template('auth/member_register.html')
            
            # 密码验证
            if password != confirm_password:
                flash('两次输入的密码不一致', 'error')
                return render_template('auth/member_register.html')
            
            if len(password) < 6:
                flash('密码长度至少为6位', 'error')
                return render_template('auth/member_register.html')
            
            # 检查用户名是否已存在
            if AuthUser.query.filter_by(username=username).first():
                flash('该用户名已被使用', 'error')
                return render_template('auth/member_register.html')
            
            # 检查邮箱是否已存在
            if AuthUser.query.filter_by(email=email).first():
                flash('该邮箱已被注册', 'error')
                return render_template('auth/member_register.html')
            
            # 获取会员角色
            member_role = Role.query.filter_by(name='member').first()
            if not member_role:
                flash('系统错误：会员角色不存在', 'error')
                return render_template('auth/member_register.html')
            
            # 创建新用户
            user = AuthUser(
                username=username,
                email=email,
                role_id=member_role.id,
                is_active=True,
                is_verified=True  # 自动验证新注册用户
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('注册成功！请登录您的账户', 'success')
            return redirect(url_for('auth.member_login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败：{str(e)}', 'error')
    
    return render_template('auth/member_register.html')

@auth_bp.route('/staff/login', methods=['GET', 'POST'])
@guest_only
def staff_login():
    """员工登录"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))
            
            # 基础验证
            if not email or not password:
                flash('请填写邮箱和密码', 'error')
                return render_template('auth/staff_login.html')
            
            # 查找用户
            user = AuthUser.query.filter_by(email=email).first()
            
            if not user:
                flash('邮箱或密码错误', 'error')
                return render_template('auth/staff_login.html')
            
            # 检查用户角色
            if not user.role or user.role.name != 'staff':
                flash('您没有员工权限', 'error')
                return render_template('auth/staff_login.html')
            
            # 检查用户状态
            if not user.is_active:
                flash('账户已被禁用，请联系管理员', 'error')
                return render_template('auth/staff_login.html')
            
            # 检查账户锁定状态
            if user.is_account_locked():
                flash('账户已被锁定，请24小时后再试或联系管理员', 'error')
                return render_template('auth/staff_login.html')
            
            # 验证密码
            if user.check_password(password):
                # 登录成功
                login_user(user, remember=remember)
                user.record_login_success()
                flash('登录成功！', 'success')
                
                # 获取重定向目标
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/staff/'):
                    return redirect(next_page)
                return redirect(url_for('staff.dashboard'))
            else:
                # 密码错误
                user.record_login_failure()
                flash('邮箱或密码错误', 'error')
                
        except Exception as e:
            flash(f'登录失败：{str(e)}', 'error')
    
    return render_template('auth/staff_login.html')

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
@guest_only
def admin_login():
    """管理员登录"""
    # TODO: 实现管理员登录逻辑
    return render_template('auth/admin_login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功退出登录', 'info')
    return redirect(url_for('guest.main.index'))

# API 路由
@auth_bp.route('/api/check-email')
def api_check_email():
    """检查邮箱是否可用"""
    email = request.args.get('email', '').strip()
    
    if not email:
        return jsonify({'available': False, 'message': '请输入邮箱地址'})
    
    # 邮箱格式验证
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return jsonify({'available': False, 'message': '邮箱格式不正确'})
    
    # 检查是否已存在
    if AuthUser.query.filter_by(email=email).first():
        return jsonify({'available': False, 'message': '该邮箱已被注册'})
    
    return jsonify({'available': True, 'message': '邮箱可用'})