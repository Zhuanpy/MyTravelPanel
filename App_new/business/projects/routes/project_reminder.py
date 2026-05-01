"""
项目提醒管理路由
直接使用 todos 表存储项目提醒，通过 source_type='project_reminder' 关联
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.business.projects.models.project import ProjectHeader
from App_new.shared.models.Utilsmodels import Todo
from App_new.utils.decorators import staff_only
from datetime import datetime

project_reminder = Blueprint('project_reminder', __name__, url_prefix='/reminder')


@project_reminder.route('/<int:header_id>/list', methods=['GET'])
@login_required
@staff_only
def get_reminders(header_id):
    """获取项目的所有提醒"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 从 todos 表查询项目提醒
        todos = Todo.query.filter_by(
            source_type='project_reminder',
            source_id=header_id
        ).order_by(Todo.due_date.asc()).all()

        # 转换为前端需要的格式
        reminders = []
        for todo in todos:
            reminders.append({
                'id': todo.id,
                'header_id': header_id,
                'reminder_event': todo.title.replace(f'[{header.hid}] ', ''),  # 移除项目编号前缀
                'reminder_date': todo.due_date.strftime('%Y-%m-%dT%H:%M') if todo.due_date else None,
                'reminder_date_display': todo.due_date.strftime('%m-%d %H:%M') if todo.due_date else None,
                'is_completed': todo.is_completed,
                'created_by': None,
                'created_at': todo.created_at.strftime('%Y-%m-%d %H:%M') if todo.created_at else None
            })

        return jsonify({
            'success': True,
            'reminders': reminders
        })
    except Exception as e:
        current_app.logger.error(f"获取项目提醒列表失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@project_reminder.route('/<int:header_id>/create', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def create_reminder(header_id):
    """创建新提醒"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 检查是否已结算
        if header.is_settled:
            return jsonify({'success': False, 'message': '项目已结算，无法添加提醒'}), 400

        data = request.get_json()
        reminder_event = data.get('reminder_event', '').strip()
        reminder_date_str = data.get('reminder_date', '')

        if not reminder_event:
            return jsonify({'success': False, 'message': '请输入提醒内容'}), 400

        if not reminder_date_str:
            return jsonify({'success': False, 'message': '请选择提醒日期'}), 400

        try:
            # 支持datetime-local格式（含时间）和纯日期格式
            if 'T' in reminder_date_str:
                reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%dT%H:%M')
            else:
                reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'success': False, 'message': '日期格式错误'}), 400

        # 直接创建 Todo（创建者自动作为负责人）
        creator_id = current_user.id if current_user and hasattr(current_user, 'id') else None
        todo = Todo(
            title=f"[{header.hid}] {reminder_event}",
            description=f"项目: {header.hid}\n描述: {header.desc or ''}\n提醒事件: {reminder_event}",
            priority=2,
            due_date=reminder_date,
            category='项目提醒',
            source_type='project_reminder',
            source_id=header_id,
            is_completed=False,
            user_id=creator_id,
            assigned_to=creator_id,
            assigned_by=creator_id,
            assigned_at=datetime.utcnow() if creator_id else None
        )

        db.session.add(todo)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '提醒添加成功',
            'reminder': {
                'id': todo.id,
                'header_id': header_id,
                'reminder_event': reminder_event,
                'reminder_date': reminder_date.strftime('%Y-%m-%dT%H:%M'),
                'is_completed': todo.is_completed
            }
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建项目提醒失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@project_reminder.route('/<int:header_id>/update/<int:reminder_id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def update_reminder(header_id, reminder_id):
    """更新提醒"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 检查是否已结算
        if header.is_settled:
            return jsonify({'success': False, 'message': '项目已结算，无法修改提醒'}), 400

        # 查找对应的 Todo
        todo = Todo.query.filter_by(
            id=reminder_id,
            source_type='project_reminder',
            source_id=header_id
        ).first_or_404()

        data = request.get_json()

        if 'reminder_event' in data:
            reminder_event = data['reminder_event'].strip()
            if not reminder_event:
                return jsonify({'success': False, 'message': '请输入提醒内容'}), 400
            todo.title = f"[{header.hid}] {reminder_event}"
            todo.description = f"项目: {header.hid}\n描述: {header.desc or ''}\n提醒事件: {reminder_event}"

        if 'reminder_date' in data:
            try:
                date_str = data['reminder_date']
                if 'T' in date_str:
                    todo.due_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
                else:
                    todo.due_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'success': False, 'message': '日期格式错误'}), 400

        if 'is_completed' in data:
            todo.is_completed = data['is_completed']

        todo.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '提醒更新成功',
            'reminder': {
                'id': todo.id,
                'header_id': header_id,
                'reminder_event': todo.title.replace(f'[{header.hid}] ', ''),
                'reminder_date': todo.due_date.strftime('%Y-%m-%dT%H:%M') if todo.due_date else None,
                'is_completed': todo.is_completed
            }
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新项目提醒失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@project_reminder.route('/<int:header_id>/delete/<int:reminder_id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_reminder(header_id, reminder_id):
    """删除提醒"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        # 检查是否已结算
        if header.is_settled:
            return jsonify({'success': False, 'message': '项目已结算，无法删除提醒'}), 400

        # 查找对应的 Todo
        todo = Todo.query.filter_by(
            id=reminder_id,
            source_type='project_reminder',
            source_id=header_id
        ).first_or_404()

        db.session.delete(todo)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '提醒删除成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除项目提醒失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@project_reminder.route('/<int:header_id>/toggle/<int:reminder_id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def toggle_reminder(header_id, reminder_id):
    """切换提醒完成状态"""
    try:
        # 查找对应的 Todo
        todo = Todo.query.filter_by(
            id=reminder_id,
            source_type='project_reminder',
            source_id=header_id
        ).first_or_404()

        todo.is_completed = not todo.is_completed
        todo.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '状态更新成功',
            'is_completed': todo.is_completed
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"切换提醒状态失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
