# -*- coding: utf-8 -*-
"""
员工模块路由 - 完整版本
包含所有员工功能模块
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from ...utils.decorators import staff_only
from werkzeug.utils import secure_filename
import json
import os

# 创建员工蓝图
# 注意：此文件位于 App_new/staff/routes/ 下，而模板位于 App_new/staff/templates/
# 这里将模板目录指向上一层的 templates，模板渲染统一使用命名空间路径 'staff/xxx.html'
staff = Blueprint('staff', __name__, url_prefix='/staff', template_folder='../templates')

# ==================== 辅助函数 ====================
def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# ==================== 个人资料 ====================
@staff.route('/profile')
@login_required
@staff_only
def profile():
    """员工个人资料页面"""
    return render_template('staff/profile.html', user=current_user)

@staff.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_profile():
    """编辑员工个人资料"""
    from ...auth.models.auth import UserProfile
    from ...exts import db
    
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            company = request.form.get('company', '').strip().upper()
            position = request.form.get('position', '').strip()
            address = request.form.get('address', '').strip()
            
            if not first_name:
                flash('姓名不能为空', 'error')
                return render_template('staff/edit_profile.html', user=current_user)
            
            # 更新用户资料
            if current_user.profile:
                current_user.profile.first_name = first_name
                current_user.profile.last_name = last_name
                current_user.profile.phone = phone
                current_user.profile.company = company
                current_user.profile.position = position
                current_user.profile.address = address
            else:
                # 如果用户没有资料，创建新的
                profile = UserProfile(
                    user_id=current_user.id,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    company=company,
                    position=position,
                    address=address
                )
                db.session.add(profile)
            
            db.session.commit()
            flash('资料更新成功', 'success')
            return redirect(url_for('staff.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    return render_template('staff/edit_profile.html', user=current_user)

@staff.route('/change-password', methods=['GET', 'POST'])
@login_required
@staff_only
def change_password():
    """员工修改密码"""
    from ...exts import db
    
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not all([current_password, new_password, confirm_password]):
                flash('请填写所有字段', 'error')
                return render_template('staff/change_password.html')
            
            # 验证当前密码
            if not current_user.check_password(current_password):
                flash('当前密码错误', 'error')
                return render_template('staff/change_password.html')
            
            # 验证新密码
            if new_password != confirm_password:
                flash('两次输入的新密码不一致', 'error')
                return render_template('staff/change_password.html')
            
            if len(new_password) < 6:
                flash('新密码长度至少6位', 'error')
                return render_template('staff/change_password.html')
            
            # 更新密码
            current_user.set_password(new_password)
            db.session.commit()
            
            flash('密码修改成功', 'success')
            return redirect(url_for('staff.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'修改密码失败：{str(e)}', 'error')
    
    return render_template('staff/change_password.html')

# ==================== 仪表板 ====================
@staff.route('/dashboard')
@login_required
@staff_only
def dashboard():
    """员工仪表板 - 实现真实数据查询"""
    try:
        # 导入必要的模型
        from ...business.projects.models.project import ProjectHeader, CustomerCompany
        from ...business.projects.models.ref import ProjectRef
        from ...exts import db
        
        # 构建基础查询
        base_query = ProjectHeader.query
        
        # 根据员工等级过滤项目
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己创建的项目
                base_query = base_query.filter(ProjectHeader.staff_name == current_user.username)
            # 2级员工可以看到所有项目，不需要额外过滤
        
        # 获取员工统计信息（真实数据）
        total_projects = base_query.count()
        active_projects = base_query.filter_by(status='active').count()
        
        # 计算本月完成的项目
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        completed_this_month = base_query.filter(
            ProjectHeader.status == 'completed',
            ProjectHeader.updated_at >= current_month_start
        ).count()
        
        # 计算待处理报价（状态为draft的项目）
        pending_quotes = base_query.filter_by(status='draft').count()
        
        stats = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'pending_quotes': pending_quotes,
            'completed_this_month': completed_this_month,
        }
        
        # 获取最近的项目列表（真实数据，最近10个）
        recent_projects_query = base_query.order_by(ProjectHeader.created_at.desc()).limit(10)
        recent_projects = []
        
        for project in recent_projects_query:
            # 计算项目财务数据
            refs = ProjectRef.query.filter_by(header_id=project.id).all()
            total_selling_price = sum([float(ref.selling_price or 0) for ref in refs])
            total_cost_price = sum([float(ref.cost_price or 0) for ref in refs])
            total_profit = total_selling_price - total_cost_price
            
            # 获取客户公司名称
            client_name = '未指定客户'
            if project.company_id and project.company:
                client_name = project.company.company_name
            
            # 构建项目数据
            project_data = {
                'id': project.id,
                'hid': project.hid,
                'name': project.desc or f'项目 {project.hid}',
                'client': client_name,
                'leader': project.leader_name or '未指定负责人',
                'contact': project.contact or '未指定联系人',
                'status': project.status,
                'type': project.type or '综合',
                'created_at': project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else '',
                'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M') if project.updated_at else '',
                'total_selling': total_selling_price,
                'total_cost': total_cost_price,
                'total_profit': total_profit,
                'ref_count': len(refs)
            }
            recent_projects.append(project_data)
        
        # 获取待处理任务（状态为draft的项目）
        pending_tasks = []
        draft_projects = base_query.filter_by(status='draft').limit(5).all()
        
        for project in draft_projects:
            task_data = {
                'id': project.id,
                'hid': project.hid,
                'name': project.desc or f'项目 {project.hid}',
                'type': '项目创建',
                'priority': 'medium',
                'due_date': project.created_at + timedelta(days=7) if project.created_at else None
            }
            pending_tasks.append(task_data)
        
        # 渲染仪表板模板，传递真实数据
        return render_template('staff/staff_dashboard.html', 
                             stats=stats,
                             recent_projects=recent_projects,
                             pending_tasks=pending_tasks)
                             
    except Exception as e:
        # 错误处理：记录错误并显示友好的错误信息
        current_app.logger.error(f'加载员工仪表板失败: {str(e)}')
        flash(f'加载仪表板失败：{str(e)}', 'error')
        
        # 返回空的仪表板，避免页面崩溃
        return render_template('staff/staff_dashboard.html',
                             stats={
                                 'total_projects': 0,
                                 'active_projects': 0,
                                 'pending_quotes': 0,
                                 'completed_this_month': 0
                             }, 
                             recent_projects=[], 
                             pending_tasks=[])

# ==================== 项目管理功能已移至 projects.py ====================

# ==================== 报价管理 ====================
@staff.route('/quotes')
@login_required
@staff_only
def quotes():
    """报价列表"""
    try:
        # 获取筛选参数
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 模拟报价数据
        all_quotes = [
            {
                'id': 1,
                'quote_no': 'QT240001',
                'client': 'ABC公司',
                'project_name': '新加坡商务团队签证',
                'status': 'pending',
                'total_amount': 5000.00,
                'created_at': datetime(2024, 1, 15, 10, 30),
                'valid_until': datetime(2024, 1, 25, 10, 30)
            },
            {
                'id': 2,
                'quote_no': 'QT240002',
                'client': 'XYZ旅行社',
                'project_name': '泰国旅游团队套餐',
                'status': 'approved',
                'total_amount': 12000.00,
                'created_at': datetime(2024, 1, 16, 9, 15),
                'valid_until': datetime(2024, 1, 26, 9, 15)
            }
        ]
        
        # 应用筛选
        filtered_quotes = all_quotes
        
        if status:
            filtered_quotes = [q for q in filtered_quotes if q['status'] == status]
        if search:
            search_lower = search.lower()
            filtered_quotes = [q for q in filtered_quotes 
                               if search_lower in q['client'].lower() 
                               or search_lower in q['project_name'].lower()]
        
        # 分页
        total = len(filtered_quotes)
        start = (page - 1) * per_page
        end = start + per_page
        quotes_page = filtered_quotes[start:end]
        
        return render_template('staff/staff_quotes.html',
                             quotes=quotes_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             status=status,
                             search=search,
                             now=datetime.now())
    except Exception as e:
        flash(f'加载报价列表失败：{str(e)}', 'error')
        return render_template('staff/staff_quotes.html',
                             quotes=[],
                             current_page=1,
                             total_pages=1,
                             total=0,
                             status='',
                             search='',
                             now=datetime.now())

@staff.route('/create_quote', methods=['GET', 'POST'])
@login_required
@staff_only
def create_quote():
    """创建报价"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            quote_data = {
                'client': request.form.get('client'),
                'project_name': request.form.get('project_name'),
                'description': request.form.get('description'),
                'items': request.form.getlist('items[]'),
                'quantities': request.form.getlist('quantities[]'),
                'unit_prices': request.form.getlist('unit_prices[]'),
                'valid_days': int(request.form.get('valid_days', 30))
            }
            
            # 生成报价编号
            quote_no = 'QT240999'  # 模拟编号
            
            flash('报价创建成功！', 'success')
            return redirect(url_for('staff.quotes'))
            
        except Exception as e:
            flash(f'创建报价失败：{str(e)}', 'error')
    
    return render_template('staff/create_quote.html')

# ==================== 文件管理 ====================
@staff.route('/files')
@login_required
@staff_only
def files():
    """文件列表"""
    try:
        # 获取筛选参数
        file_type = request.args.get('type', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 获取实际上传的文件
        upload_folder = current_app.config['UPLOAD_FOLDER']
        all_files = []
        
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, filename)
                if os.path.isfile(file_path):
                    # 获取文件信息
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    
                    # 确定文件类型
                    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                    if file_ext in ['pdf']:
                        file_type_display = 'pdf'
                    elif file_ext in ['doc', 'docx']:
                        file_type_display = 'document'
                    elif file_ext in ['xls', 'xlsx']:
                        file_type_display = 'excel'
                    elif file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                        file_type_display = 'image'
                    elif file_ext in ['zip', 'rar']:
                        file_type_display = 'archive'
                    else:
                        file_type_display = 'document'
                    
                    # 格式化文件大小
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    
                    all_files.append({
                        'id': len(all_files) + 1,
                        'filename': filename,
                        'file_type': file_type_display,
                        'size': size_str,
                        'uploaded_by': current_user.username,
                        'uploaded_at': datetime.fromtimestamp(file_stat.st_mtime),
                        'project': '未分类',
                        'category': 'other'
                    })
        
        # 按上传时间倒序排列
        all_files.sort(key=lambda x: x['uploaded_at'], reverse=True)
        
        # 应用筛选
        filtered_files = all_files
        
        if file_type:
            filtered_files = [f for f in filtered_files if f['file_type'] == file_type]
        if search:
            search_lower = search.lower()
            filtered_files = [f for f in filtered_files 
                               if search_lower in f['filename'].lower() 
                               or search_lower in f['project'].lower()]
        
        # 分页
        total = len(filtered_files)
        start = (page - 1) * per_page
        end = start + per_page
        files_page = filtered_files[start:end]
        
        return render_template('staff/staff_files.html',
                             files=files_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             file_type=file_type,
                             search=search)
    except Exception as e:
        flash(f'加载文件列表失败：{str(e)}', 'error')
        return render_template('staff/staff_files.html',
                             files=[],
                             current_page=1,
                             total_pages=1,
                             total=0)

@staff.route('/upload_file', methods=['GET', 'POST'])
@login_required
@staff_only
def upload_file():
    """上传文件"""
    if request.method == 'POST':
        try:
            # 检查是否有文件
            if 'file' not in request.files:
                flash('没有选择文件', 'error')
                return render_template('staff/staff_upload.html')
            
            file = request.files['file']
            if file.filename == '':
                flash('没有选择文件', 'error')
                return render_template('staff/staff_upload.html')
            
            # 获取其他表单数据
            filename = request.form.get('filename', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '')
            project = request.form.get('project', '')
            tags = request.form.get('tags', '').strip()
            
            # 基础验证
            if not category:
                flash('请选择文件分类', 'error')
                return render_template('staff/staff_upload.html')
            
            # 检查文件类型
            allowed_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar'}
            if not allowed_file(file.filename, allowed_extensions):
                flash('不支持的文件类型', 'error')
                return render_template('staff/staff_upload.html')
            
            # 确保上传目录存在
            upload_folder = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # 保存文件
            if filename:
                # 使用用户指定的文件名，但需要添加扩展名
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext:
                    filename = f"{filename}.{file_ext}"
                else:
                    filename = filename
            else:
                # 使用原始文件名
                filename = secure_filename(file.filename)
            
            # 确保文件名唯一
            file_path = os.path.join(upload_folder, filename)
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}{ext}"
                file_path = os.path.join(upload_folder, filename)
                counter += 1
            
            # 保存文件
            file.save(file_path)
            
            # 这里可以保存文件信息到数据库
            # 暂时只显示成功消息
            
            flash(f'文件上传成功！文件名：{filename}', 'success')
            return redirect(url_for('staff.files'))
            
        except Exception as e:
            flash(f'文件上传失败：{str(e)}', 'error')
    
    return render_template('staff/staff_upload.html')

@staff.route('/download/<filename>')
@login_required
@staff_only
def download_file(filename):
    """下载文件"""
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(upload_folder, filename, as_attachment=True)
        else:
            flash('文件不存在', 'error')
            return redirect(url_for('staff.files'))
    except Exception as e:
        flash(f'下载文件失败：{str(e)}', 'error')
        return redirect(url_for('staff.files'))

@staff.route('/delete_file/<filename>')
@login_required
@staff_only
def delete_file(filename):
    """删除文件"""
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            flash(f'文件 {filename} 删除成功', 'success')
        else:
            flash('文件不存在', 'error')
    except Exception as e:
        flash(f'删除文件失败：{str(e)}', 'error')
    
    return redirect(url_for('staff.files'))

# ==================== API 路由 ====================
@staff.route('/api/stats')
@login_required
@staff_only
def api_stats():
    """获取统计数据"""
    try:
        # 导入必要的模型
        from ...business.projects.models.project import ProjectHeader, CustomerCompany
        from ...business.projects.models.ref import ProjectRef
        from datetime import datetime
        
        # 构建基础查询
        base_query = ProjectHeader.query
        
        # 根据员工等级过滤项目
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己创建的项目
                base_query = base_query.filter(ProjectHeader.staff_name == current_user.username)
            # 2级员工可以看到所有项目，不需要额外过滤
        
        # 获取真实统计数据
        total_projects = base_query.count()
        active_projects = base_query.filter_by(status='active').count()
        
        # 计算本月完成的项目
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        completed_this_month = base_query.filter(
            ProjectHeader.status == 'completed',
            ProjectHeader.updated_at >= current_month_start
        ).count()
        
        # 计算待处理报价（状态为draft的项目）
        pending_quotes = base_query.filter_by(status='draft').count()
        
        # 计算财务数据
        all_projects = base_query.all()
        total_revenue = 0
        total_cost = 0
        
        for project in all_projects:
            refs = ProjectRef.query.filter_by(header_id=project.id).all()
            for ref in refs:
                if ref.selling_price:
                    total_revenue += float(ref.selling_price)
                if ref.cost_price:
                    total_cost += float(ref.cost_price)
        
        total_profit = total_revenue - total_cost
        
        stats = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'pending_quotes': pending_quotes,
            'completed_this_month': completed_this_month,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_profit
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@staff.route('/api/recent-projects')
@login_required
@staff_only
def api_recent_projects():
    """获取最近项目"""
    try:
        # 导入必要的模型
        from ...business.projects.models.project import ProjectHeader, CustomerCompany
        from ...business.projects.models.ref import ProjectRef
        
        # 构建基础查询
        base_query = ProjectHeader.query
        
        # 根据员工等级过滤项目
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己创建的项目
                base_query = base_query.filter(ProjectHeader.staff_name == current_user.username)
            # 2级员工可以看到所有项目，不需要额外过滤
        
        # 获取最近的项目（最近10个）
        recent_projects_query = base_query.order_by(ProjectHeader.created_at.desc()).limit(10)
        projects = []
        
        for project in recent_projects_query:
            # 计算项目财务数据
            refs = ProjectRef.query.filter_by(header_id=project.id).all()
            total_selling_price = sum([float(ref.selling_price or 0) for ref in refs])
            total_cost_price = sum([float(ref.cost_price or 0) for ref in refs])
            total_profit = total_selling_price - total_cost_price
            
            # 获取客户公司名称
            client_name = '未指定客户'
            if project.company_id and project.company:
                client_name = project.company.company_name
            
            # 构建项目数据
            project_data = {
                'id': project.id,
                'hid': project.hid,
                'name': project.desc or f'项目 {project.hid}',
                'client': client_name,
                'leader': project.leader_name or '未指定负责人',
                'contact': project.contact or '未指定联系人',
                'status': project.status,
                'type': project.type or '综合',
                'created_at': project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else '',
                'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M') if project.updated_at else '',
                'total_selling': total_selling_price,
                'total_cost': total_cost_price,
                'total_profit': total_profit,
                'ref_count': len(refs)
            }
            projects.append(project_data)
        
        return jsonify({
            'success': True,
            'data': projects
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@staff.route('/api/pending-tasks')
@login_required
@staff_only
def api_pending_tasks():
    """获取待处理任务"""
    try:
        # 导入必要的模型
        from ...shared.models.Utilsmodels import Todo
        
        # 获取未完成的待办事项（真正的待处理任务）
        pending_tasks = []
        
        # 构建基础查询
        base_query = Todo.query.filter_by(is_completed=False)
        
        # 根据员工等级过滤待办事项
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己创建的待办事项
                base_query = base_query.filter(Todo.user_id == current_user.id)
            # 2级员工可以看到所有待办事项，不需要额外过滤
        
        todos = base_query.order_by(Todo.created_at.desc()).all()
        
        for todo in todos[:5]:  # 限制显示5个任务
            # 转换优先级数字为文本
            priority_map = {1: 'high', 2: 'medium', 3: 'low'}
            priority_text = priority_map.get(todo.priority, 'medium')
            
            task_data = {
                'id': todo.id,
                'title': todo.title,
                'description': todo.description or f'待办事项: {todo.title}',
                'priority': priority_text,
                'due_date': todo.due_date.strftime('%Y-%m-%d') if todo.due_date else '未设置',
                'type': 'todo'
            }
            pending_tasks.append(task_data)
        
        return jsonify({
            'success': True,
            'data': pending_tasks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 任务管理 ====================
@staff.route('/tasks')
@login_required
@staff_only
def tasks():
    """任务中心 - 重定向到todo_list页面"""
    return redirect(url_for('utils_blue.render_todo_list'))

# ==================== 客户管理 ====================
@staff.route('/customers')
@login_required
@staff_only
def customers():
    """客户列表"""
    try:
        # 获取筛选参数
        status = request.args.get('status', '')
        industry = request.args.get('industry', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 模拟客户数据
        all_customers = [
            {
                'id': 1,
                'company_name': 'ABC旅行社',
                'company_code': 'ABC001',
                'contact_person': '张经理',
                'contact_phone': '+86 138 0013 8000',
                'contact_email': 'zhang@abc.com',
                'industry': 'travel',
                'status': 'active',
                'credit_limit': 100000.00,
                'created_at': datetime(2024, 1, 15)
            },
            {
                'id': 2,
                'company_name': 'XYZ企业',
                'company_code': 'XYZ002',
                'contact_person': '李总',
                'contact_phone': '+86 139 0023 9000',
                'contact_email': 'li@xyz.com',
                'industry': 'business',
                'status': 'active',
                'credit_limit': 200000.00,
                'created_at': datetime(2024, 1, 16)
            },
            {
                'id': 3,
                'company_name': 'DEF教育集团',
                'company_code': 'DEF003',
                'contact_person': '王主任',
                'contact_phone': '+86 137 0033 7000',
                'contact_email': 'wang@def.com',
                'industry': 'education',
                'status': 'pending',
                'credit_limit': 50000.00,
                'created_at': datetime(2024, 1, 17)
            }
        ]
        
        # 应用筛选
        filtered_customers = all_customers
        
        if status:
            filtered_customers = [c for c in filtered_customers if c['status'] == status]
        if industry:
            filtered_customers = [c for c in filtered_customers if c['industry'] == industry]
        if search:
            search_lower = search.lower()
            filtered_customers = [c for c in filtered_customers 
                                 if search_lower in c['company_name'].lower() 
                                 or search_lower in c['contact_person'].lower()
                                 or search_lower in c['company_code'].lower()]
        
        # 分页
        total = len(filtered_customers)
        start = (page - 1) * per_page
        end = start + per_page
        customers_page = filtered_customers[start:end]
        
        return render_template('staff/staff_customers.html',
                             customers=customers_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             status=status,
                             industry=industry,
                             search=search)
    except Exception as e:
        flash(f'加载客户列表失败：{str(e)}', 'error')
        return render_template('staff/staff_customers.html',
                             customers=[],
                             current_page=1,
                             total_pages=1,
                             total=0,
                             status='',
                             industry='',
                             search='')

# ==================== 供应商管理 ====================
@staff.route('/suppliers')
@login_required
@staff_only
def suppliers():
    """供应商列表"""
    try:
        # 获取筛选参数
        status = request.args.get('status', '')
        supplier_type = request.args.get('supplier_type', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 模拟供应商数据
        all_suppliers = [
            {
                'id': 1,
                'name': '新加坡签证中心',
                'address': '新加坡市中心商务区',
                'contact_person': '陈经理',
                'phone': '+65 9123 4567',
                'email': 'chen@sgvisa.com',
                'supplier_type': 'visa',
                'country': '新加坡',
                'region': '市中心',
                'status': 'active',
                'created_at': datetime(2024, 1, 15)
            },
            {
                'id': 2,
                'name': '泰国航空代理',
                'address': '曼谷素万那普机场',
                'contact_person': 'Somchai',
                'phone': '+66 81 234 5678',
                'email': 'somchai@thaiair.com',
                'supplier_type': 'flight',
                'country': '泰国',
                'region': '曼谷',
                'status': 'active',
                'created_at': datetime(2024, 1, 16)
            },
            {
                'id': 3,
                'name': '马来西亚酒店联盟',
                'address': '吉隆坡双子塔附近',
                'contact_person': 'Ahmad',
                'phone': '+60 12 345 6789',
                'email': 'ahmad@myhotel.com',
                'supplier_type': 'hotel',
                'country': '马来西亚',
                'region': '吉隆坡',
                'status': 'pending',
                'created_at': datetime(2024, 1, 17)
            }
        ]
        
        # 应用筛选
        filtered_suppliers = all_suppliers
        
        if status:
            filtered_suppliers = [s for s in filtered_suppliers if s['status'] == status]
        if supplier_type:
            filtered_suppliers = [s for s in filtered_suppliers if s['supplier_type'] == supplier_type]
        if search:
            search_lower = search.lower()
            filtered_suppliers = [s for s in filtered_suppliers 
                                 if search_lower in s['name'].lower() 
                                 or search_lower in s['contact_person'].lower()
                                 or search_lower in s['supplier_type'].lower()]
        
        # 分页
        total = len(filtered_suppliers)
        start = (page - 1) * per_page
        end = start + per_page
        suppliers_page = filtered_suppliers[start:end]
        
        return render_template('staff/staff_suppliers.html',
                             suppliers=suppliers_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             status=status,
                             supplier_type=supplier_type,
                             search=search)
    except Exception as e:
        flash(f'加载供应商列表失败：{str(e)}', 'error')
        return render_template('staff/staff_suppliers.html',
                             suppliers=[],
                             current_page=1,
                             total_pages=1,
                             total=0,
                             status='',
                             supplier_type='',
                             search='')

# ==================== 业务类型管理 ====================
@staff.route('/business_types')
@login_required
@staff_only
def business_types():
    """业务类型列表"""
    try:
        # 获取筛选参数
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 模拟业务类型数据
        all_business_types = [
            {
                'id': 1,
                'code': 'VISA_SG',
                'name_cn': '新加坡签证',
                'name_en': 'Singapore Visa',
                'description': '新加坡各类签证服务，包括旅游签证、商务签证、工作签证等',
                'category': 'visa',
                'parent_id': None,
                'level': 1,
                'sort_order': 1,
                'is_active': True,
                'icon': 'fas fa-passport',
                'color': '#007bff',
                'created_at': datetime(2024, 1, 15)
            },
            {
                'id': 2,
                'code': 'VISA_SG_TOURIST',
                'name_cn': '新加坡旅游签证',
                'name_en': 'Singapore Tourist Visa',
                'description': '新加坡旅游签证，适用于短期旅游观光',
                'category': 'visa',
                'parent_id': 1,
                'level': 2,
                'sort_order': 1,
                'is_active': True,
                'icon': 'fas fa-plane',
                'color': '#28a745',
                'created_at': datetime(2024, 1, 15)
            },
            {
                'id': 3,
                'code': 'FLIGHT_INTL',
                'name_cn': '国际机票',
                'name_en': 'International Flight',
                'description': '国际航班机票预订服务',
                'category': 'flight',
                'parent_id': None,
                'level': 1,
                'sort_order': 2,
                'is_active': True,
                'icon': 'fas fa-plane',
                'color': '#ffc107',
                'created_at': datetime(2024, 1, 16)
            },
            {
                'id': 4,
                'code': 'TOUR_PACKAGE',
                'name_cn': '旅游套餐',
                'name_en': 'Tour Package',
                'description': '完整的旅游套餐服务，包括机票、酒店、景点等',
                'category': 'tour',
                'parent_id': None,
                'level': 1,
                'sort_order': 3,
                'is_active': True,
                'icon': 'fas fa-suitcase',
                'color': '#17a2b8',
                'created_at': datetime(2024, 1, 17)
            }
        ]
        
        # 应用筛选
        filtered_types = all_business_types
        
        if category:
            filtered_types = [t for t in filtered_types if t['category'] == category]
        if status:
            if status == 'active':
                filtered_types = [t for t in filtered_types if t['is_active']]
            else:
                filtered_types = [t for t in filtered_types if not t['is_active']]
        if search:
            search_lower = search.lower()
            filtered_types = [t for t in filtered_types 
                             if search_lower in t['name_cn'].lower() 
                             or search_lower in t['name_en'].lower()
                             or search_lower in t['code'].lower()
                             or (t['description'] and search_lower in t['description'].lower())]
        
        # 分页
        total = len(filtered_types)
        start = (page - 1) * per_page
        end = start + per_page
        types_page = filtered_types[start:end]
        
        return render_template('staff/staff_business_types.html',
                             business_types=types_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             category=category,
                             status=status,
                             search=search)
    except Exception as e:
        flash(f'加载业务类型列表失败：{str(e)}', 'error')
        return render_template('staff/staff_business_types.html',
                             business_types=[],
                             current_page=1,
                             total_pages=1,
                             total=0,
                             category='',
                             status='',
                             search='')

# ==================== 工作报告 ====================
@staff.route('/reports')
@login_required
@staff_only
def reports():
    """工作报告"""
    try:
        # 获取报告参数
        report_type = request.args.get('type', 'monthly')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # 模拟报告数据
        report_data = {
            'total_projects': 15,
            'completed_projects': 8,
            'pending_projects': 5,
            'cancelled_projects': 2,
            'total_revenue': 25000.00,
            'total_cost': 18000.00,
            'total_profit': 7000.00,
            'profit_margin': 28.0
        }
        
        return render_template('staff/staff_reports.html',
                             report_data=report_data,
                             report_type=report_type,
                             start_date=start_date,
                             end_date=end_date)
    except Exception as e:
        flash(f'加载报告失败：{str(e)}', 'error')
        return render_template('staff/staff_reports.html',
                             report_data={},
                             report_type='monthly',
                             start_date='',
                             end_date='')


# ==================== 首页轮播图管理 ====================

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_image_file(filename):
    """检查是否为允许的图片格式"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@staff.route('/home-banners')
@login_required
@staff_only
def home_banners():
    """首页轮播图管理列表"""
    from ...business.tour.models.Packagemodels import HomeBanner
    
    try:
        banners = HomeBanner.get_all_banners()
        return render_template('staff/home_banners.html', banners=banners)
    except Exception as e:
        flash(f'加载轮播图列表失败：{str(e)}', 'error')
        return render_template('staff/home_banners.html', banners=[])


@staff.route('/home-banners/upload', methods=['POST'])
@login_required
@staff_only
def upload_home_banner():
    """上传首页轮播图"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400
        
        if not allowed_image_file(file.filename):
            return jsonify({'success': False, 'message': '不支持的图片格式，请上传 PNG、JPG、JPEG、GIF 或 WEBP 格式'}), 400
        
        # 保存图片
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"banner_{timestamp}.{ext}"
        
        # 创建上传目录
        upload_dir = os.path.join('App_new', 'static', 'uploads', 'banners')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, new_filename)
        file.save(file_path)
        
        # 获取表单数据
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        link_url = request.form.get('link_url', '').strip()
        
        # 获取当前最大排序号
        max_order = db.session.query(db.func.max(HomeBanner.sort_order)).scalar() or 0
        
        # 创建数据库记录
        banner = HomeBanner(
            title=title or None,
            description=description or None,
            image_path=f"uploads/banners/{new_filename}",
            link_url=link_url or None,
            sort_order=max_order + 1,
            is_active=True,
            created_by=current_user.username
        )
        
        db.session.add(banner)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': '轮播图上传成功',
            'banner': {
                'id': banner.id,
                'title': banner.title,
                'image_path': banner.image_path,
                'is_active': banner.is_active
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'}), 500


@staff.route('/home-banners/<int:banner_id>/delete', methods=['POST'])
@login_required
@staff_only
def delete_home_banner(banner_id):
    """删除首页轮播图"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        banner = HomeBanner.query.get_or_404(banner_id)
        
        # 删除图片文件
        if banner.image_path:
            file_path = os.path.join('App_new', 'static', banner.image_path)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    current_app.logger.warning(f"删除图片文件失败: {e}")
        
        db.session.delete(banner)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '轮播图已删除'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500


@staff.route('/home-banners/<int:banner_id>/toggle', methods=['POST'])
@login_required
@staff_only
def toggle_home_banner(banner_id):
    """切换轮播图启用/禁用状态"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        banner = HomeBanner.query.get_or_404(banner_id)
        banner.is_active = not banner.is_active
        db.session.commit()
        
        status = '启用' if banner.is_active else '禁用'
        return jsonify({'success': True, 'message': f'轮播图已{status}', 'is_active': banner.is_active})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败：{str(e)}'}), 500


@staff.route('/home-banners/<int:banner_id>/update', methods=['POST'])
@login_required
@staff_only
def update_home_banner(banner_id):
    """更新轮播图信息"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        banner = HomeBanner.query.get_or_404(banner_id)
        
        data = request.get_json()
        if data:
            if 'title' in data:
                banner.title = data['title'].strip() or None
            if 'description' in data:
                banner.description = data['description'].strip() or None
            if 'link_url' in data:
                banner.link_url = data['link_url'].strip() or None
            if 'sort_order' in data:
                banner.sort_order = int(data['sort_order'])
        
        db.session.commit()
        return jsonify({'success': True, 'message': '更新成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


@staff.route('/home-banners/reorder', methods=['POST'])
@login_required
@staff_only
def reorder_home_banners():
    """重新排序轮播图"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        data = request.get_json()
        order_list = data.get('order', [])  # [banner_id, banner_id, ...]
        
        for index, banner_id in enumerate(order_list):
            banner = HomeBanner.query.get(banner_id)
            if banner:
                banner.sort_order = index
        
        db.session.commit()
        return jsonify({'success': True, 'message': '排序已更新'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'排序失败：{str(e)}'}), 500
