from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from App_new.shared.models.Utilsmodels import Task, Todo
from App_new.exts import db, csrf
from App_new.utils.decorators import staff_only
from datetime import datetime
import traceback

# 定义蓝图
utils_blue = Blueprint('utils_blue', __name__)

@utils_blue.route('/render_pomodoro', methods=['GET'])
@login_required
@staff_only
def render_pomodoro():
    return render_template('utils/番茄工作法.html')

# 获取任务列表
@utils_blue.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([{
        'id': task.id,
        'name': task.name,
        'remaining_time': task.remaining_time,
        'status': task.status
    } for task in tasks])

# 添加任务
@utils_blue.route('/tasks', methods=['POST'])
def add_task():
    data = request.get_json()
    task = Task(
        name=data['name'],
        remaining_time=data['remaining_time'],
        status=data.get('status', 'pending')
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({
        'id': task.id,
        'name': task.name,
        'remaining_time': task.remaining_time,
        'status': task.status
    })

# 更新任务
@utils_blue.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    
    task.name = data.get('name', task.name)
    task.remaining_time = data.get('remaining_time', task.remaining_time)
    task.status = data.get('status', task.status)
    
    db.session.commit()
    return jsonify({
        'id': task.id,
        'name': task.name,
        'remaining_time': task.remaining_time,
        'status': task.status
    })

# 删除任务
@utils_blue.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return '', 204

# 重置任务
@utils_blue.route('/tasks/<int:task_id>/reset', methods=['POST'])
def reset_task(task_id):
    task = Task.reset(task_id)
    if task:
        return jsonify({'message': 'Task reset to 10 minutes'})
    return jsonify({'message': 'Task not found'}), 404

# 切换任务状态（开始或暂停）
@utils_blue.route('/tasks/<int:task_id>/toggle', methods=['GET','POST'])
def toggle_task(task_id):
    task = Task.query.get(task_id)
    if task:
        task_data = request.get_json()  # 获取前端传来的 JSON 数据
        remaining_time = task_data.get('remaining_time')  # 从请求中提取剩余时间

        # 如果任务正在运行，保存当前时间并暂停任务
        if task.status == 'running':
            Task.update_status(task_id, status='paused', remaining_time=remaining_time)
            return jsonify({'message': 'Task paused', 'remaining_time': remaining_time})

        # 如果任务处于暂停状态或停止状态，则恢复运行
        elif task.status in ['paused', 'stopped']:
            Task.update_status(task_id, status='running', remaining_time=remaining_time)
            return jsonify({'message': 'Task started', 'remaining_time': remaining_time})

        return jsonify({'message': 'Invalid task status'}), 400
    return jsonify({'message': 'Task not found'}), 404

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
            user_id=None  # 暂时设置为None避免外键约束问题
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