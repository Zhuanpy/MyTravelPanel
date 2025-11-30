"""
认证功能路由
用户注册、登录、登出等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from App_new.auth.models.auth import AuthUser, Role, UserProfile, InvitationCode, PasswordResetToken
from App_new.utils.decorators import guest_only, member_only
from App_new.exts import db
import re

# 创建用户认证蓝图（用户资料相关）
auth_profile = Blueprint('auth_profile', __name__, url_prefix='/auth')

@auth_profile.route('/register', methods=['GET', 'POST'])
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

@auth_profile.route('/login', methods=['GET', 'POST'])
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
            
            if not user:
                flash('邮箱或密码错误', 'error')
                return render_template('auth/login.html')
            
            # 检查账户是否被锁定
            if user.is_account_locked():
                remaining_minutes = user.get_remaining_lock_time()
                if remaining_minutes > 0:
                    flash(f'账户已被锁定，请{remaining_minutes}分钟后再试', 'error')
                else:
                    flash('账户已被锁定，请联系管理员解锁', 'error')
                return render_template('auth/login.html')
            
            # 检查账户是否被禁用
            if not user.is_active:
                flash('账户已被禁用，请联系管理员', 'error')
                return render_template('auth/login.html')
            
            if user.check_password(password):
                # 登录成功，记录成功登录并重置失败计数
                user.record_login_success()
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
                    return redirect(url_for('guest.main.index'))
            else:
                # 登录失败，记录失败次数
                user.record_login_failure()
                
                # 根据失败次数显示不同的提示信息
                if user.login_attempts >= 5:
                    flash('登录失败次数过多，账户已被锁定24小时', 'error')
                else:
                    remaining_attempts = 5 - user.login_attempts
                    flash(f'邮箱或密码错误，还剩{remaining_attempts}次尝试机会', 'error')
                
        except Exception as e:
            flash(f'登录失败：{str(e)}', 'error')
    
    return render_template('auth/login.html')

@auth_profile.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('guest.main.index'))

@auth_profile.route('/profile')
@login_required
@member_only
def profile():
    """用户资料页面"""
    # 模拟统计数据（实际项目中应该从数据库查询）
    stats = {
        'total_orders': 0,
        'completed_orders': 0,
        'pending_orders': 0,
        'total_spent': 0
    }
    
    # 模拟最近活动（实际项目中应该从数据库查询）
    recent_activities = [
        {
            'title': '登录系统',
            'time': '刚刚',
            'icon': 'sign-in-alt'
        },
        {
            'title': '查看个人资料',
            'time': '1小时前',
            'icon': 'user'
        },
        {
            'title': '更新联系方式',
            'time': '2天前',
            'icon': 'phone'
        }
    ]
    
    return render_template('auth/profile.html', 
                         user=current_user, 
                         stats=stats, 
                         recent_activities=recent_activities)

@auth_profile.route('/profile/edit', methods=['GET', 'POST'])
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
            return redirect(url_for('auth_profile.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    return render_template('auth/edit_profile.html', user=current_user)

@auth_profile.route('/change-password', methods=['GET', 'POST'])
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
            return redirect(url_for('auth_profile.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'修改密码失败：{str(e)}', 'error')
    
    return render_template('auth/change_password.html')

# API 路由
@auth_profile.route('/api/check-email')
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

# 分角色的登录和注册路由
@auth_profile.route('/member/login', methods=['GET', 'POST'])
@guest_only
def member_login():
    """会员登录"""
    if request.method == 'POST':
        return _handle_role_login('member', 'auth/member_login.html')
    
    return render_template('auth/member_login.html', role_type='member')

@auth_profile.route('/member/register', methods=['GET', 'POST'])
@guest_only
def member_register():
    """会员注册 - 第一步：发送验证码"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        # 基础验证
        if not email:
            flash('请输入邮箱地址', 'error')
            return render_template('auth/member_register_step1.html', role_type='member')
        
        # 邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('请输入有效的邮箱地址', 'error')
            return render_template('auth/member_register_step1.html', role_type='member')
        
        # 检查邮箱是否已存在
        existing_user = AuthUser.query.filter_by(email=email).first()
        if existing_user:
            flash('该邮箱已被注册', 'error')
            return render_template('auth/member_register_step1.html', role_type='member')
        
        # 生成并发送验证码
        try:
            from ...auth.models.auth import EmailVerificationCode
            verification_code_obj, verification_code = EmailVerificationCode.generate_code(email)
            db.session.add(verification_code_obj)
            db.session.commit()
            
            # 发送验证码邮件
            send_verification_code_email(email, verification_code)
            
            # 将邮箱存储到session中
            session['registration_email'] = email
            flash('验证码已发送到您的邮箱，请查收', 'success')
            return redirect(url_for('auth_profile.member_register_verify'))
            
        except Exception as e:
            flash(f'发送验证码失败：{str(e)}', 'error')
            return render_template('auth/member_register_step1.html', role_type='member')
    
    return render_template('auth/member_register_step1.html', role_type='member')

@auth_profile.route('/member/register/verify', methods=['GET', 'POST'])
@guest_only
def member_register_verify():
    """会员注册 - 第二步：验证码确认和完成注册"""
    # 检查是否有注册邮箱在session中
    if 'registration_email' not in session:
        flash('请先输入邮箱地址', 'error')
        return redirect(url_for('auth_profile.member_register'))
    
    email = session['registration_email']
    
    if request.method == 'POST':
        verification_code = request.form.get('verification_code', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # 基础验证
        if not all([verification_code, password, confirm_password, first_name]):
            flash('请填写所有必填字段', 'error')
            return render_template('auth/member_register_verify.html', email=email)
        
        # 验证验证码
        try:
            from ...auth.models.auth import EmailVerificationCode
            is_valid, message = EmailVerificationCode.verify_code(email, verification_code)
            if not is_valid:
                flash(f'验证码{message}，请重新输入', 'error')
                return render_template('auth/member_register_verify.html', email=email)
        except Exception as e:
            flash(f'验证码验证失败：{str(e)}', 'error')
            return render_template('auth/member_register_verify.html', email=email)
        
        # 密码验证
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('auth/member_register_verify.html', email=email)
        
        if len(password) < 6:
            flash('密码长度至少6位', 'error')
            return render_template('auth/member_register_verify.html', email=email)
        
        # 创建用户账户
        try:
            # 获取会员角色
            member_role = Role.query.filter_by(name='member').first()
            if not member_role:
                flash('系统错误：会员角色不存在', 'error')
                return render_template('auth/member_register_verify.html', email=email)
            
            # 创建用户名
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while AuthUser.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            # 创建用户
            new_user = AuthUser(
                username=username,
                email=email,
                role_id=member_role.id,
                is_verified=True,  # 邮箱已验证
                is_active=True     # 直接激活
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
            
            # 清除session中的注册邮箱
            session.pop('registration_email', None)
            
            flash('注册成功！您的账户已激活，现在可以登录了。', 'success')
            return redirect(url_for('auth_profile.member_login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败：{str(e)}', 'error')
            return render_template('auth/member_register_verify.html', email=email)
    
    return render_template('auth/member_register_verify.html', email=email)

@auth_profile.route('/member/register/resend-code', methods=['POST'])
@guest_only
def resend_verification_code():
    """重新发送验证码"""
    # 检查是否有注册邮箱在session中
    if 'registration_email' not in session:
        flash('请先输入邮箱地址', 'error')
        return redirect(url_for('auth_profile.member_register'))
    
    email = session['registration_email']
    
    try:
        from ...auth.models.auth import EmailVerificationCode
        verification_code_obj, verification_code = EmailVerificationCode.generate_code(email)
        db.session.add(verification_code_obj)
        db.session.commit()
        
        # 发送验证码邮件
        if send_verification_code_email(email, verification_code):
            flash('验证码已重新发送，请查收邮箱', 'success')
        else:
            flash('验证码发送失败，请稍后重试', 'error')
        
        return redirect(url_for('auth_profile.member_register_verify'))
        
    except Exception as e:
        flash(f'重新发送验证码失败：{str(e)}', 'error')
        return redirect(url_for('auth_profile.member_register_verify'))

@auth_profile.route('/staff/login', methods=['GET', 'POST'])
@guest_only
def staff_login():
    """员工登录"""
    if request.method == 'POST':
        return _handle_role_login('staff', 'auth/staff_login.html')
    
    return render_template('auth/staff_login.html', role_type='staff')

@auth_profile.route('/staff/register', methods=['GET', 'POST'])
@guest_only
def staff_register():
    """员工注册（管理员邀请）"""
    if request.method == 'POST':
        return _handle_role_register('staff', 'auth/staff_register.html')
    
    return render_template('auth/staff_register.html', role_type='staff')

@auth_profile.route('/admin/login', methods=['GET', 'POST'])
@guest_only
def admin_login():
    """管理员登录"""
    if request.method == 'POST':
        return _handle_role_login('admin', 'auth/admin_login.html')
    
    return render_template('auth/admin_login.html', role_type='admin')

@auth_profile.route('/admin/register', methods=['GET', 'POST'])
@guest_only
def admin_register():
    """管理员注册（超级管理员邀请）"""
    if request.method == 'POST':
        return _handle_role_register('admin', 'auth/admin_register.html')
    
    return render_template('auth/admin_register.html', role_type='admin')

# ==================== 忘记密码功能 ====================

@auth_profile.route('/forgot-password', methods=['GET', 'POST'])
@guest_only
def forgot_password():
    """忘记密码页面"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('请输入邮箱地址', 'error')
            return render_template('auth/forgot_password.html')
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('请输入有效的邮箱地址', 'error')
            return render_template('auth/forgot_password.html')
        
        # 查找用户
        user = AuthUser.query.filter_by(email=email).first()
        
        # 无论用户是否存在，都显示相同的消息（防止邮箱枚举攻击）
        if user:
            try:
                print(f"[忘记密码] 找到用户: {user.username} ({email})")
                
                # 生成重置令牌
                reset_token, raw_token = PasswordResetToken.generate_token(user.id, email)
                db.session.add(reset_token)
                db.session.commit()
                print(f"[忘记密码] 重置令牌已生成并保存")
                
                # 发送重置邮件
                from App_new.utils.email_service import send_password_reset_email
                reset_url = url_for('auth_profile.reset_password', token=raw_token, _external=True)
                print(f"[忘记密码] 重置链接: {reset_url}")
                
                try:
                    send_password_reset_email(email, user.username, reset_url)
                    print(f"[忘记密码] 邮件发送成功!")
                except Exception as e:
                    import traceback
                    print(f"[忘记密码] 发送邮件失败: {str(e)}")
                    print(f"[忘记密码] 详细错误: {traceback.format_exc()}")
                    # 即使邮件发送失败，也显示成功消息（安全考虑）
                
            except Exception as e:
                import traceback
                print(f"[忘记密码] 生成令牌失败: {str(e)}")
                print(f"[忘记密码] 详细错误: {traceback.format_exc()}")
                db.session.rollback()
        else:
            print(f"[忘记密码] 未找到用户: {email}")
        
        flash('如果该邮箱已注册，您将收到一封密码重置邮件，请查收。', 'success')
        return redirect(url_for('auth_profile.forgot_password'))
    
    return render_template('auth/forgot_password.html')

@auth_profile.route('/reset-password/<token>', methods=['GET', 'POST'])
@guest_only
def reset_password(token):
    """重置密码页面"""
    import hashlib
    
    # 验证令牌
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset_token, is_valid, message = PasswordResetToken.verify_token(token_hash)
    
    if not is_valid:
        flash(message, 'error')
        return redirect(url_for('auth_profile.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # 验证密码
        if not password or not confirm_password:
            flash('请输入新密码', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if len(password) < 6:
            flash('密码长度至少6位', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        try:
            # 更新用户密码
            user = reset_token.user
            user.set_password(password)
            
            # 标记令牌为已使用
            reset_token.use_token()
            
            # 解锁账户（如果被锁定）
            if user.is_locked:
                user.unlock_account()
            
            db.session.commit()
            
            flash('密码重置成功！请使用新密码登录', 'success')
            
            # 根据用户角色重定向到对应登录页
            if user.role.name == 'staff':
                return redirect(url_for('auth_profile.staff_login'))
            elif user.role.name == 'admin':
                return redirect(url_for('admin_auth.login'))
            else:
                return redirect(url_for('auth_profile.member_login'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'密码重置失败：{str(e)}', 'error')
            return render_template('auth/reset_password.html', token=token)
    
    return render_template('auth/reset_password.html', token=token, email=reset_token.email)

def _handle_role_login(role_name, template_name):
    """处理角色登录逻辑"""
    try:
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('请输入邮箱和密码', 'error')
            return render_template(template_name, role_type=role_name)
        
        # 查找用户
        user = AuthUser.query.filter_by(email=email).first()
        
        if not user:
            flash('邮箱或密码错误', 'error')
            return render_template(template_name, role_type=role_name)
        
        # 检查账户是否被锁定
        if user.is_account_locked():
            remaining_minutes = user.get_remaining_lock_time()
            if remaining_minutes > 0:
                flash(f'账户已被锁定，请{remaining_minutes}分钟后再试', 'error')
            else:
                flash('账户已被锁定，请联系管理员解锁', 'error')
            return render_template(template_name, role_type=role_name)
        
        # 检查账户是否被禁用
        if not user.is_active:
            flash('账户已被禁用，请联系管理员', 'error')
            return render_template(template_name, role_type=role_name)
        
        # 验证密码
        if user.check_password(password):
            # 验证用户角色是否匹配
            if user.role.name != role_name:
                flash(f'该账号不是{_get_role_display_name(role_name)}，请使用正确的登录入口', 'error')
                return render_template(template_name, role_type=role_name)
            
            # 对于会员，检查邮箱是否已验证
            if role_name == 'member' and not user.is_verified:
                flash('您的邮箱尚未验证，请查收邮件并点击验证链接完成邮箱验证。', 'warning')
                return redirect(url_for('auth_profile.email_verification_sent'))
            
            # 登录成功，记录成功登录并重置失败计数
            user.record_login_success()
            login_user(user, remember=remember)
            
            # 重定向到原来想访问的页面或默认页面
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # 根据用户角色重定向到不同页面
            if role_name == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role_name == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif role_name == 'member':
                return redirect(url_for('member.dashboard'))
        else:
            # 登录失败，记录失败次数
            user.record_login_failure()
            
            # 根据失败次数显示不同的提示信息
            if user.login_attempts >= 5:
                flash('登录失败次数过多，账户已被锁定24小时', 'error')
            else:
                remaining_attempts = 5 - user.login_attempts
                flash(f'邮箱或密码错误，还剩{remaining_attempts}次尝试机会', 'error')
            
    except Exception as e:
        flash(f'登录失败：{str(e)}', 'error')
    
    return render_template(template_name, role_type=role_name)

def _handle_role_register(role_name, template_name):
    """处理角色注册逻辑"""
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
            return render_template(template_name, role_type=role_name)
        
        # 邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('请输入有效的邮箱地址', 'error')
            return render_template(template_name, role_type=role_name)
        
        # 密码验证
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template(template_name, role_type=role_name)
        
        if len(password) < 6:
            flash('密码长度至少6位', 'error')
            return render_template(template_name, role_type=role_name)
        
        # 检查邮箱是否已存在
        existing_user = AuthUser.query.filter_by(email=email).first()
        if existing_user:
            flash('该邮箱已被注册', 'error')
            return render_template(template_name, role_type=role_name)
        
        # 获取角色
        target_role = Role.query.filter_by(name=role_name).first()
        if not target_role:
            flash(f'系统错误：{_get_role_display_name(role_name)}角色不存在', 'error')
            return render_template(template_name, role_type=role_name)
        
        # 对于非会员角色，添加额外验证
        if role_name in ['staff', 'admin']:
            invitation_code_str = request.form.get('invitation_code', '').strip()
            if not invitation_code_str:
                flash('请输入邀请码', 'error')
                return render_template(template_name, role_type=role_name)
            
            # 查找邀请码
            invitation_code = InvitationCode.query.filter_by(
                code=invitation_code_str,
                role_name=role_name
            ).first()
            
            if not invitation_code:
                flash('邀请码不存在或角色不匹配，请联系管理员', 'error')
                return render_template(template_name, role_type=role_name)
            
            # 验证邀请码有效性
            is_valid, message = invitation_code.is_valid()
            if not is_valid:
                flash(f'邀请码无效：{message}', 'error')
                return render_template(template_name, role_type=role_name)
        
        # 创建新用户
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while AuthUser.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        # 对于会员注册，初始状态为未验证
        is_verified = False if role_name == 'member' else True
        
        new_user = AuthUser(
            username=username,
            email=email,
            role_id=target_role.id,
            is_verified=is_verified,
            is_active=not is_verified  # 未验证的用户暂时不激活
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
        
        # 如果使用了邀请码，标记为已使用
        if role_name in ['staff', 'admin'] and 'invitation_code' in locals():
            invitation_code.use_code(new_user.id)
        
        # 对于会员注册，发送邮箱验证邮件
        if role_name == 'member':
            try:
                from ...auth.models.auth import EmailVerificationToken
                verification_token, raw_token = EmailVerificationToken.generate_token(new_user.id, email)
                db.session.add(verification_token)
                db.session.commit()
                
                # 发送验证邮件
                send_verification_email(email, raw_token, first_name)
                
                flash('注册成功！我们已向您的邮箱发送了验证链接，请查收邮件并点击链接完成邮箱验证。', 'success')
                return redirect(url_for('auth_profile.email_verification_sent'))
            except Exception as e:
                flash(f'注册成功，但验证邮件发送失败：{str(e)}。请联系客服。', 'warning')
                return redirect(url_for('auth_profile.member_login'))
        else:
            flash(f'{_get_role_display_name(role_name)}注册成功！请登录', 'success')
            if role_name == 'admin':
                return redirect(url_for('admin_auth.login'))
            else:
                return redirect(url_for(f'auth_profile.{role_name}_login'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'注册失败：{str(e)}', 'error')
        
    return render_template(template_name, role_type=role_name)

def _get_role_display_name(role_name):
    """获取角色显示名称"""
    role_names = {
        'member': '会员',
        'staff': '员工',
        'admin': '管理员'
    }
    return role_names.get(role_name, role_name)

def send_verification_code_email(email, verification_code):
    """发送邮箱验证码邮件"""
    try:
        from flask_mail import Message
        from flask import current_app
        from ...exts import mail
        
        # 检查邮件配置
        if not current_app.config.get('MAIL_SERVER'):
            print("❌ 邮件服务器未配置")
            return False
        
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            print("❌ 邮件用户名或密码未配置")
            return False
        
        print(f"📧 正在发送验证码到: {email}")
        print(f"🔧 邮件服务器: {current_app.config.get('MAIL_SERVER')}")
        print(f"👤 发件人: {current_app.config.get('MAIL_USERNAME')}")
        
        msg = Message(
            subject='悦行假期 - 邮箱验证码',
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', current_app.config.get('MAIL_USERNAME')),
            recipients=[email],
            html=f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #28a745;">悦行假期</h1>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 30px; border-radius: 10px; margin-bottom: 20px;">
                        <h2 style="color: #28a745; margin-bottom: 20px;">邮箱验证码</h2>
                        <p>您好，</p>
                        <p>您正在注册悦行假期会员账户，请使用以下验证码完成注册：</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <div style="background: linear-gradient(135deg, #28a745 0%, #34ce57 100%); color: white; padding: 20px; border-radius: 10px; display: inline-block; font-size: 32px; font-weight: bold; letter-spacing: 5px; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);">
                                {verification_code}
                            </div>
                        </div>
                        
                        <p><strong>验证码有效期为10分钟，请及时使用。</strong></p>
                        <p>如果您没有注册悦行假期账户，请忽略此邮件。</p>
                    </div>
                    
                    <div style="text-align: center; color: #666; font-size: 14px;">
                        <p>此邮件由系统自动发送，请勿回复。</p>
                        <p>如有疑问，请联系客服：info@joyesc.com</p>
                    </div>
                </div>
            </body>
            </html>
            """
        )
        
        mail.send(msg)
        print(f"✅ 验证码邮件发送成功: {email}")
        return True
        
    except Exception as e:
        print(f"❌ 发送验证码邮件失败: {str(e)}")
        print(f"🔍 错误详情: {type(e).__name__}")
        return False

def send_verification_email(email, token, first_name):
    """发送邮箱验证邮件"""
    try:
        from flask_mail import Message
        from ...exts import mail
        
        verification_url = url_for('auth_profile.verify_email', token=token, _external=True)
        
        msg = Message(
            subject='MyTravelPanel - 邮箱验证',
            recipients=[email],
            html=f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #007bff;">MyTravelPanel</h1>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 30px; border-radius: 10px; margin-bottom: 20px;">
                        <h2 style="color: #007bff; margin-bottom: 20px;">欢迎加入MyTravelPanel！</h2>
                        <p>亲爱的 {first_name}，</p>
                        <p>感谢您注册MyTravelPanel会员账户。为了确保账户安全，请点击下面的按钮验证您的邮箱地址：</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{verification_url}" 
                               style="background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                               验证邮箱地址
                            </a>
                        </div>
                        
                        <p>如果按钮无法点击，请复制以下链接到浏览器中打开：</p>
                        <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px; font-family: monospace;">
                            {verification_url}
                        </p>
                        
                        <p><strong>注意：</strong>此验证链接将在24小时后失效。</p>
                    </div>
                    
                    <div style="text-align: center; color: #666; font-size: 14px;">
                        <p>此邮件由系统自动发送，请勿回复。</p>
                        <p>如有疑问，请联系客服：support@mytravelpanel.com</p>
                    </div>
                </div>
            </body>
            </html>
            """
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"发送验证邮件失败: {str(e)}")
        return False

@auth_profile.route('/email-verification-sent')
def email_verification_sent():
    """邮箱验证邮件发送成功页面"""
    return render_template('auth/email_verification_sent.html')

@auth_profile.route('/verify-email/<token>')
def verify_email(token):
    """邮箱验证处理"""
    try:
        from ...auth.models.auth import EmailVerificationToken
        import hashlib
        
        # 将原始token转换为hash
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # 查找验证令牌
        verification_token = EmailVerificationToken.query.filter_by(token=token_hash).first()
        
        if not verification_token:
            flash('验证链接无效或已过期', 'error')
            return redirect(url_for('auth_profile.member_login'))
        
        if not verification_token.is_valid():
            flash('验证链接已过期，请重新注册', 'error')
            return redirect(url_for('auth_profile.member_register'))
        
        # 验证成功，激活用户账户
        user = verification_token.user
        user.is_verified = True
        user.is_active = True
        
        # 标记令牌为已使用
        verification_token.use_token()
        
        db.session.commit()
        
        flash('邮箱验证成功！您的账户已激活，现在可以登录了。', 'success')
        return redirect(url_for('auth_profile.member_login'))
        
    except Exception as e:
        flash(f'邮箱验证失败：{str(e)}', 'error')
        return redirect(url_for('auth_profile.member_login'))

@auth_profile.route('/resend-verification', methods=['POST'])
def resend_verification():
    """重新发送验证邮件"""
    try:
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('请输入邮箱地址', 'error')
            return redirect(url_for('auth_profile.email_verification_sent'))
        
        # 查找用户
        user = AuthUser.query.filter_by(email=email).first()
        if not user:
            flash('该邮箱未注册', 'error')
            return redirect(url_for('auth_profile.email_verification_sent'))
        
        if user.is_verified:
            flash('该邮箱已验证，无需重复验证', 'info')
            return redirect(url_for('auth_profile.member_login'))
        
        # 生成新的验证令牌
        from ...auth.models.auth import EmailVerificationToken
        verification_token, raw_token = EmailVerificationToken.generate_token(user.id, email)
        db.session.add(verification_token)
        db.session.commit()
        
        # 发送验证邮件
        if send_verification_email(email, raw_token, user.profile.first_name if user.profile else '用户'):
            flash('验证邮件已重新发送，请查收邮箱', 'success')
        else:
            flash('验证邮件发送失败，请联系客服', 'error')
        
        return redirect(url_for('auth_profile.email_verification_sent'))
        
    except Exception as e:
        flash(f'重新发送验证邮件失败：{str(e)}', 'error')
        return redirect(url_for('auth_profile.email_verification_sent')) 