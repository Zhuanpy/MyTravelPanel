# 任务分配功能优化方案

## 📋 需求分析

### 核心需求
1. **任务分配功能**：2级员工或管理员可以将任务分配给指定员工
2. **员工选择功能**：提供员工列表供选择
3. **完成统计**：显示谁完成了任务，统计每个员工的任务完成情况
4. **任务追踪**：清晰显示任务的分配者和执行者

---

## 🎯 优化方案

### 方案一：基础任务分配（已实现后端）

#### 功能点
- ✅ 任务分配API（后端已实现）
- ⚠️ 员工选择下拉框（前端待实现）
- ⚠️ 任务分配按钮（前端待实现）
- ⚠️ 分配信息显示（前端待实现）

### 方案二：增强功能（推荐实现）

#### 1. 任务完成记录
- 记录任务完成者（`completed_by`字段）
- 记录完成时间（`completed_at`字段）
- 区分创建者、分配者、执行者

#### 2. 任务统计增强
- 按员工统计：待处理、已完成、已逾期
- 完成率统计：每个员工的任务完成率
- 工作量统计：按时间段统计任务量
- 完成时间分析：平均完成时间

#### 3. 任务状态流转
- 待分配 → 已分配 → 进行中 → 已完成
- 状态变更记录
- 状态变更通知

---

## 🔧 实现步骤

### 第一步：添加任务完成记录字段（数据库）

```sql
-- 添加完成记录字段
ALTER TABLE todos 
ADD COLUMN completed_by INT NULL COMMENT '完成者用户ID',
ADD COLUMN completed_at DATETIME NULL COMMENT '完成时间';

-- 添加外键约束
ALTER TABLE todos 
ADD CONSTRAINT fk_todos_completed_by 
FOREIGN KEY (completed_by) REFERENCES auth_users(id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- 添加索引
CREATE INDEX idx_todos_completed_by ON todos(completed_by);
```

### 第二步：创建获取员工列表API

```python
@utils_blue.route('/todos/staff-list')
@login_required
@staff_only
def get_staff_list():
    """获取员工列表（用于任务分配）"""
    from App_new.auth.models.auth import AuthUser, Role
    
    # 获取所有员工和管理员
    staff_role = Role.query.filter_by(name='staff').first()
    admin_role = Role.query.filter_by(name='admin').first()
    
    staff_users = AuthUser.query.filter(
        AuthUser.role_id.in_([staff_role.id, admin_role.id] if admin_role else [staff_role.id]),
        AuthUser.is_active == True
    ).all()
    
    staff_list = []
    for user in staff_users:
        staff_level = 1
        if user.profile:
            staff_level = user.profile.staff_level or 1
        
        staff_list.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'staff_level': staff_level,
            'display_name': f"{user.profile.first_name} {user.profile.last_name}".strip() if user.profile else user.username
        })
    
    return jsonify({
        'success': True,
        'staff': staff_list
    })
```

### 第三步：更新任务完成逻辑

在任务标记为完成时，记录完成者信息。

### 第四步：前端界面增强

1. 添加员工选择下拉框
2. 添加任务分配按钮
3. 显示分配信息和完成信息
4. 添加任务统计面板

---

## 📊 数据库字段说明

### 新增字段（任务完成记录）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `completed_by` | INT | 完成者用户ID |
| `completed_at` | DATETIME | 完成时间 |

### 现有字段（任务分配）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `assigned_to` | INT | 分配给的用户ID |
| `assigned_by` | INT | 分配者用户ID |
| `assigned_at` | DATETIME | 分配时间 |
| `user_id` | INT | 创建者用户ID |

---

## 🎨 界面设计建议

### 任务列表表格新增列

1. **分配给**：显示被分配员工的姓名
2. **完成者**：显示完成任务的员工姓名
3. **来源**：显示任务来源（签证/项目/手动）

### 任务操作按钮

- **分配任务**（仅2级员工可见）
- **查看详情**
- **编辑**
- **删除**

### 任务统计面板

显示：
- 总任务数
- 我的任务（待处理/已完成）
- 我分配的任务
- 按员工统计的任务量
- 完成率统计

---

## 📝 详细实现代码

见后续实现步骤。

