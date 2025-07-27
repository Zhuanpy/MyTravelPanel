"""
认证功能路由
用户注册、登录、登出等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from App.models.auth import AuthUser, Role, UserProfile
from App.utils.decorators import guest_only, member_only
from App.exts import db
import re

# 创建认证蓝图
auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/register', methods=['GET', 'POST'])
@guest_only
def register():
    """用户注册"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            
            # 基础验证
            if not all([email, password, confirm_password, first_name]):
                flash('请填写所有必填字段', 'error')
                return render_template('auth/register.html')
            
            # 邮箱格式验证
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                flash('请输入有效的邮箱地址', 'error')
                return render_template('auth/register.html')
            
            # 密码验证
            if password != confirm_password:
                flash('两次输入的密码不一致', 'error')
                return render_template('auth/register.html')
            
            if len(password) < 6:
                flash('密码长度至少6位', 'error')
                return render_template('auth/register.html')
            
            # 检查邮箱是否已存在
            existing_user = AuthUser.query.filter_by(email=email).first()
            if existing_user:
                flash('该邮箱已被注册', 'error')
                return render_template('auth/register.html')
            
            # 获取会员角色（公开注册只能注册为会员）
            member_role = Role.query.filter_by(name='member').first()
            if not member_role:
                flash('系统错误：会员角色不存在', 'error')
                return render_template('auth/register.html')
            
            # 创建新用户（通过公开注册的用户只能是会员客户）
            # 使用邮箱前缀作为用户名，如果重复则添加数字后缀
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while AuthUser.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            new_user = AuthUser(
                username=username,
                email=email,
                role_id=member_role.id  # 公开注册只能是会员
            )
            new_user.set_password(password)
            
            # 保存用户到数据库
            db.session.add(new_user)
            db.session.commit()
            
            # 创建用户资料
            user_profile = UserProfile(
                user_id=new_user.id,
                first_name=first_name,
                last_name=last_name,
                phone=phone
            )
            db.session.add(user_profile)
            db.session.commit()
            
            flash('注册成功！请登录', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败：{str(e)}', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth.route('/login', methods=['GET', 'POST'])
@guest_only
def login():
    """用户登录"""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))
            
            if not email or not password:
                flash('请输入邮箱和密码', 'error')
                return render_template('auth/login.html')
            
            # 查找用户
            user = AuthUser.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                # 登录成功
                login_user(user, remember=remember)
                
                # 重定向到原来想访问的页面或默认页面
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                
                # 根据用户角色重定向到不同页面
                if user.role.name == 'admin':
                    # 管理员跳转到管理员后台
                    return redirect(url_for('admin.dashboard'))
                elif user.role.name == 'staff':
                    # 员工跳转到员工工作台
                    return redirect(url_for('staff.dashboard'))
                elif user.role.name == 'member':
                    # 会员跳转到会员中心
                    return redirect(url_for('member.dashboard'))
                else:
                    # 其他情况跳转到公开页面
                    flash('登录成功，但用户角色未知', 'warning')
                    return redirect(url_for('public.index'))
            else:
                flash('邮箱或密码错误', 'error')
                
        except Exception as e:
            flash(f'登录失败：{str(e)}', 'error')
    
    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('public.index'))

@auth.route('/profile')
@login_required
@member_only
def profile():
    """用户资料页面"""
    return render_template('auth/profile.html', user=current_user)

@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@member_only
def edit_profile():
    """编辑用户资料"""
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            
            if not first_name:
                flash('姓名不能为空', 'error')
                return render_template('auth/edit_profile.html', user=current_user)
            
            # 更新用户资料
            if current_user.profile:
                current_user.profile.first_name = first_name
                current_user.profile.last_name = last_name
                current_user.profile.phone = phone
                current_user.profile.address = address
            else:
                # 如果用户没有资料，创建新的
                profile = UserProfile(
                    user_id=current_user.id,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    address=address
                )
                db.session.add(profile)
            
            db.session.commit()
            flash('资料更新成功', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    return render_template('auth/edit_profile.html', user=current_user)

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
@member_only
def change_password():
    """修改密码"""
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not all([current_password, new_password, confirm_password]):
                flash('请填写所有字段', 'error')
                return render_template('auth/change_password.html')
            
            # 验证当前密码
            if not current_user.check_password(current_password):
                flash('当前密码错误', 'error')
                return render_template('auth/change_password.html')
            
            # 验证新密码
            if new_password != confirm_password:
                flash('两次输入的新密码不一致', 'error')
                return render_template('auth/change_password.html')
            
            if len(new_password) < 6:
                flash('新密码长度至少6位', 'error')
                return render_template('auth/change_password.html')
            
            # 更新密码
            current_user.set_password(new_password)
            db.session.commit()
            
            flash('密码修改成功', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'修改密码失败：{str(e)}', 'error')
    
    return render_template('auth/change_password.html')

# API 路由
@auth.route('/api/check-email')
def api_check_email():
    """检查邮箱是否已存在"""
    email = request.args.get('email', '').strip()
    
    if not email:
        return jsonify({'available': False, 'message': '邮箱不能为空'})
    
    # 邮箱格式验证
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return jsonify({'available': False, 'message': '邮箱格式不正确'})
    
    # 检查是否已存在
    existing_user = AuthUser.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'available': False, 'message': '该邮箱已被注册'})
    
    return jsonify({'available': True, 'message': '邮箱可用'}) 