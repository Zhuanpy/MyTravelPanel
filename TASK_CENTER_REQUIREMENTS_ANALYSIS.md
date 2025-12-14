# 任务中心需求分析与实现方案

## 📋 需求概述

任务中心主要实现两个核心功能：
1. **任务提醒**：自动从业务事件（签证、项目等）生成到期提醒
2. **任务分配**：支持将任务分配给员工，方便统计任务量和分配工作

---

## 🔍 现有功能分析

### 当前已实现的功能

#### 1. 基础任务管理
- ✅ Todo模型（`App_new/shared/models/Utilsmodels.py`）
  - 支持创建、更新、删除待办事项
  - 支持优先级、分类、截止日期
  - 支持任务完成状态
  - 支持关联用户（`user_id`）

#### 2. 邮件提醒功能
- ✅ 邮件提醒字段（`recipient_email`, `send_email`, `email_reminder_sent`）
- ✅ 手动发送提醒邮件接口（`/utils/todos/send_reminder`）
- ✅ 定时任务自动发送到期提醒（`send_due_todo_reminders()`）

#### 3. 权限控制
- ✅ 根据员工等级过滤任务（1级员工只能看到自己的任务）
- ✅ 2级员工可以看到所有任务

#### 4. 业务集成
- ✅ 签证项目详情页可以创建提醒（`visa_project_detail.html`）

---

## ❌ 缺失的功能

### 1. 自动任务提醒生成
- ❌ 无法自动从业务数据（签证、项目）生成提醒任务
- ❌ 没有到期日期的自动检测机制
- ❌ 没有提前提醒功能（如提前3天、7天提醒）

### 2. 任务分配功能
- ❌ 缺少明确的"分配给"字段（当前只有`user_id`创建者）
- ❌ 无法查看分配给自己的任务
- ❌ 缺少任务统计功能（按员工统计任务量）
- ❌ 缺少任务分配历史记录

### 3. 任务关联业务数据
- ❌ 任务与业务数据（签证、项目）的关联不够明确
- ❌ 缺少从业务数据跳转到任务的链接
- ❌ 缺少从任务跳转到业务数据的链接

---

## 🎯 实现方案

### 方案一：任务提醒功能增强

#### 1.1 数据库模型扩展

**需要添加的字段：**
```python
# 在Todo模型中添加
assigned_to = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='分配给的用户ID')
source_type = db.Column(db.String(50), nullable=True, comment='来源类型: visa, project, manual')
source_id = db.Column(db.Integer, nullable=True, comment='来源业务数据ID')
reminder_days_before = db.Column(db.Integer, default=0, comment='提前提醒天数')
auto_generated = db.Column(db.Boolean, default=False, comment='是否自动生成')
```

#### 1.2 自动提醒生成服务

**创建服务类：`App_new/shared/services/task_reminder_service.py`**

```python
class TaskReminderService:
    """任务提醒服务类"""
    
    def generate_visa_reminders(self):
        """从签证项目生成提醒任务"""
        # 1. 查询即将到期的签证项目
        # 2. 检查是否已存在提醒任务
        # 3. 自动创建提醒任务
        
    def generate_project_reminders(self):
        """从项目生成提醒任务"""
        # 1. 查询即将到期的项目
        # 2. 检查是否已存在提醒任务
        # 3. 自动创建提醒任务
        
    def check_and_create_reminders(self, days_ahead=7):
        """检查并创建提前提醒"""
        # 提前N天创建提醒任务
```

#### 1.3 定时任务增强

**修改：`App_new/shared/routes/tasks.py`**

```python
def auto_generate_reminders():
    """自动生成业务数据提醒任务"""
    with current_app.app_context():
        service = TaskReminderService()
        # 每天运行一次，检查未来7天内的到期事件
        service.check_and_create_reminders(days_ahead=7)
```

---

### 方案二：任务分配功能实现

#### 2.1 数据库模型修改

**在Todo模型中添加：**
```python
assigned_to = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='分配给的用户ID')
assigned_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='分配者用户ID')
assigned_at = db.Column(db.DateTime, nullable=True, comment='分配时间')
```

#### 2.2 任务分配API

**新增接口：`/utils/todos/assign`**
```python
@utils_blue.route('/todos/assign', methods=['POST'])
@login_required
@staff_only
def assign_todo():
    """分配任务给员工"""
    # 1. 验证权限（只有2级员工或管理员可以分配任务）
    # 2. 更新任务的assigned_to字段
    # 3. 记录分配历史
```

#### 2.3 任务统计功能

**新增接口：`/utils/todos/statistics`**
```python
@utils_blue.route('/todos/statistics')
@login_required
@staff_only
def todo_statistics():
    """获取任务统计信息"""
    # 返回：
    # - 总任务数
    # - 待处理任务数
    # - 已完成任务数
    # - 按员工统计的任务量
    # - 按分类统计的任务数
```

#### 2.4 前端界面增强

**修改：`App_new/templates/shared/utils/todo_list.html`**

1. 添加"分配任务"按钮（仅2级员工可见）
2. 添加"我的任务"筛选选项
3. 添加任务统计面板
4. 显示任务分配信息

---

### 方案三：业务数据关联

#### 3.1 任务详情显示

**在任务列表中显示：**
- 来源类型（签证/项目/手动）
- 来源数据链接（点击跳转到业务详情页）

#### 3.2 业务详情页集成

**在签证/项目详情页：**
- 显示相关任务列表
- 快速创建任务按钮
- 任务完成状态显示

---

## 📝 具体实现步骤

### 第一步：数据库迁移

1. 创建迁移文件添加新字段
2. 执行数据库迁移

### 第二步：后端功能实现

1. 修改Todo模型，添加新字段
2. 创建TaskReminderService服务类
3. 实现自动提醒生成逻辑
4. 添加任务分配API
5. 添加任务统计API
6. 修改现有API支持新字段

### 第三步：定时任务配置

1. 配置自动生成提醒的定时任务（每天运行）
2. 保持现有的到期提醒发送任务

### 第四步：前端界面更新

1. 更新任务列表页面，显示分配信息
2. 添加任务分配功能
3. 添加任务统计面板
4. 添加"我的任务"筛选

### 第五步：业务数据集成

1. 在签证项目详情页显示相关任务
2. 在项目详情页显示相关任务
3. 添加快速创建任务功能

---

## 🔧 代码修改清单

### 需要修改的文件

1. **模型文件**
   - `App_new/shared/models/Utilsmodels.py` - 添加新字段

2. **路由文件**
   - `App_new/shared/routes/tasks.py` - 添加新接口

3. **服务文件（新建）**
   - `App_new/shared/services/task_reminder_service.py` - 提醒服务

4. **模板文件**
   - `App_new/templates/shared/utils/todo_list.html` - 更新界面

5. **JavaScript文件**
   - `App_new/static/js/todo_list.js` - 更新前端逻辑

6. **定时任务配置**
   - `App_new/exts.py` 或 `App_new/utils/scheduler.py` - 配置定时任务

---

## 📊 数据库表结构变更

### todos表新增字段

```sql
ALTER TABLE todos 
ADD COLUMN assigned_to INTEGER REFERENCES auth_users(id),
ADD COLUMN assigned_by INTEGER REFERENCES auth_users(id),
ADD COLUMN assigned_at DATETIME,
ADD COLUMN source_type VARCHAR(50),
ADD COLUMN source_id INTEGER,
ADD COLUMN reminder_days_before INTEGER DEFAULT 0,
ADD COLUMN auto_generated BOOLEAN DEFAULT FALSE;

-- 添加索引
CREATE INDEX idx_todos_assigned_to ON todos(assigned_to);
CREATE INDEX idx_todos_source ON todos(source_type, source_id);
```

---

## 🎨 前端界面设计建议

### 任务列表页面增强

1. **筛选栏新增**
   - "我的任务"筛选（显示分配给当前用户的任务）
   - "我创建的"筛选（显示当前用户创建的任务）
   - "我分配的"筛选（显示当前用户分配的任务，仅2级员工）

2. **任务卡片显示**
   - 显示"分配给：XXX"
   - 显示"来源：签证项目 #123"（可点击跳转）
   - 显示"提前提醒：3天前"

3. **操作按钮**
   - "分配任务"按钮（仅2级员工可见）
   - "查看来源"按钮（如果有source_type和source_id）

### 任务统计面板

显示：
- 总任务数
- 待处理任务数
- 已完成任务数
- 已逾期任务数
- 按员工统计的任务量（饼图或列表）
- 按分类统计的任务数

---

## ⚙️ 定时任务配置

### 需要配置的定时任务

1. **自动生成提醒任务**（每天凌晨2点运行）
   - 扫描未来7天内的到期事件
   - 自动创建提醒任务

2. **发送到期提醒邮件**（每小时运行）
   - 扫描到期的任务
   - 发送提醒邮件

---

## 🔐 权限控制

### 任务分配权限

- **1级员工**：
  - 可以创建任务
  - 只能看到分配给自己的任务和自己创建的任务
  - 不能分配任务给其他人

- **2级员工**：
  - 可以创建任务
  - 可以看到所有任务
  - 可以分配任务给任何员工
  - 可以查看任务统计

- **管理员**：
  - 拥有所有权限
  - 可以管理所有任务

---

## 📈 后续扩展建议

1. **任务模板**：支持创建任务模板，快速生成重复任务
2. **任务评论**：支持在任务中添加评论和附件
3. **任务依赖**：支持设置任务之间的依赖关系
4. **任务提醒规则**：支持自定义提醒规则（如提前N天提醒）
5. **任务报表**：生成任务完成情况报表
6. **移动端支持**：优化移动端显示和操作

---

## 🚀 实施优先级

### 高优先级（必须实现）
1. ✅ 添加任务分配字段和功能
2. ✅ 实现任务统计功能
3. ✅ 添加"我的任务"筛选

### 中优先级（建议实现）
1. ⚠️ 自动从业务数据生成提醒任务
2. ⚠️ 任务与业务数据的关联显示
3. ⚠️ 提前提醒功能

### 低优先级（可选实现）
1. ⚪ 任务分配历史记录
2. ⚪ 任务评论功能
3. ⚪ 任务模板功能

---

## 📌 注意事项

1. **数据迁移**：修改数据库结构前需要备份数据
2. **向后兼容**：确保现有功能不受影响
3. **性能优化**：大量任务时需要考虑查询性能
4. **邮件配置**：确保邮件服务正常配置
5. **定时任务**：确保定时任务服务正常运行

