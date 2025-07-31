"""
员工功能路由
员工仪表板、项目管理、报价管理、文件上传等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from App.utils.decorators import staff_only, require_permission
from App.models.auth import AuthUser
from App.models.projects.BookingProject import ProjectHeader, CustomerCompany
from App.forms.header_forms import ProjectHeaderForm
from App.exts import db
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

# 创建员工蓝图
staff = Blueprint('staff', __name__, url_prefix='/staff')

@staff.route('/dashboard')
@login_required
@staff_only
def dashboard():
    """员工仪表板"""
    try:
        from App.models.projects.BookingProject import ProjectHeader, ProjectRef, CustomerCompany
        from datetime import datetime, timedelta
        
        # 获取员工统计信息
        total_projects = ProjectHeader.query.count()
        active_projects = ProjectHeader.query.filter_by(status='active').count()
        completed_this_month = ProjectHeader.query.filter(
            ProjectHeader.status == 'completed',
            ProjectHeader.updated_at >= datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        stats = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'pending_quotes': 0,  # 待处理报价
            'completed_this_month': completed_this_month,
        }
        
        # 获取最近的项目（最近10个）
        recent_projects_query = ProjectHeader.query.order_by(ProjectHeader.created_at.desc()).limit(10)
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
            
            # 简化项目数据
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
        
        # 获取待处理任务
        pending_tasks = []
        
        return render_template('staff/dashboard.html', 
                             stats=stats,
                             recent_projects=recent_projects,
                             pending_tasks=pending_tasks)
    except Exception as e:
        flash(f'加载仪表板失败：{str(e)}', 'error')
        return render_template('staff/dashboard.html',
                             stats={}, recent_projects=[], pending_tasks=[])

@staff.route('/projects')
@login_required
@staff_only
def projects():
    """项目列表"""
    try:
        # 获取筛选参数
        status = request.args.get('status', '')
        project_type = request.args.get('type', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 构建查询
        query = ProjectHeader.query
        
        # 基础筛选
        if status:
            query = query.filter(ProjectHeader.status == status)
        
        if search:
            query = query.filter(
                db.or_(
                    ProjectHeader.hid.contains(search),
                    ProjectHeader.desc.contains(search),
                    ProjectHeader.contact.contains(search)
                )
            )
        
        # 按创建时间倒序排列
        query = query.order_by(ProjectHeader.created_at.desc())
        
        # 分页
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        projects = pagination.items
        
        # 计算项目统计
        total_projects = ProjectHeader.query.count()
        pending_count = ProjectHeader.query.filter_by(status='pending').count()
        active_count = ProjectHeader.query.filter_by(status='active').count()
        completed_count = ProjectHeader.query.filter_by(status='completed').count()
        
        return render_template('staff/projects.html',
                             projects=projects,
                             pagination=pagination,
                             current_status=status,
                             current_type=project_type,
                             total_projects=total_projects,
                             pending_count=pending_count,
                             active_count=active_count,
                             completed_count=completed_count)
    except Exception as e:
        flash(f'加载项目列表失败：{str(e)}', 'error')
        return render_template('staff/projects.html',
                             projects=[], pagination=None, 
                             current_status='', current_type='',
                             total_projects=0, pending_count=0,
                             active_count=0, completed_count=0)

@staff.route('/project/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_project():
    """创建新项目（HID项目）"""
    form = ProjectHeaderForm()
    
    if form.validate_on_submit():
        try:
            hid = ProjectHeader.generate_hid()
            
            # 处理公司信息
            company_id = None
            
            if form.company_id.data and form.company_id.data != 0:
                company_id = form.company_id.data
            
            header = ProjectHeader(
                hid=hid,
                desc=form.desc.data,
                company_id=company_id,
                limit=form.limit.data,
                contact=form.contact.data,
                dept=form.dept.data,
                staff_id=current_user.id if current_user.is_authenticated else None,
                staff_name=form.staff_name.data,
                leader_name=form.leader_name.data,
                currency=form.currency.data,
                type=form.type.data,
                source=form.source.data,
                country=form.country.data,
                status=form.status.data,
                remarks=form.remarks.data
            )
            db.session.add(header)
            db.session.commit()
            flash('项目主表创建成功！', 'success')
            return redirect(url_for('staff.project_detail', project_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充项目编号
    hid = ProjectHeader.generate_hid()
    form.hid.data = hid
    
    # 预填充经办人姓名（当前登录用户）
    if current_user.is_authenticated:
        if current_user.profile and current_user.profile.get_full_name() != "未设置姓名":
            form.staff_name.data = current_user.profile.get_full_name()
        else:
            # 如果用户资料未设置姓名，使用用户名
            form.staff_name.data = current_user.username
    
    return render_template('staff/create_project.html', form=form, hid=hid)

@staff.route('/project/<int:project_id>')
@login_required
@staff_only
def project_detail(project_id):
    """项目详情"""
    try:
        # 重定向到原有的项目详情页面
        return redirect(url_for('projects.header_detail', header_id=project_id))
    except Exception as e:
        flash(f'加载项目详情失败：{str(e)}', 'error')
        return render_template('staff/404.html', message='加载失败'), 500

@staff.route('/quotes')
@login_required
@staff_only
def quotes():
    """报价列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 获取报价状态筛选
        status = request.args.get('status', '')
        quote_type = request.args.get('type', '')
        
        # 暂时返回空的报价列表
        quotes = []
        pagination = None
        
        return render_template('staff/quotes.html',
                             quotes=quotes,
                             pagination=pagination,
                             current_status=status,
                             current_type=quote_type)
    except Exception as e:
        flash(f'加载报价列表失败：{str(e)}', 'error')
        return render_template('staff/quotes.html',
                             quotes=[], pagination=None,
                             current_status='', current_type='')

@staff.route('/quote/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_quote():
    """创建新报价"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            quote_name = request.form.get('quote_name', '').strip()
            client_name = request.form.get('client_name', '').strip()
            service_type = request.form.get('service_type', '')
            amount = request.form.get('amount', '0')
            
            # 基础验证
            if not all([quote_name, client_name, service_type]):
                flash('请填写所有必填字段', 'error')
                return render_template('staff/create_quote.html')
            
            # 验证金额
            try:
                amount = float(amount)
                if amount < 0:
                    flash('金额不能为负数', 'error')
                    return render_template('staff/create_quote.html')
            except ValueError:
                flash('请输入有效的金额', 'error')
                return render_template('staff/create_quote.html')
            
            # 这里应该创建报价，暂时模拟
            flash('报价创建成功！', 'success')
            return redirect(url_for('staff.quotes'))
            
        except Exception as e:
            flash(f'创建报价失败：{str(e)}', 'error')
    
    return render_template('staff/create_quote.html')

@staff.route('/quote/<int:quote_id>')
@login_required
@staff_only
def quote_detail(quote_id):
    """报价详情"""
    try:
        # 暂时返回404，因为报价模型还未完全实现
        return render_template('staff/404.html', message='报价详情功能开发中'), 404
    except Exception as e:
        flash(f'加载报价详情失败：{str(e)}', 'error')
        return render_template('staff/404.html', message='加载失败'), 500

@staff.route('/files')
@login_required
@staff_only
def files():
    """文件管理"""
    try:
        # 获取文件类型筛选
        file_type = request.args.get('type', '')
        
        # 暂时返回空的文件列表
        files = []
        
        return render_template('staff/files.html',
                             files=files,
                             current_type=file_type)
    except Exception as e:
        flash(f'加载文件列表失败：{str(e)}', 'error')
        return render_template('staff/files.html',
                             files=[], current_type='')

@staff.route('/upload', methods=['GET', 'POST'])
@login_required
@staff_only
def upload_file():
    """文件上传"""
    if request.method == 'POST':
        try:
            # 检查是否有文件
            if 'file' not in request.files:
                flash('没有选择文件', 'error')
                return render_template('staff/upload.html')
            
            file = request.files['file']
            if file.filename == '':
                flash('没有选择文件', 'error')
                return render_template('staff/upload.html')
            
            # 获取其他表单数据
            file_type = request.form.get('file_type', '')
            description = request.form.get('description', '').strip()
            project_id = request.form.get('project_id', '')
            
            # 基础验证
            if not file_type:
                flash('请选择文件类型', 'error')
                return render_template('staff/upload.html')
            
            # 检查文件类型
            allowed_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'gif'}
            if not allowed_file(file.filename, allowed_extensions):
                flash('不支持的文件类型', 'error')
                return render_template('staff/upload.html')
            
            # 保存文件
            filename = secure_filename(file.filename)
            # 这里应该保存到指定目录，暂时模拟
            
            flash('文件上传成功！', 'success')
            return redirect(url_for('staff.files'))
            
        except Exception as e:
            flash(f'文件上传失败：{str(e)}', 'error')
    
    return render_template('staff/upload.html')

@staff.route('/tasks')
@login_required
@staff_only
def tasks():
    """任务管理 - 重定向到完整的待办事项系统"""
    return redirect(url_for('utils_blue.render_todo_list'))

# 工具函数
def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# API 路由
@staff.route('/api/stats')
@login_required
@staff_only
def api_stats():
    """获取员工统计数据"""
    try:
        from App.models.projects.BookingProject import ProjectHeader
        from datetime import datetime
        
        # 获取真实统计数据
        total_projects = ProjectHeader.query.count()
        active_projects = ProjectHeader.query.filter_by(status='active').count()
        completed_this_month = ProjectHeader.query.filter(
            ProjectHeader.status == 'completed',
            ProjectHeader.updated_at >= datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        stats = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'pending_quotes': 0,  # 待处理报价
            'completed_this_month': completed_this_month,
            'files_uploaded': 0,  # 文件上传统计
            'tasks_pending': 0    # 待处理任务统计
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

@staff.route('/api/recent-projects')
@login_required
@staff_only
def api_recent_projects():
    """获取最近项目"""
    try:
        from App.models.projects.BookingProject import ProjectHeader, ProjectRef, CustomerCompany
        
        # 获取最近的项目（最近10个）
        recent_projects_query = ProjectHeader.query.order_by(ProjectHeader.created_at.desc()).limit(10)
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
            
            # 简化项目数据
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
            'message': str(e)
        }), 500

@staff.route('/api/pending-tasks')
@login_required
@staff_only
def api_pending_tasks():
    """获取待处理任务"""
    try:
        tasks = [
            {
                'id': 1,
                'title': '欢迎使用员工系统',
                'description': '请完善您的个人资料并熟悉系统功能',
                'priority': 'medium',
                'due_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                'type': 'setup'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': tasks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500 