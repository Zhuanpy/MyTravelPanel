from flask import Blueprint, request, jsonify, render_template
from ..models.Utilsmodels import Task

# 定义蓝图
utils_blue = Blueprint('utils_blue', __name__)

@utils_blue.route('/render_pomodoro', methods=['GET'])
def render_pomodoro():
    return render_template('files/番茄工作法.html')

# 获取任务列表
@utils_blue.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    task_data = [{"id": task.id, "name": task.name, "remaining_time": task.remaining_time, "status": task.status} for task in tasks]
    return jsonify(task_data)

# 创建新任务
@utils_blue.route('/tasks', methods=['POST'])
def create_task():
    task_data = request.get_json()  # 从请求中获取 JSON 数据
    new_task = Task()  # 创建新任务对象
    new_task.create(name=task_data['name'])
    return jsonify({"message": "任务已创建", "task_id": new_task.id}), 201

# 删除任务
@utils_blue.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if Task.delete(task_id):
        return jsonify({'message': 'Task deleted successfully'})
    return jsonify({'message': 'Task not found'}), 404

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
@utils_blue.route('/render_visa_project')
def render_visa_project():
    return render_template("files/visa_project.html")

# 签证链接管理
@utils_blue.route('/render_visa_link')
def render_visa_link():
    return render_template("files/visa_link.html")