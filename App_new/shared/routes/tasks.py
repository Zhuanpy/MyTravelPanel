from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from App_new.shared.models.Utilsmodels import Todo
from App_new.exts import db, csrf
from App_new.utils.decorators import staff_only
from datetime import datetime
import traceback

# 定义蓝图
utils_blue = Blueprint('utils_blue', __name__)

# Task相关路由已删除，现在只保留Todo相关功能

# 签证项目管理
@utils_blue.route('/visa_project')
def visa_project():
    return render_template("utils/visa_project.html")

# 签证链接管理
@utils_blue.route('/visa_link')
def visa_link():
    return render_template("utils/visa_link.html")

# 待办事项列表页面
@utils_blue.route('/todo_list')
@login_required
@staff_only
def render_todo_list():
    return render_template('utils/todo_list.html')

# 待办事项列表API
@utils_blue.route('/todos/list')
@login_required
@staff_only
def list_todos():
    try:
        current_app.logger.info("开始获取待办事项列表")
        
        # 获取查询参数
        priority = request.args.get('priority', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        project_id = request.args.get('project_id', '')
        
        current_app.logger.info(f"查询参数: priority={priority}, status={status}, search={search}, category={category}, project_id={project_id}")
        
        # 构建查询
        query = Todo.query
        
        # 根据员工等级过滤待办事项
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己创建的待办事项
                query = query.filter(Todo.user_id == current_user.id)
            # 2级员工可以看到所有待办事项，不需要额外过滤
        
        # 应用过滤条件
        if priority:
            query = query.filter(Todo.priority == int(priority))
        if status:
            query = query.filter(Todo.is_completed == (status == 'completed'))
        if search:
            query = query.filter(Todo.title.ilike(f'%{search}%'))
        if category:
            query = query.filter(Todo.category == category)
        if project_id:
            # 根据项目ID筛选，检查标题或描述中是否包含项目ID
            query = query.filter(
                (Todo.title.ilike(f'%项目ID: {project_id}%')) |
                (Todo.description.ilike(f'%项目ID: {project_id}%'))
            )
            
        # 执行查询
        todos = query.order_by(Todo.created_at.desc()).all()
        
        current_app.logger.info(f"查询到 {len(todos)} 条待办事项")
        
        # 转换为字典列表
        todos_list = [todo.to_dict() for todo in todos]
            
        return jsonify({
            'success': True,
            'todos': todos_list
        })
        
    except Exception as e:
        current_app.logger.error(f"获取待办事项列表时发生错误: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'获取待办事项列表失败: {str(e)}'
        }), 500

# 创建待办事项
@utils_blue.route('/todos/create', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def create_todo():
    try:
        data = request.get_json()
        current_app.logger.info(f"创建待办事项，数据: {data}")
        
        # 处理日期格式
        due_date = data.get('due_date')
        if due_date:
            try:
                from datetime import datetime
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                due_date = None
        
        todo = Todo.create(
            title=data.get('title'),
            description=data.get('description'),
            priority=int(data.get('priority', 2)),
            due_date=due_date,
            category=data.get('category'),
            user_id=current_user.id  # 关联到当前登录用户
        )
        
        return jsonify({
            'success': True,
            'message': '待办事项创建成功',
            'todo': todo.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"创建待办事项时发生错误: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'创建待办事项失败: {str(e)}'
        }), 500

# 更新待办事项
@utils_blue.route('/todos/update', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def update_todo():
    try:
        data = request.get_json()
        current_app.logger.info(f"更新待办事项，数据: {data}")
        
        # 处理日期格式
        due_date = data.get('due_date')
        if due_date:
            try:
                due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            except ValueError as e:
                current_app.logger.error(f"日期格式错误: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': '日期格式错误'
                }), 400
        
        # 更新待办事项
        todo = Todo.update(data['id'], **{
            'title': data.get('title'),
            'description': data.get('description'),
            'priority': int(data.get('priority', 2)),
            'is_completed': data.get('is_completed'),
            'due_date': due_date,
            'category': data.get('category')
        })
        
        if not todo:
            return jsonify({
                'success': False,
                'message': '待办事项不存在'
            }), 404
            
        return jsonify({
            'success': True,
            'message': '待办事项更新成功',
            'todo': todo.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"更新待办事项时发生错误: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'更新待办事项失败: {str(e)}'
        }), 500

# 删除待办事项
@utils_blue.route('/todos/delete', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_todo():
    try:
        data = request.get_json()
        current_app.logger.info(f"删除待办事项，ID: {data.get('id')}")
        
        if not Todo.delete(data['id']):
            return jsonify({
                'success': False,
                'message': '待办事项不存在'
            }), 404
            
        return jsonify({
            'success': True,
            'message': '待办事项删除成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"删除待办事项时发生错误: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'删除待办事项失败: {str(e)}'
        }), 500

# 获取单个待办事项
@utils_blue.route('/todos/get/<int:todo_id>')
@login_required
@staff_only
def get_todo(todo_id):
    try:
        todo = Todo.query.get(todo_id)
        if not todo:
            return jsonify({
                'success': False,
                'message': '待办事项不存在'
            }), 404

        return jsonify({
            'success': True,
            'todo': {
                'id': todo.id,
                'title': todo.title,
                'description': todo.description,
                'is_completed': todo.is_completed,
                'due_date': todo.due_date.isoformat() if todo.due_date else None,
                'priority': todo.priority,
                'category': todo.category,
                'created_at': todo.created_at.isoformat(),
                'updated_at': todo.updated_at.isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500