# 任务中心实现指南

## 📝 实现步骤详解

### 第一步：数据库迁移

创建迁移文件：`migrations/add_task_assignment_fields.sql`

```sql
-- 添加任务分配相关字段
ALTER TABLE todos 
ADD COLUMN assigned_to INTEGER REFERENCES auth_users(id),
ADD COLUMN assigned_by INTEGER REFERENCES auth_users(id),
ADD COLUMN assigned_at DATETIME,
ADD COLUMN source_type VARCHAR(50),
ADD COLUMN source_id INTEGER,
ADD COLUMN reminder_days_before INTEGER DEFAULT 0,
ADD COLUMN auto_generated BOOLEAN DEFAULT FALSE;

-- 添加索引提高查询性能
CREATE INDEX IF NOT EXISTS idx_todos_assigned_to ON todos(assigned_to);
CREATE INDEX IF NOT EXISTS idx_todos_source ON todos(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id);
```

---

### 第二步：修改Todo模型

**文件：`App_new/shared/models/Utilsmodels.py`**

在Todo类中添加新字段：

```python
class Todo(db.Model):
    """待办事项模型"""
    __tablename__ = 'todos'

    # ... 现有字段 ...
    
    # 新增字段
    assigned_to = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='分配给的用户ID')
    assigned_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='分配者用户ID')
    assigned_at = db.Column(db.DateTime, nullable=True, comment='分配时间')
    source_type = db.Column(db.String(50), nullable=True, comment='来源类型: visa, project, manual')
    source_id = db.Column(db.Integer, nullable=True, comment='来源业务数据ID')
    reminder_days_before = db.Column(db.Integer, default=0, comment='提前提醒天数')
    auto_generated = db.Column(db.Boolean, default=False, comment='是否自动生成')
    
    # 关系
    assignee = db.relationship('AuthUser', foreign_keys=[assigned_to], backref='assigned_todos')
    assigner = db.relationship('AuthUser', foreign_keys=[assigned_by], backref='assigned_todos_by_me')
    
    def to_dict(self):
        """将模型转换为字典"""
        result = {
            # ... 现有字段 ...
            'assigned_to': self.assigned_to,
            'assigned_by': self.assigned_by,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'reminder_days_before': self.reminder_days_before,
            'auto_generated': self.auto_generated,
            'assignee_name': self.assignee.username if self.assignee else None,
            'assigner_name': self.assigner.username if self.assigner else None,
        }
        return result
```

---

### 第三步：创建任务提醒服务

**新建文件：`App_new/shared/services/task_reminder_service.py`**

```python
# -*- coding: utf-8 -*-
"""
任务提醒服务
自动从业务数据生成提醒任务
"""

from App_new.exts import db
from App_new.shared.models.Utilsmodels import Todo
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from datetime import datetime, timedelta
from flask import current_app


class TaskReminderService:
    """任务提醒服务类"""
    
    def generate_visa_reminders(self, days_ahead=7):
        """
        从签证项目生成提醒任务
        days_ahead: 提前多少天创建提醒
        """
        try:
            # 这里需要根据实际的签证项目模型来查询
            # 假设签证项目有expiry_date或due_date字段
            from App_new.business.visa.models.visa import VisaProject  # 根据实际路径调整
            
            today = datetime.now().date()
            target_date = today + timedelta(days=days_ahead)
            
            # 查询即将到期的签证项目
            visa_projects = VisaProject.query.filter(
                VisaProject.expiry_date >= today,
                VisaProject.expiry_date <= target_date,
                VisaProject.status != 'completed'
            ).all()
            
            created_count = 0
            for project in visa_projects:
                # 检查是否已存在提醒任务
                existing = Todo.query.filter_by(
                    source_type='visa',
                    source_id=project.id,
                    is_completed=False
                ).first()
                
                if not existing:
                    # 创建提醒任务
                    todo = Todo.create(
                        title=f'[签证提醒] {project.applicant_name} - {project.visa_type}',
                        description=f'项目ID: {project.id}\n签证类型: {project.visa_type}\n申请人: {project.applicant_name}\n到期日期: {project.expiry_date}',
                        category='visa_reminder',
                        priority=1,  # 高优先级
                        due_date=datetime.combine(project.expiry_date, datetime.min.time()),
                        source_type='visa',
                        source_id=project.id,
                        reminder_days_before=days_ahead,
                        auto_generated=True,
                        user_id=None  # 可以设置为项目负责人
                    )
                    created_count += 1
                    current_app.logger.info(f'创建签证提醒任务: {todo.id}')
            
            return created_count
            
        except Exception as e:
            current_app.logger.error(f'生成签证提醒失败: {str(e)}')
            return 0
    
    def generate_project_reminders(self, days_ahead=7):
        """
        从项目生成提醒任务
        """
        try:
            today = datetime.now().date()
            target_date = today + timedelta(days=days_ahead)
            
            # 查询即将到期的项目
            projects = ProjectHeader.query.filter(
                ProjectHeader.due_date >= today,
                ProjectHeader.due_date <= target_date,
                ProjectHeader.status != 'completed'
            ).all()
            
            created_count = 0
            for project in projects:
                # 检查是否已存在提醒任务
                existing = Todo.query.filter_by(
                    source_type='project',
                    source_id=project.id,
                    is_completed=False
                ).first()
                
                if not existing:
                    # 创建提醒任务
                    todo = Todo.create(
                        title=f'[项目提醒] {project.project_name or f"项目#{project.id}"}',
                        description=f'项目ID: {project.id}\n项目名称: {project.project_name}\n到期日期: {project.due_date}',
                        category='project_reminder',
                        priority=2,  # 中优先级
                        due_date=datetime.combine(project.due_date, datetime.min.time()),
                        source_type='project',
                        source_id=project.id,
                        reminder_days_before=days_ahead,
                        auto_generated=True,
                        user_id=project.staff_id  # 分配给项目负责人
                    )
                    created_count += 1
                    current_app.logger.info(f'创建项目提醒任务: {todo.id}')
            
            return created_count
            
        except Exception as e:
            current_app.logger.error(f'生成项目提醒失败: {str(e)}')
            return 0
    
    def check_and_create_reminders(self, days_ahead=7):
        """
        检查并创建所有类型的提醒任务
        """
        visa_count = self.generate_visa_reminders(days_ahead)
        project_count = self.generate_project_reminders(days_ahead)
        
        current_app.logger.info(f'自动生成提醒任务完成: 签证{visa_count}个, 项目{project_count}个')
        return visa_count + project_count
```

---

### 第四步：添加任务分配API

**修改文件：`App_new/shared/routes/tasks.py`**

在文件末尾添加：

```python
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
        
        if not todo_id or not assigned_to_id:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
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
        from App_new.auth.models.auth import AuthUser
        from sqlalchemy import func
        
        # 基础统计
        total_todos = Todo.query.count()
        pending_todos = Todo.query.filter_by(is_completed=False).count()
        completed_todos = Todo.query.filter_by(is_completed=True).count()
        
        # 已逾期任务
        overdue_todos = Todo.query.filter(
            Todo.due_date < datetime.utcnow(),
            Todo.is_completed == False
        ).count()
        
        # 按员工统计任务量
        staff_stats = db.session.query(
            AuthUser.username,
            func.count(Todo.id).label('task_count')
        ).join(
            Todo, AuthUser.id == Todo.assigned_to
        ).filter(
            Todo.is_completed == False
        ).group_by(
            AuthUser.id, AuthUser.username
        ).all()
        
        staff_task_counts = {username: count for username, count in staff_stats}
        
        # 按分类统计
        category_stats = db.session.query(
            Todo.category,
            func.count(Todo.id).label('count')
        ).filter(
            Todo.is_completed == False
        ).group_by(Todo.category).all()
        
        category_counts = {category or '未分类': count for category, count in category_stats}
        
        # 我的任务统计
        my_tasks = Todo.query.filter_by(assigned_to=current_user.id, is_completed=False).count()
        my_completed = Todo.query.filter_by(assigned_to=current_user.id, is_completed=True).count()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total': total_todos,
                'pending': pending_todos,
                'completed': completed_todos,
                'overdue': overdue_todos,
                'my_tasks': my_tasks,
                'my_completed': my_completed,
                'staff_task_counts': staff_task_counts,
                'category_counts': category_counts
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取任务统计失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取统计失败: {str(e)}'
        }), 500


# 修改list_todos接口，支持新的筛选条件
# 在list_todos函数中添加：
def list_todos():
    try:
        # ... 现有代码 ...
        
        # 新增筛选条件
        assigned_to = request.args.get('assigned_to', '')
        assigned_to_me = request.args.get('assigned_to_me', '')  # 'true'表示只显示分配给我的
        source_type = request.args.get('source_type', '')
        
        # 应用新的过滤条件
        if assigned_to_me == 'true':
            query = query.filter(Todo.assigned_to == current_user.id)
        elif assigned_to:
            query = query.filter(Todo.assigned_to == int(assigned_to))
        
        if source_type:
            query = query.filter(Todo.source_type == source_type)
        
        # ... 其余代码保持不变 ...
```

---

### 第五步：配置定时任务

**修改文件：`App_new/exts.py` 或 `App_new/utils/scheduler.py`**

```python
from App_new.shared.services.task_reminder_service import TaskReminderService

def init_scheduler(app):
    """初始化定时任务"""
    # ... 现有定时任务 ...
    
    # 添加自动生成提醒任务的定时任务（每天凌晨2点运行）
    @scheduler.task('cron', hour=2, minute=0)
    def auto_generate_reminders():
        """自动生成业务数据提醒任务"""
        with app.app_context():
            service = TaskReminderService()
            service.check_and_create_reminders(days_ahead=7)
            current_app.logger.info('自动生成提醒任务完成')
```

---

### 第六步：前端界面更新

**修改文件：`App_new/templates/shared/utils/todo_list.html`**

在筛选栏添加：

```html
<!-- 新增筛选选项 -->
<div class="visa-filter-item">
    <label>任务筛选：</label>
    <select id="taskFilter" class="visa-form-select">
        <option value="">全部任务</option>
        <option value="assigned_to_me">我的任务</option>
        <option value="created_by_me">我创建的</option>
        <option value="assigned_by_me">我分配的</option>
    </select>
</div>

<div class="visa-filter-item">
    <label>来源类型：</label>
    <select id="sourceTypeFilter" class="visa-form-select">
        <option value="">全部</option>
        <option value="visa">签证</option>
        <option value="project">项目</option>
        <option value="manual">手动创建</option>
    </select>
</div>
```

在任务列表中添加分配信息显示和操作按钮。

---

## 🎯 快速开始

### 1. 执行数据库迁移
```bash
# 运行SQL脚本
mysql -u username -p database_name < migrations/add_task_assignment_fields.sql
```

### 2. 修改代码文件
按照上述步骤修改相应的文件

### 3. 重启应用
重启Flask应用使更改生效

### 4. 测试功能
- 测试任务分配功能
- 测试任务统计功能
- 测试自动生成提醒任务

---

## 📌 注意事项

1. **数据库备份**：修改前务必备份数据库
2. **字段默认值**：新字段需要设置合理的默认值
3. **权限检查**：确保权限检查逻辑正确
4. **性能优化**：大量任务时考虑添加缓存
5. **错误处理**：确保所有异常都有适当的处理

