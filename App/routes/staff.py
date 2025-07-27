"""
员工功能路由
员工仪表板、项目管理、报价管理、文件上传等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from App.utils.decorators import staff_only, require_permission
from App.models.auth import AuthUser
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
        # 获取员工统计信息
        stats = {
            'total_projects': 0,  # 总项目数
            'active_projects': 0,  # 活跃项目
            'pending_quotes': 0,  # 待处理报价
            'completed_this_month': 0,  # 本月完成项目
        }
        
        # 获取最近的项目
        recent_projects = []
        
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
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 获取项目状态筛选
        status = request.args.get('status', '')
        project_type = request.args.get('type', '')
        
        # 暂时返回空的项目列表
        projects = []
        pagination = None
        
        return render_template('staff/projects.html',
                             projects=projects,
                             pagination=pagination,
                             current_status=status,
                             current_type=project_type)
    except Exception as e:
        flash(f'加载项目列表失败：{str(e)}', 'error')
        return render_template('staff/projects.html',
                             projects=[], pagination=None, 
                             current_status='', current_type='')

@staff.route('/project/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_project():
    """创建新项目"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            project_name = request.form.get('project_name', '').strip()
            project_type = request.form.get('project_type', '')
            client_name = request.form.get('client_name', '').strip()
            description = request.form.get('description', '').strip()
            
            # 基础验证
            if not all([project_name, project_type, client_name]):
                flash('请填写所有必填字段', 'error')
                return render_template('staff/create_project.html')
            
            # 这里应该创建项目，暂时模拟
            flash('项目创建成功！', 'success')
            return redirect(url_for('staff.projects'))
            
        except Exception as e:
            flash(f'创建项目失败：{str(e)}', 'error')
    
    return render_template('staff/create_project.html')

@staff.route('/project/<int:project_id>')
@login_required
@staff_only
def project_detail(project_id):
    """项目详情"""
    try:
        # 暂时返回404，因为项目模型还未完全实现
        return render_template('staff/404.html', message='项目详情功能开发中'), 404
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
    """任务管理"""
    try:
        # 获取任务状态筛选
        status = request.args.get('status', '')
        priority = request.args.get('priority', '')
        
        # 暂时返回空的任务列表
        tasks = []
        
        return render_template('staff/tasks.html',
                             tasks=tasks,
                             current_status=status,
                             current_priority=priority)
    except Exception as e:
        flash(f'加载任务列表失败：{str(e)}', 'error')
        return render_template('staff/tasks.html',
                             tasks=[], current_status='', current_priority='')

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
        stats = {
            'total_projects': 0,
            'active_projects': 0,
            'pending_quotes': 0,
            'completed_this_month': 0,
            'files_uploaded': 0,
            'tasks_pending': 0
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
        projects = [
            {
                'id': 1,
                'name': '示例项目',
                'client': '示例客户',
                'status': 'active',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'type': 'visa'
            }
        ]
        
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