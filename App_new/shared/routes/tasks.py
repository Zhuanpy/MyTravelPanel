from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from App_new.shared.models.Utilsmodels import Todo
from App_new.exts import db, csrf, scheduler
import re
from App_new.utils.decorators import staff_only
from datetime import datetime
import traceback
from flask_mail import Message
from App_new.exts import mail

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
    return render_template('shared/utils/todo_list.html')

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
        
        # 处理日期时间，支持多种格式
        def _parse_due_datetime(val: str):
            if not val:
                return None
            try:
                # 直接 ISO 格式（如 2025-10-06T17:30）
                return datetime.fromisoformat(val)
            except Exception:
                pass
            # 常见替换
            v = val.strip()
            v = v.replace('/', '-').replace(' ', 'T')
            try:
                return datetime.fromisoformat(v)
            except Exception:
                pass
            # 兜底：仅日期
            for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(val.replace('/', '-'), fmt)
                    return dt
                except Exception:
                    continue
            return None

        due_date = _parse_due_datetime(data.get('due_date'))
        
        todo = Todo.create(
            title=data.get('title'),
            description=data.get('description'),
            priority=int(data.get('priority', 2)),
            due_date=due_date,
            category=data.get('category'),
            user_id=current_user.id,  # 关联到当前登录用户
            recipient_email=data.get('recipient_email'),
            send_email=bool(data.get('send_email', False))
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
        
        # 处理日期格式（更新）
        def _parse_due_datetime(val: str):
            if not val:
                return None
            try:
                return datetime.fromisoformat(val.replace('Z', '+00:00'))
            except Exception:
                pass
            v = val.strip().replace('/', '-').replace(' ', 'T')
            try:
                return datetime.fromisoformat(v)
            except Exception:
                pass
            for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    return datetime.strptime(val.replace('/', '-'), fmt)
                except Exception:
                    continue
            return None

        due_date = _parse_due_datetime(data.get('due_date'))
        
        # 取旧值用来判断是否需要重置邮件发送状态
        todo_old = Todo.query.get(data['id'])
        old_due = getattr(todo_old, 'due_date', None)
        old_recipient = getattr(todo_old, 'recipient_email', None) or ''
        old_send_flag = bool(getattr(todo_old, 'send_email', False))

        new_recipient = data.get('recipient_email') or ''
        new_send_flag = bool(data.get('send_email', False))

        reset_email_status = False
        # 仅当需要发送邮件时，以下变更触发重置为“待发送”
        if new_send_flag:
            if (old_due != due_date) or (old_recipient.strip() != new_recipient.strip()) or (not old_send_flag and new_send_flag):
                reset_email_status = True

        update_payload = {
            'title': data.get('title'),
            'description': data.get('description'),
            'priority': int(data.get('priority', 2)),
            'is_completed': data.get('is_completed'),
            'due_date': due_date,
            'category': data.get('category'),
            'recipient_email': new_recipient,
            'send_email': new_send_flag
        }

        if reset_email_status:
            update_payload['email_reminder_sent'] = False
            update_payload['email_sent_at'] = None

        # 更新待办事项
        todo = Todo.update(data['id'], **update_payload)
        
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

# 发送提醒邮件
@utils_blue.route('/todos/send_reminder', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def send_todo_reminder():
    try:
        data = request.get_json() or {}
        todo_id = data.get('id')
        if not todo_id:
            return jsonify({'success': False, 'message': '缺少待办事项ID'}), 400

        todo = Todo.query.get(todo_id)
        if not todo:
            return jsonify({'success': False, 'message': '待办事项不存在'}), 404

        # 解析多个收件人，支持逗号/分号分隔
        def _parse_recipients(raw: str):
            if not raw:
                return []
            parts = re.split(r"[;,]", raw)
            return [p.strip() for p in parts if p and p.strip()]

        recipients = _parse_recipients(todo.recipient_email)
        if not recipients:
            return jsonify({'success': False, 'message': '未配置收件邮箱，请在待办事项中填写“收件邮箱”'}), 400

        subject = f"待办提醒：{todo.title}"
        desc = (todo.description or '').strip()
        due = todo.due_date.strftime('%Y-%m-%d %H:%M') if todo.due_date else '未设置'
        body = (
            f"您有一个待办提醒：\n\n"
            f"标题：{todo.title}\n"
            f"描述：{desc}\n"
            f"类型：{todo.category or '未分类'}\n"
            f"优先级：{todo.priority}\n"
            f"截止时间：{due}\n\n"
            f"此邮件由系统自动发送，请勿回复。"
        )

        # 组装并发送
        sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
        msg = Message(subject=subject, sender=sender, recipients=recipients, body=body)
        mail.send(msg)

        return jsonify({'success': True, 'message': '提醒邮件已发送'})

    except Exception as e:
        current_app.logger.error(f"发送待办提醒邮件失败: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'发送失败：{str(e)}'}), 500


def send_due_todo_reminders():
    """扫描到期需要发送的待办事项并发送提醒邮件。"""
    with current_app.app_context():
        try:
            # 使用本地时间对比，避免时区导致的误差
            now = datetime.now()
            # 仅选取必要字段，避免大开销
            todos = Todo.query.filter(
                Todo.send_email.is_(True),
                Todo.is_completed.is_(False),
                Todo.due_date.isnot(None),
                Todo.due_date <= now,
                getattr(Todo, 'email_reminder_sent', False).is_(False)
            ).order_by(Todo.due_date.asc()).all()

            sent_count = 0
            def _parse_recipients(raw: str):
                if not raw:
                    return []
                parts = re.split(r"[;,]", raw)
                return [p.strip() for p in parts if p and p.strip()]

            for todo in todos:
                recipients = _parse_recipients(todo.recipient_email)
                if not recipients:
                    # 没有配置收件邮箱则跳过自动发送
                    continue

                subject = f"【到期提醒】{todo.title}"
                desc = (todo.description or '').strip()
                due = todo.due_date.strftime('%Y-%m-%d %H:%M') if todo.due_date else '未设置'
                body = (
                    f"以下待办已到期：\n\n"
                    f"标题：{todo.title}\n"
                    f"描述：{desc}\n"
                    f"类型：{todo.category or '未分类'}\n"
                    f"优先级：{todo.priority}\n"
                    f"截止时间：{due}\n\n"
                    f"此邮件由系统自动发送，请勿回复。"
                )

                sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
                try:
                    msg = Message(subject=subject, sender=sender, recipients=recipients, body=body)
                    mail.send(msg)
                    # 标记已发送
                    if hasattr(todo, 'email_reminder_sent'):
                        todo.email_reminder_sent = True
                    if hasattr(todo, 'email_sent_at'):
                        todo.email_sent_at = datetime.utcnow()
                    db.session.commit()
                    sent_count += 1
                except Exception as e:
                    current_app.logger.error(f"发送到期提醒失败 todo_id={todo.id}: {e}")
                    db.session.rollback()
            if sent_count:
                current_app.logger.info(f"到期提醒邮件发送完成，数量: {sent_count}")
        except Exception as e:
            current_app.logger.error(f"定时任务执行失败: {e}")


# 定时任务的注册将在 exts.init_exts(app) 中完成，以确保有应用上下文

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
                'recipient_email': todo.recipient_email,
                'send_email': todo.send_email,
                'created_at': todo.created_at.isoformat(),
                'updated_at': todo.updated_at.isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500