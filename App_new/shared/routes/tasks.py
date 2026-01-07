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
                # 1级员工只能看到自己创建的或分配给自己的待办事项
                from sqlalchemy import or_
                query = query.filter(
                    or_(
                        Todo.user_id == current_user.id,
                        Todo.assigned_to == current_user.id
                    )
                )
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
        
        # 新增筛选条件
        assigned_to_me = request.args.get('assigned_to_me', '')
        assigned_to = request.args.get('assigned_to', '')
        assigned_by_me = request.args.get('assigned_by_me', '')
        source_type = request.args.get('source_type', '')
        created_by_me = request.args.get('created_by_me', '')
        my_tasks = request.args.get('my_tasks', '')

        # 我的任务筛选（显示分配给我的 + 我创建的未分配任务）
        if my_tasks == 'true':
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Todo.assigned_to == current_user.id,  # 分配给我的
                    (Todo.user_id == current_user.id) & (Todo.assigned_to.is_(None))  # 我创建的且未分配的
                )
            )
        elif assigned_to_me == 'true':
            query = query.filter(Todo.assigned_to == current_user.id)
        elif assigned_to:
            # 指定用户的任务
            query = query.filter(Todo.assigned_to == int(assigned_to))
        
        # 我分配的任务筛选（显示当前用户分配的任务）
        if assigned_by_me == 'true':
            query = query.filter(Todo.assigned_by == current_user.id)
        
        # 我创建的任务筛选
        if created_by_me == 'true':
            query = query.filter(Todo.user_id == current_user.id)
        
        # 来源类型筛选
        if source_type:
            query = query.filter(Todo.source_type == source_type)
            
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
        
        # 获取任务分配信息
        assigned_to = data.get('assigned_to')
        if assigned_to:
            assigned_to = int(assigned_to) if assigned_to else None
        
        todo = Todo.create(
            title=data.get('title'),
            description=data.get('description'),
            priority=int(data.get('priority', 2)),
            due_date=due_date,
            category=data.get('category'),
            user_id=current_user.id,  # 关联到当前登录用户
            recipient_email=data.get('recipient_email'),
            send_email=bool(data.get('send_email', False)),
            assigned_to=assigned_to,
            assigned_by=current_user.id if assigned_to else None,
            assigned_at=datetime.utcnow() if assigned_to else None,
            source_type=data.get('source_type'),
            source_id=data.get('source_id'),
            reminder_days_before=int(data.get('reminder_days_before', 0)),
            auto_generated=bool(data.get('auto_generated', False)),
            estimated_hours=float(data.get('estimated_hours', 0) or 0),
            actual_hours=float(data.get('actual_hours', 0) or 0)
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

        # 处理任务分配
        assigned_to = data.get('assigned_to')
        assigned_by = None
        assigned_at = None
        
        if assigned_to is not None:
            assigned_to = int(assigned_to) if assigned_to else None
            # 如果分配了任务，记录分配信息
            if assigned_to:
                if not todo_old.assigned_to or assigned_to != todo_old.assigned_to:
                    # 新分配或重新分配任务
                    assigned_by = current_user.id
                    assigned_at = datetime.utcnow()
                else:
                    # 保持原有分配信息
                    assigned_by = todo_old.assigned_by
                    assigned_at = todo_old.assigned_at
            else:
                # 取消分配
                assigned_by = None
                assigned_at = None
        
        # 处理任务完成记录
        is_completed = data.get('is_completed', False)
        completed_by = None
        completed_at = None
        is_on_time = None
        delay_days = 0

        # 如果任务状态从未完成变为已完成，记录完成者并计算准时性
        if is_completed and not todo_old.is_completed:
            # 任务被标记为完成，记录完成者
            # 优先使用被分配者，如果没有分配则使用当前用户
            completed_by = assigned_to if assigned_to else current_user.id
            completed_at = datetime.utcnow()

            # 计算准时性
            if due_date:
                if completed_at <= due_date:
                    is_on_time = True
                    delay_days = (completed_at - due_date).days  # 负数表示提前
                else:
                    is_on_time = False
                    delay_days = (completed_at - due_date).days
            else:
                # 没有截止日期，默认为准时
                is_on_time = True
                delay_days = 0
        elif not is_completed and todo_old.is_completed:
            # 任务从已完成变为未完成，清除完成记录和准时性
            completed_by = None
            completed_at = None
            is_on_time = None
            delay_days = 0
        elif is_completed and todo_old.is_completed:
            # 保持已完成状态，保留原有完成记录和准时性
            completed_by = todo_old.completed_by
            completed_at = todo_old.completed_at
            is_on_time = todo_old.is_on_time if hasattr(todo_old, 'is_on_time') else None
            delay_days = todo_old.delay_days if hasattr(todo_old, 'delay_days') else 0
        
        update_payload = {
            'title': data.get('title'),
            'description': data.get('description'),
            'priority': int(data.get('priority', 2)),
            'is_completed': is_completed,
            'due_date': due_date,
            'category': data.get('category'),
            'recipient_email': new_recipient,
            'send_email': new_send_flag,
            'source_type': data.get('source_type'),
            'source_id': data.get('source_id'),
            'reminder_days_before': int(data.get('reminder_days_before', 0)),
            'auto_generated': bool(data.get('auto_generated', False)),
            'assigned_to': assigned_to,
            'assigned_by': assigned_by,
            'assigned_at': assigned_at,
            'completed_by': completed_by,
            'completed_at': completed_at,
            'is_on_time': is_on_time,
            'delay_days': delay_days,
            'estimated_hours': float(data.get('estimated_hours', 0) or 0),
            'actual_hours': float(data.get('actual_hours', 0) or 0)
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
            'todo': todo.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# 分配任务
@utils_blue.route('/todos/assign', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def assign_todo():
    """分配任务给员工"""
    try:
        data = request.get_json()
        todo_id = data.get('todo_id')
        assigned_to_id = data.get('assigned_to')

        if not todo_id:
            return jsonify({
                'success': False,
                'message': '缺少任务ID'
            }), 400
        
        # 检查权限：只有2级员工或管理员可以分配任务
        staff_level = 1
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1
        
        is_admin = current_user.role and current_user.role.name in ['admin', 'super_admin']
        
        if staff_level < 2 and not is_admin:
            return jsonify({
                'success': False,
                'message': '您没有权限分配任务，只有2级员工或管理员可以分配任务'
            }), 403
        
        # 获取任务
        todo = Todo.query.get(todo_id)
        if not todo:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        # 如果 assigned_to_id 为空或 None，则取消分配
        if not assigned_to_id:
            todo.assigned_to = None
            todo.assigned_by = None
            todo.assigned_at = None
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '任务分配已取消',
                'todo': todo.to_dict()
            })

        # 验证被分配用户是否存在
        from App_new.auth.models.auth import AuthUser
        assignee = AuthUser.query.get(assigned_to_id)
        if not assignee:
            return jsonify({
                'success': False,
                'message': '被分配用户不存在'
            }), 404

        # 更新任务分配信息
        todo.assigned_to = assigned_to_id
        todo.assigned_by = current_user.id
        todo.assigned_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'任务已分配给 {assignee.username}',
            'todo': todo.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f'分配任务失败: {str(e)}')
        current_app.logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'分配任务失败: {str(e)}'
        }), 500


# 获取任务统计
@utils_blue.route('/todos/statistics')
@login_required
@staff_only
def todo_statistics():
    """获取任务统计信息"""
    try:
        from App_new.auth.models.auth import AuthUser, Role
        from sqlalchemy import func, or_, and_

        # 获取日期范围参数
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                # 结束日期包含当天
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except:
                pass

        # 构建基础查询（应用日期过滤）
        def apply_date_filter(query):
            if start_date:
                query = query.filter(Todo.created_at >= start_date)
            if end_date:
                query = query.filter(Todo.created_at <= end_date)
            return query

        # 基础统计
        base_query = apply_date_filter(Todo.query)
        total_todos = base_query.count()
        pending_todos = apply_date_filter(Todo.query.filter_by(is_completed=False)).count()
        completed_todos = apply_date_filter(Todo.query.filter_by(is_completed=True)).count()

        # 已逾期任务
        overdue_todos = apply_date_filter(Todo.query.filter(
            Todo.due_date < datetime.utcnow(),
            Todo.is_completed == False
        )).count()
        
        # 根据员工等级过滤统计
        base_query = Todo.query
        if current_user.role and current_user.role.name == 'staff':
            staff_level = 1
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己的任务统计
                base_query = base_query.filter(
                    (Todo.assigned_to == current_user.id) | (Todo.user_id == current_user.id)
                )
        
        # 按员工统计任务量（统计待处理任务：分配给该员工的 + 该员工创建但未分配的）
        # 获取所有员工
        staff_role = Role.query.filter_by(name='staff').first()
        admin_role = Role.query.filter_by(name='admin').first()
        role_ids = []
        if staff_role:
            role_ids.append(staff_role.id)
        if admin_role:
            role_ids.append(admin_role.id)

        all_staff = AuthUser.query.filter(AuthUser.role_id.in_(role_ids)).all() if role_ids else []

        staff_task_counts = {}
        for staff in all_staff:
            # 统计分配给该员工的任务 + 该员工创建但未分配的任务
            staff_query = Todo.query.filter(
                Todo.is_completed == False,
                or_(
                    Todo.assigned_to == staff.id,
                    and_(Todo.user_id == staff.id, Todo.assigned_to.is_(None))
                )
            )
            staff_query = apply_date_filter(staff_query)
            count = staff_query.count()
            if count > 0:
                display_name = staff.profile.get_full_name() if staff.profile else staff.username
                display_name = display_name or staff.username
                staff_task_counts[display_name] = count

        # 应用权限过滤（1级员工只能看到自己的统计）
        if current_user.role and current_user.role.name == 'staff':
            staff_level = 1
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1

            if staff_level == 1:
                my_display_name = current_user.profile.get_full_name() if current_user.profile else current_user.username
                my_display_name = my_display_name or current_user.username
                staff_task_counts = {k: v for k, v in staff_task_counts.items() if k == my_display_name}
        
        # 按分类统计
        category_query = Todo.query.filter(Todo.is_completed == False)
        if start_date:
            category_query = category_query.filter(Todo.created_at >= start_date)
        if end_date:
            category_query = category_query.filter(Todo.created_at <= end_date)

        # 应用权限过滤
        if current_user.role and current_user.role.name == 'staff':
            staff_level = 1
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1

            if staff_level == 1:
                category_query = category_query.filter(
                    (Todo.assigned_to == current_user.id) | (Todo.user_id == current_user.id)
                )

        category_stats = db.session.query(
            Todo.category,
            func.count(Todo.id).label('count')
        ).filter(Todo.id.in_([t.id for t in category_query.all()])).group_by(Todo.category).all()
        category_counts = {category or '未分类': count for category, count in category_stats}

        # 我的任务统计
        my_tasks_query = Todo.query.filter_by(assigned_to=current_user.id, is_completed=False)
        my_completed_query = Todo.query.filter_by(assigned_to=current_user.id, is_completed=True)
        my_created_query = Todo.query.filter_by(user_id=current_user.id, is_completed=False)
        my_tasks = apply_date_filter(my_tasks_query).count()
        my_completed = apply_date_filter(my_completed_query).count()
        my_created = apply_date_filter(my_created_query).count()

        # 计算准时完成率
        on_time_rate = 0
        try:
            # 查询已完成且有 is_on_time 字段的任务
            timeliness_query = Todo.query.filter(
                Todo.is_completed == True,
                Todo.is_on_time.isnot(None)
            )
            timeliness_query = apply_date_filter(timeliness_query)
            completed_with_timeliness = timeliness_query.all()

            if completed_with_timeliness:
                on_time_count = sum(1 for t in completed_with_timeliness if t.is_on_time)
                on_time_rate = round(on_time_count / len(completed_with_timeliness) * 100)
        except Exception as e:
            current_app.logger.error(f'计算准时率失败: {str(e)}')
            on_time_rate = 0

        # 计算工时统计
        total_estimated_hours = 0
        total_actual_hours = 0
        staff_hours = {}
        try:
            # 计算总预估工时和实际工时
            hours_query = apply_date_filter(Todo.query)
            all_todos_for_hours = hours_query.all()
            total_estimated_hours = sum(t.estimated_hours or 0 for t in all_todos_for_hours)
            total_actual_hours = sum(t.actual_hours or 0 for t in all_todos_for_hours)

            # 按员工统计工时（已完成任务的实际工时）
            for staff in all_staff:
                staff_hours_query = Todo.query.filter(
                    Todo.is_completed == True,
                    or_(
                        Todo.assigned_to == staff.id,
                        and_(Todo.user_id == staff.id, Todo.assigned_to.is_(None))
                    )
                )
                staff_hours_query = apply_date_filter(staff_hours_query)
                staff_todos = staff_hours_query.all()
                staff_actual = sum(t.actual_hours or 0 for t in staff_todos)
                if staff_actual > 0:
                    display_name = staff.profile.get_full_name() if staff.profile else staff.username
                    display_name = display_name or staff.username
                    staff_hours[display_name] = round(staff_actual, 1)

            # 应用权限过滤（1级员工只能看到自己的工时统计）
            if current_user.role and current_user.role.name == 'staff':
                staff_level = 1
                if current_user.profile:
                    staff_level = current_user.profile.staff_level or 1
                if staff_level == 1:
                    my_display_name = current_user.profile.get_full_name() if current_user.profile else current_user.username
                    my_display_name = my_display_name or current_user.username
                    staff_hours = {k: v for k, v in staff_hours.items() if k == my_display_name}
        except Exception as e:
            current_app.logger.error(f'计算工时统计失败: {str(e)}')

        return jsonify({
            'success': True,
            'statistics': {
                'total': total_todos,
                'pending': pending_todos,
                'completed': completed_todos,
                'overdue': overdue_todos,
                'my_tasks': my_tasks,
                'my_completed': my_completed,
                'my_created': my_created,
                'staff_task_counts': staff_task_counts,
                'category_counts': category_counts,
                'on_time_rate': on_time_rate,
                'total_estimated_hours': round(total_estimated_hours, 1),
                'total_actual_hours': round(total_actual_hours, 1),
                'staff_hours': staff_hours
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取任务统计失败: {str(e)}')
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'获取统计失败: {str(e)}'
        }), 500

# 获取员工列表（用于任务分配）
@utils_blue.route('/todos/staff-list')
@login_required
@staff_only
def get_staff_list():
    """获取员工列表（用于任务分配）"""
    try:
        from App_new.auth.models.auth import AuthUser, Role
        
        # 获取所有员工和管理员
        staff_role = Role.query.filter_by(name='staff').first()
        admin_role = Role.query.filter_by(name='admin').first()
        
        role_ids = []
        if staff_role:
            role_ids.append(staff_role.id)
        if admin_role:
            role_ids.append(admin_role.id)
        
        if not role_ids:
            return jsonify({
                'success': True,
                'staff': []
            })
        
        staff_users = AuthUser.query.filter(
            AuthUser.role_id.in_(role_ids),
            AuthUser.is_active == True
        ).all()
        
        staff_list = []
        for user in staff_users:
            staff_level = 1
            if user.profile:
                staff_level = user.profile.staff_level or 1
            
            # 获取显示名称
            display_name = user.username
            if user.profile:
                name_parts = []
                if user.profile.first_name:
                    name_parts.append(user.profile.first_name)
                if user.profile.last_name:
                    name_parts.append(user.profile.last_name)
                if name_parts:
                    display_name = ' '.join(name_parts)
            
            staff_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'staff_level': staff_level,
                'display_name': display_name,
                'role_name': user.role.name if user.role else 'unknown'
            })
        
        # 按员工等级和用户名排序
        staff_list.sort(key=lambda x: (x['staff_level'], x['display_name']))
        
        # 检查当前用户是否有分配任务权限
        staff_level = 1
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1
        
        is_admin = current_user.role and current_user.role.name in ['admin', 'super_admin']
        can_assign = (staff_level >= 2) or is_admin
        
        return jsonify({
            'success': True,
            'staff': staff_list,
            'current_user': {
                'id': current_user.id,
                'username': current_user.username,
                'staff_level': staff_level,
                'is_admin': is_admin,
                'can_assign': can_assign
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取员工列表失败: {str(e)}')
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'获取员工列表失败: {str(e)}'
        }), 500