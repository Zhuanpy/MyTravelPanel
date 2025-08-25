"""
管理员功能路由
管理员仪表板、用户管理、权限管理、系统配置等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from App_new.utils.decorators import admin_only, permission_required
from App_new.auth.models.auth import AuthUser, Role, UserProfile, InvitationCode
from App_new.utils.permissions import get_all_permissions, get_all_roles, ROLE_PERMISSIONS
from App_new.exts import db
from datetime import datetime, timedelta
from sqlalchemy import func
import json

# 创建管理员蓝图
admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/dashboard')
@login_required
@admin_only
def dashboard():
    """管理员仪表板"""
    try:
        # 获取系统统计信息
        stats = {
            'total_users': AuthUser.query.count(),
            'total_roles': Role.query.count(),
            'active_users': AuthUser.query.filter_by(is_active=True).count() if hasattr(AuthUser, 'is_active') else AuthUser.query.count(),
            'new_users_this_month': get_new_users_count(),
        }
        
        # 获取最近注册的用户
        recent_users = AuthUser.query.order_by(AuthUser.created_at.desc()).limit(5).all() if hasattr(AuthUser, 'created_at') else []
        
        # 获取系统活动
        recent_activities = get_recent_activities()
        
        return render_template('admin/dashboard.html', 
                             stats=stats,
                             recent_users=recent_users,
                             recent_activities=recent_activities,
                             now=datetime.now())
    except Exception as e:
        flash(f'加载仪表板失败：{str(e)}', 'error')
        return render_template('admin/dashboard.html',
                             stats={}, recent_users=[], recent_activities=[],
                             now=datetime.now())

@admin.route('/users')
@login_required
@admin_only
def users():
    """用户管理"""
    try:
        # 获取所有用户
        all_users = AuthUser.query.order_by(AuthUser.created_at.desc()).all()
        
        # 统计各角色用户数量
        admin_count = AuthUser.query.join(Role).filter(Role.name == 'admin').count()
        staff_count = AuthUser.query.join(Role).filter(Role.name == 'staff').count()
        member_count = AuthUser.query.join(Role).filter(Role.name == 'member').count()
        total_count = AuthUser.query.count()
        
        return render_template('admin/users.html',
                             users=all_users,
                             admin_count=admin_count,
                             staff_count=staff_count,
                             member_count=member_count,
                             total_count=total_count)
    except Exception as e:
        flash(f'加载用户列表失败：{str(e)}', 'error')
        return render_template('admin/users.html',
                             users=[],
                             admin_count=0,
                             staff_count=0,
                             member_count=0,
                             total_count=0)

@admin.route('/user/<int:user_id>')
@login_required
@admin_only
def user_detail(user_id):
    """用户详情"""
    try:
        user = AuthUser.query.get_or_404(user_id)
        
        # 获取用户统计信息（模拟数据）
        user_stats = {
            'login_count': 0,
            'last_login': None,
            'projects_count': 0,
            'orders_count': 0
        }
        
        return render_template('admin/user_detail.html',
                             user=user,
                             user_stats=user_stats)
    except Exception as e:
        flash(f'加载用户详情失败：{str(e)}', 'error')
        return redirect(url_for('admin.users'))

@admin.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_only
def edit_user(user_id):
    """编辑用户"""
    try:
        user = AuthUser.query.get_or_404(user_id)
        
        if request.method == 'POST':
            # 获取表单数据
            role_id = request.form.get('role_id', type=int)
            is_active = request.form.get('is_active') == 'on'
            
            # 更新用户信息
            if role_id:
                role = Role.query.get(role_id)
                if role:
                    user.role_id = role_id
                    user.role = role
            
            # 如果用户模型有is_active字段，更新它
            if hasattr(user, 'is_active'):
                user.is_active = is_active
            
            # 更新用户资料
            if user.profile:
                user.profile.first_name = request.form.get('first_name', '').strip()
                user.profile.last_name = request.form.get('last_name', '').strip()
                user.profile.phone = request.form.get('phone', '').strip()
                user.profile.address = request.form.get('address', '').strip()
            
            db.session.commit()
            flash('用户信息更新成功', 'success')
            return redirect(url_for('admin.user_detail', user_id=user_id))
        
        # 获取所有角色
        roles = Role.query.all()
        
        return render_template('admin/edit_user.html',
                             user=user,
                             roles=roles)
    except Exception as e:
        db.session.rollback()
        flash(f'编辑用户失败：{str(e)}', 'error')
        return redirect(url_for('admin.users'))

@admin.route('/roles')
@login_required
@admin_only
def roles():
    """角色管理"""
    try:
        roles = Role.query.all()
        
        # 为每个角色获取用户数量
        role_stats = {}
        for role in roles:
            role_stats[role.id] = AuthUser.query.filter_by(role_id=role.id).count()
        
        return render_template('admin/roles.html',
                             roles=roles,
                             role_stats=role_stats,
                             role_permissions=ROLE_PERMISSIONS)
    except Exception as e:
        flash(f'加载角色列表失败：{str(e)}', 'error')
        return render_template('admin/roles.html',
                             roles=[], role_stats={}, role_permissions={})

@admin.route('/role/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_only
def edit_role(role_id):
    """编辑角色"""
    try:
        role = Role.query.get_or_404(role_id)
        
        if request.method == 'POST':
            # 获取表单数据
            role.description = request.form.get('description', '').strip()
            
            # 获取权限列表
            permissions = request.form.getlist('permissions')
            role.permissions = permissions
            
            db.session.commit()
            flash('角色权限更新成功', 'success')
            return redirect(url_for('admin.roles'))
        
        # 获取所有可用权限
        all_permissions = get_all_permissions()
        current_permissions = role.permissions or []
        
        return render_template('admin/edit_role.html',
                             role=role,
                             all_permissions=all_permissions,
                             current_permissions=current_permissions)
    except Exception as e:
        db.session.rollback()
        flash(f'编辑角色失败：{str(e)}', 'error')
        return redirect(url_for('admin.roles'))

@admin.route('/system')
@login_required
@admin_only
def system():
    """系统配置"""
    try:
        # 获取系统信息
        system_info = {
            'app_name': 'MyTravelPanel',
            'version': '1.0.0',
            'database_users': AuthUser.query.count(),
            'database_roles': Role.query.count(),
            'python_version': get_python_version(),
            'flask_version': get_flask_version(),
        }
        
        return render_template('admin/system.html',
                             system_info=system_info)
    except Exception as e:
        flash(f'加载系统配置失败：{str(e)}', 'error')
        return render_template('admin/system.html',
                             system_info={})

@admin.route('/analytics')
@login_required
@admin_only
def analytics():
    """数据分析"""
    try:
        # 获取分析数据
        analytics_data = {
            'user_growth': get_user_growth_data(),
            'role_distribution': get_role_distribution(),
            'activity_stats': get_activity_stats(),
        }
        
        return render_template('admin/analytics.html',
                             analytics_data=analytics_data)
    except Exception as e:
        flash(f'加载数据分析失败：{str(e)}', 'error')
        return render_template('admin/analytics.html',
                             analytics_data={})

@admin.route('/create-user', methods=['GET', 'POST'])
@login_required
@admin_only
def create_user():
    """管理员创建用户"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            role_name = request.form.get('role', '')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            
            # 基础验证
            if not all([email, password, role_name, first_name]):
                flash('请填写所有必填字段', 'error')
                return render_template('admin/create_user.html', roles=get_all_roles())
            
            # 只允许创建员工和管理员（会员通过公开注册）
            if role_name not in ['staff', 'admin']:
                flash('只能创建员工或管理员账户，会员请通过公开注册', 'error')
                return render_template('admin/create_user.html', roles=get_all_roles())
            
            # 邮箱格式验证
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                flash('请输入有效的邮箱地址', 'error')
                return render_template('admin/create_user.html', roles=get_all_roles())
            
            # 密码长度验证
            if len(password) < 6:
                flash('密码长度至少6位', 'error')
                return render_template('admin/create_user.html', roles=get_all_roles())
            
            # 检查邮箱是否已存在
            existing_user = AuthUser.query.filter_by(email=email).first()
            if existing_user:
                flash('该邮箱已被注册', 'error')
                return render_template('admin/create_user.html', roles=get_all_roles())
            
            # 获取角色
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                flash(f'角色 {role_name} 不存在', 'error')
                return render_template('admin/create_user.html', roles=get_all_roles())
            
            # 创建新用户
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while AuthUser.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            new_user = AuthUser(
                username=username,
                email=email,
                role_id=role.id
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
            
            flash(f'成功创建{role.description}账户：{email}', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建用户失败：{str(e)}', 'error')
            return render_template('admin/create_user.html', roles=get_all_roles())
    
    # GET请求，显示创建用户表单
    return render_template('admin/create_user.html', roles=get_all_roles())

@admin.route('/invitation-codes')
@login_required
@admin_only
def invitation_codes():
    """邀请码管理页面"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    codes = InvitationCode.query.order_by(InvitationCode.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/invitation_codes.html', codes=codes, now=datetime.utcnow())

@admin.route('/invitation-codes/create', methods=['GET', 'POST'])
@login_required
@admin_only
def create_invitation_code():
    """创建邀请码"""
    if request.method == 'POST':
        try:
            role_name = request.form.get('role_name', '').strip()
            expires_days = request.form.get('expires_days', type=int)
            count = request.form.get('count', 1, type=int)
            
            if role_name not in ['staff', 'admin']:
                flash('角色类型无效', 'error')
                return render_template('admin/create_invitation_code.html')
            
            if count < 1 or count > 10:
                flash('一次最多生成10个邀请码', 'error')
                return render_template('admin/create_invitation_code.html')
            
            # 计算过期时间
            expires_at = None
            if expires_days and expires_days > 0:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)
            
            # 批量创建邀请码
            created_codes = []
            for _ in range(count):
                code = InvitationCode(
                    code=InvitationCode.generate_code(),
                    role_name=role_name,
                    created_by=current_user.id,
                    expires_at=expires_at
                )
                db.session.add(code)
                created_codes.append(code.code)
            
            db.session.commit()
            
            flash(f'成功创建 {count} 个{_get_role_display_name(role_name)}邀请码', 'success')
            
            # 如果只创建了一个，显示邀请码
            if count == 1:
                flash(f'邀请码：{created_codes[0]}', 'info')
            
            return redirect(url_for('admin.invitation_codes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建邀请码失败：{str(e)}', 'error')
    
    return render_template('admin/create_invitation_code.html')

@admin.route('/invitation-codes/<int:code_id>/revoke', methods=['POST'])
@login_required
@admin_only
def revoke_invitation_code(code_id):
    """撤销邀请码"""
    try:
        code = InvitationCode.query.get_or_404(code_id)
        
        if code.is_used:
            flash('邀请码已被使用，无法撤销', 'error')
        else:
            code.is_used = True
            code.used_at = datetime.utcnow()
            db.session.commit()
            flash('邀请码已撤销', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'撤销邀请码失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.invitation_codes'))

# 工具函数
def get_new_users_count():
    """获取本月新用户数量"""
    try:
        if hasattr(AuthUser, 'created_at'):
            first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return AuthUser.query.filter(AuthUser.created_at >= first_day).count()
        return 0
    except:
        return 0

def get_recent_activities():
    """获取最近系统活动"""
    activities = [
        {
            'type': 'user_register',
            'title': '系统初始化完成',
            'description': '管理员账户已创建，系统准备就绪',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'icon': 'fa-check-circle',
            'color': 'success'
        }
    ]
    return activities

def get_python_version():
    """获取Python版本"""
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

def get_flask_version():
    """获取Flask版本"""
    try:
        import flask
        return flask.__version__
    except:
        return "未知"

def get_user_growth_data():
    """获取用户增长数据"""
    # 模拟数据
    return {
        'labels': ['1月', '2月', '3月', '4月', '5月', '6月'],
        'data': [1, 1, 1, 1, 1, AuthUser.query.count()]
    }

def get_role_distribution():
    """获取角色分布数据"""
    try:
        roles = Role.query.all()
        distribution = {}
        for role in roles:
            count = AuthUser.query.filter_by(role_id=role.id).count()
            distribution[role.name] = count
        return distribution
    except:
        return {}

def get_activity_stats():
    """获取活动统计"""
    return {
        'total_logins': 0,
        'active_sessions': 1,  # 当前管理员
        'system_uptime': '运行中'
    }

def get_all_roles():
    """获取所有角色（仅用于管理员创建用户）"""
    return Role.query.filter(Role.name.in_(['staff', 'admin'])).all()

def _get_role_display_name(role_name):
    """获取角色显示名称"""
    role_names = {
        'member': '会员',
        'staff': '员工',
        'admin': '管理员'
    }
    return role_names.get(role_name, role_name)

# API 路由
@admin.route('/api/stats')
@login_required
@admin_only
def api_stats():
    """获取管理员统计数据"""
    try:
        stats = {
            'total_users': AuthUser.query.count(),
            'total_roles': Role.query.count(),
            'active_users': AuthUser.query.count(),  # 简化版本
            'new_users_today': 0,
            'system_health': 'excellent'
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin.route('/api/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_only
def api_toggle_user_status(user_id):
    """切换用户状态"""
    try:
        user = AuthUser.query.get_or_404(user_id)
        
        # 如果用户模型有is_active字段
        if hasattr(user, 'is_active'):
            user.is_active = not user.is_active
            db.session.commit()
            
            status = '激活' if user.is_active else '禁用'
            return jsonify({
                'success': True,
                'message': f'用户已{status}',
                'is_active': user.is_active
            })
        else:
            return jsonify({
                'success': False,
                'message': '用户状态切换功能未实现'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin.route('/api/user/<int:user_id>/delete', methods=['DELETE'])
@login_required
@admin_only
def api_delete_user(user_id):
    """删除用户"""
    try:
        user = AuthUser.query.get_or_404(user_id)
        
        # 不能删除自己
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'message': '不能删除自己的账户'
            }), 400
        
        # 不能删除管理员（除非当前用户是超级管理员）
        if user.role and user.role.name == 'admin':
            return jsonify({
                'success': False,
                'message': '不能删除管理员账户'
            }), 400
        
        # 删除用户资料（如果存在）
        if user.profile:
            db.session.delete(user.profile)
        
        # 删除用户
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户已删除'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin.route('/api/system/info')
@login_required
@admin_only
def api_system_info():
    """获取系统信息"""
    try:
        import psutil
        import platform
        
        system_info = {
            'platform': platform.system(),
            'python_version': get_python_version(),
            'flask_version': get_flask_version(),
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:').percent
        }
        
        return jsonify({
            'success': True,
            'data': system_info
        })
    except ImportError:
        # 如果psutil未安装，返回基础信息
        return jsonify({
            'success': True,
            'data': {
                'python_version': get_python_version(),
                'flask_version': get_flask_version(),
                'status': '运行中'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500 

@admin.route('/users/locked')
@admin_only
def locked_users():
    """查看被锁定的用户列表"""
    try:
        from App.models.auth import AuthUser
        
        # 获取所有被锁定的用户
        locked_users = AuthUser.query.filter_by(is_locked=True).all()
        
        return render_template('admin/locked_users.html', users=locked_users)
    except Exception as e:
        flash(f'获取锁定用户列表失败：{str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin.route('/users/<int:user_id>/unlock', methods=['POST'])
@admin_only
def unlock_user(user_id):
    """解锁被锁定的用户"""
    try:
        from App.models.auth import AuthUser
        
        user = AuthUser.query.get_or_404(user_id)
        
        if not user.is_locked:
            flash('该用户账户未被锁定', 'info')
        else:
            user.unlock_account()
            flash(f'用户 {user.username} 的账户已成功解锁', 'success')
        
        return redirect(url_for('admin.locked_users'))
    except Exception as e:
        flash(f'解锁用户失败：{str(e)}', 'error')
        return redirect(url_for('admin.locked_users'))

@admin.route('/users/<int:user_id>/reset-attempts', methods=['POST'])
@admin_only
def reset_user_attempts(user_id):
    """重置用户的登录失败次数"""
    try:
        from App.models.auth import AuthUser
        
        user = AuthUser.query.get_or_404(user_id)
        
        user.login_attempts = 0
        db.session.commit()
        
        flash(f'用户 {user.username} 的登录失败次数已重置', 'success')
        return redirect(url_for('admin.locked_users'))
    except Exception as e:
        flash(f'重置失败次数失败：{str(e)}', 'error')
        return redirect(url_for('admin.locked_users')) 