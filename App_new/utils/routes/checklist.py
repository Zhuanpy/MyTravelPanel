"""
任务清单路由
用于管理重复任务清单和任务模板
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from App_new.exts import db
from App_new.shared.models.Utilsmodels import TodoChecklist, TodoChecklistItem, Todo
from datetime import datetime, timedelta

checklist_bp = Blueprint('checklist', __name__, url_prefix='/utils/checklists')

@checklist_bp.route('/')
@login_required
def index():
    """任务清单管理页面"""
    return render_template('shared/utils/checklist_list.html')


@checklist_bp.route('/list', methods=['GET'])
@login_required
def list_checklists():
    """获取所有任务清单"""
    try:
        checklists = TodoChecklist.query.filter_by(user_id=current_user.id).order_by(TodoChecklist.created_at.desc()).all()
        return jsonify({
            'success': True,
            'checklists': [checklist.to_dict() for checklist in checklists]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取清单失败: {str(e)}'
        }), 500


@checklist_bp.route('/get/<int:checklist_id>', methods=['GET'])
@login_required
def get_checklist(checklist_id):
    """获取单个任务清单详情"""
    try:
        checklist = TodoChecklist.query.get_or_404(checklist_id)
        
        # 检查权限
        if checklist.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '无权访问该清单'
            }), 403
        
        return jsonify({
            'success': True,
            'checklist': checklist.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取清单失败: {str(e)}'
        }), 500


@checklist_bp.route('/create', methods=['POST'])
@login_required
def create_checklist():
    """创建任务清单"""
    try:
        data = request.get_json()
        
        # 创建清单
        checklist = TodoChecklist(
            name=data.get('name'),
            description=data.get('description'),
            category=data.get('category', '公司日常'),
            is_recurring=data.get('is_recurring', False),
            recurrence_type=data.get('recurrence_type'),
            recurrence_days=data.get('recurrence_days'),
            recurrence_time=data.get('recurrence_time'),
            user_id=current_user.id
        )
        db.session.add(checklist)
        db.session.flush()  # 获取checklist的ID
        
        # 添加清单项
        items_data = data.get('items', [])
        for index, item_data in enumerate(items_data):
            item = TodoChecklistItem(
                checklist_id=checklist.id,
                title=item_data.get('title'),
                description=item_data.get('description'),
                priority=item_data.get('priority', 2),
                order_index=index,
                assigned_to=item_data.get('assigned_to'),
                due_days_offset=item_data.get('due_days_offset', 0)
            )
            db.session.add(item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '清单创建成功',
            'checklist': checklist.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'创建清单失败: {str(e)}'
        }), 500


@checklist_bp.route('/update', methods=['POST'])
@login_required
def update_checklist():
    """更新任务清单"""
    try:
        data = request.get_json()
        checklist_id = data.get('id')
        
        checklist = TodoChecklist.query.get_or_404(checklist_id)
        
        # 检查权限
        if checklist.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '无权修改该清单'
            }), 403
        
        # 更新清单信息
        checklist.name = data.get('name', checklist.name)
        checklist.description = data.get('description', checklist.description)
        checklist.category = data.get('category', checklist.category)
        checklist.is_recurring = data.get('is_recurring', checklist.is_recurring)
        checklist.recurrence_type = data.get('recurrence_type', checklist.recurrence_type)
        checklist.recurrence_days = data.get('recurrence_days', checklist.recurrence_days)
        checklist.recurrence_time = data.get('recurrence_time', checklist.recurrence_time)
        checklist.is_active = data.get('is_active', checklist.is_active)
        checklist.updated_at = datetime.utcnow()
        
        # 更新清单项
        if 'items' in data:
            # 删除旧的清单项
            TodoChecklistItem.query.filter_by(checklist_id=checklist.id).delete()
            
            # 添加新的清单项
            items_data = data.get('items', [])
            for index, item_data in enumerate(items_data):
                item = TodoChecklistItem(
                    checklist_id=checklist.id,
                    title=item_data.get('title'),
                    description=item_data.get('description'),
                    priority=item_data.get('priority', 2),
                    order_index=index,
                    assigned_to=item_data.get('assigned_to'),
                    due_days_offset=item_data.get('due_days_offset', 0)
                )
                db.session.add(item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '清单更新成功',
            'checklist': checklist.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新清单失败: {str(e)}'
        }), 500


@checklist_bp.route('/delete', methods=['POST'])
@login_required
def delete_checklist():
    """删除任务清单"""
    try:
        data = request.get_json()
        checklist_id = data.get('id')
        
        checklist = TodoChecklist.query.get_or_404(checklist_id)
        
        # 检查权限
        if checklist.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '无权删除该清单'
            }), 403
        
        db.session.delete(checklist)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '清单删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除清单失败: {str(e)}'
        }), 500


@checklist_bp.route('/generate_todos', methods=['POST'])
@login_required
def generate_todos():
    """从清单生成待办事项"""
    try:
        data = request.get_json()
        checklist_id = data.get('checklist_id')
        due_date_str = data.get('due_date')  # 可选的基准截止日期

        checklist = TodoChecklist.query.get_or_404(checklist_id)

        # 检查权限
        if checklist.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '无权使用该清单'
            }), 403

        # 解析基准截止日期，如果没有指定则使用当前时间
        base_date = datetime.now()
        if due_date_str:
            try:
                base_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            except:
                pass

        # 生成待办事项
        generated_count = 0
        assigned_users = set()

        for item in checklist.items.order_by(TodoChecklistItem.order_index).all():
            # 计算截止日期：基准日期 + 偏移天数
            item_due_date = None
            if item.due_days_offset:
                item_due_date = base_date + timedelta(days=item.due_days_offset)
            elif checklist.default_due_days:
                item_due_date = base_date + timedelta(days=checklist.default_due_days)

            # 确定分配给谁
            assigned_to = item.assigned_to
            assigned_by = current_user.id if assigned_to else None
            assigned_at = datetime.utcnow() if assigned_to else None

            if assigned_to:
                assigned_users.add(item.assignee.username if item.assignee else str(assigned_to))

            todo = Todo(
                title=item.title,
                description=item.description,
                priority=item.priority,
                category=checklist.category,
                due_date=item_due_date,
                user_id=current_user.id,
                is_completed=False,
                assigned_to=assigned_to,
                assigned_by=assigned_by,
                assigned_at=assigned_at,
                source_type='checklist',
                source_id=checklist.id
            )
            db.session.add(todo)
            generated_count += 1

        # 更新最后生成时间
        checklist.last_generated_at = datetime.utcnow()

        db.session.commit()

        # 构建返回消息
        message = f'成功生成 {generated_count} 个待办事项'
        if assigned_users:
            message += f'，已分配给: {", ".join(assigned_users)}'

        return jsonify({
            'success': True,
            'message': message,
            'count': generated_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'生成待办事项失败: {str(e)}'
        }), 500


@checklist_bp.route('/toggle_active', methods=['POST'])
@login_required
def toggle_active():
    """切换清单的启用状态"""
    try:
        data = request.get_json()
        checklist_id = data.get('id')
        
        checklist = TodoChecklist.query.get_or_404(checklist_id)
        
        # 检查权限
        if checklist.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '无权修改该清单'
            }), 403
        
        checklist.is_active = not checklist.is_active
        checklist.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'清单已{"启用" if checklist.is_active else "禁用"}',
            'is_active': checklist.is_active
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500











