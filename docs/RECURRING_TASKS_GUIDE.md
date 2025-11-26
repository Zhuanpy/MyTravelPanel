# 重复任务清单使用指南

## 功能简介

重复任务清单功能帮助您管理定期重复的工作任务，例如：
- 每周核对账单（UOB、OCBC、航空公司账户等）
- 每天检查邮件
- 每月生成报表
- 等等...

## 主要功能

### 1. 任务清单管理
- 创建和管理任务清单模板
- 每个清单可以包含多个相关的任务项
- 支持任务优先级设置
- 支持任务描述和分类

### 2. 重复任务设置
- **每天重复**：每天自动生成任务
- **每周重复**：可选择一周中的特定日期（如每周一、三、五）
- **每月重复**：每月第一天自动生成任务

### 3. 自动生成
- 系统按照设定的规则自动生成待办事项
- 支持启用/停用清单
- 记录最后生成时间

## 使用步骤

### 第一步：创建数据库表

在服务器和本地都需要执行以下SQL脚本：

```bash
# 方法 1: 使用 sqlite3 命令行
sqlite3 instance/travel_panel_new.db < migrations/create_todo_checklists_tables.sql

# 方法 2: 使用 Python
python -c "import sqlite3; conn = sqlite3.connect('instance/travel_panel_new.db'); conn.executescript(open('migrations/create_todo_checklists_tables.sql', encoding='utf-8').read()); conn.commit(); conn.close()"
```

### 第二步：创建任务清单

1. 访问 `/utils/checklists/` 或从待办事项页面点击"任务清单管理"
2. 点击"创建新清单"按钮
3. 填写清单信息：
   - **清单名称**：例如"每周账单核对"
   - **分类**：选择"公司日常"等
   - **描述**：说明清单用途

4. 如果需要重复任务，勾选"启用重复任务"：
   - 选择重复类型（每天/每周/每月）
   - 如果选择每周，选择具体的星期几
   - 设置生成时间（例如 09:00）

5. 添加任务项：
   - 点击"添加任务"按钮
   - 填写任务标题和描述
   - 设置优先级

6. 点击"保存"

### 第三步：设置自动生成（推荐）

#### 在 Linux 服务器上（使用 cron）

编辑 crontab：
```bash
crontab -e
```

添加以下行（每小时执行一次）：
```
0 * * * * cd /path/to/MyTravelPanel && /usr/bin/python3 scripts/generate_recurring_todos.py >> logs/recurring_tasks.log 2>&1
```

或者每天早上 8:00 执行：
```
0 8 * * * cd /path/to/MyTravelPanel && /usr/bin/python3 scripts/generate_recurring_todos.py >> logs/recurring_tasks.log 2>&1
```

#### 在 Windows 本地（使用任务计划程序）

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器（每天或每小时）
4. 操作：启动程序
   - 程序：`python`
   - 参数：`scripts/generate_recurring_todos.py`
   - 起始于：`E:\MyProject\MyTravelWork\MyTravelPanel`

### 第四步：手动生成（可选）

如果不想设置自动任务，也可以手动生成：

1. 在任务清单管理页面
2. 找到要生成的清单
3. 点击"生成待办事项"按钮
4. 系统会根据清单项创建待办事项

## 使用示例

### 示例 1：每周账单核对

**清单配置：**
- 名称：每周账单核对
- 分类：公司日常
- 重复类型：每周
- 重复日期：周一
- 生成时间：09:00

**任务项：**
1. 核对 UOB 账户 - 高优先级
2. 核对 OCBC 账户 - 高优先级
3. 核对 US AIRLINE 账户 - 中优先级
4. 核对 Indigo airline 账户 - 中优先级
5. 核对 Scoot airline 账户 - 中优先级

**结果：**
每周一早上 9:00，系统会自动生成上述 5 个待办事项

### 示例 2：每天邮件检查

**清单配置：**
- 名称：每日邮件处理
- 分类：公司日常
- 重复类型：每天
- 生成时间：09:00

**任务项：**
1. 检查并回复客户邮件 - 高优先级
2. 检查供应商邮件 - 中优先级
3. 处理内部沟通邮件 - 低优先级

## 管理清单

### 编辑清单
1. 在清单列表中找到要编辑的清单
2. 点击"编辑"按钮
3. 修改信息后保存

### 启用/停用清单
- 点击"停用"按钮：清单不会再自动生成任务
- 点击"启用"按钮：恢复自动生成

### 删除清单
1. 点击"删除"按钮
2. 确认删除
3. 清单和所有任务项将被永久删除

## 注意事项

1. **数据库同步**：
   - 如果本地和服务器共用数据库，迁移脚本只需在服务器执行一次
   - 如果是独立的数据库，需要在两边都执行

2. **重复任务逻辑**：
   - 系统每天只会生成一次任务（即使运行多次脚本）
   - 已生成的任务不会重复生成

3. **时区设置**：
   - 确保服务器时区设置正确
   - 生成时间基于服务器时间

4. **手动生成**：
   - 手动点击"生成待办事项"不受重复规则限制
   - 可以随时手动生成，不影响自动生成

## 故障排查

### 问题 1：任务没有自动生成

检查项：
1. 清单是否启用（`is_active = True`）
2. 重复任务是否开启（`is_recurring = True`）
3. cron 任务或 Windows 任务计划是否正常运行
4. 查看日志文件：`logs/recurring_tasks.log`

### 问题 2：重复生成相同任务

检查项：
1. 确认只有一个定时任务在运行
2. 检查 `last_generated_at` 字段是否正确更新

### 问题 3：权限错误

确保：
1. Python 脚本有执行权限
2. 数据库文件有写入权限
3. 日志目录存在且可写

## 技术细节

### 数据库表结构

**todo_checklists**（任务清单）
- `id`: 主键
- `name`: 清单名称
- `description`: 描述
- `category`: 分类
- `is_recurring`: 是否重复
- `recurrence_type`: 重复类型
- `recurrence_days`: 重复日期（用于weekly）
- `recurrence_time`: 生成时间
- `is_active`: 是否启用
- `last_generated_at`: 最后生成时间

**todo_checklist_items**（清单任务项）
- `id`: 主键
- `checklist_id`: 所属清单
- `title`: 任务标题
- `description`: 任务描述
- `priority`: 优先级
- `order_index`: 排序

### API 端点

- `GET /utils/checklists/` - 清单管理页面
- `GET /utils/checklists/list` - 获取清单列表
- `POST /utils/checklists/create` - 创建清单
- `POST /utils/checklists/update` - 更新清单
- `POST /utils/checklists/delete` - 删除清单
- `POST /utils/checklists/generate_todos` - 手动生成任务
- `POST /utils/checklists/toggle_active` - 切换启用状态

## 相关文件

- 模型：`App_new/shared/models/Utilsmodels.py`
- 路由：`App_new/utils/routes/checklist.py`
- 模板：`App_new/templates/shared/utils/checklist_list.html`
- 迁移：`migrations/create_todo_checklists_tables.sql`
- 脚本：`scripts/generate_recurring_todos.py`











