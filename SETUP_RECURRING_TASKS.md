# 重复任务功能部署步骤

## 🎯 功能说明

现在您可以创建重复任务清单（例如：每周核对账单），系统会自动生成待办事项。

**使用场景示例：**
- ✅ 每周一自动生成"核对 UOB、OCBC、航空公司账户"的任务
- ✅ 每天生成"检查邮件"任务
- ✅ 每月生成"生成报表"任务

## 📋 部署步骤

### 步骤 1：创建数据库表

在**服务器**（Linux）上执行（本地和服务器共用数据库，只需在服务器执行一次）：

```bash
cd /path/to/MyTravelPanel

# 方法 1：使用 sqlite3
sqlite3 instance/travel_panel_new.db < migrations/create_todo_checklists_tables.sql

# 或方法 2：使用 Python
python3 -c "import sqlite3; conn = sqlite3.connect('instance/travel_panel_new.db'); conn.executescript(open('migrations/create_todo_checklists_tables.sql', encoding='utf-8').read()); conn.commit(); conn.close()"
```

验证表是否创建成功：
```bash
sqlite3 instance/travel_panel_new.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'todo_checklist%';"
```

应该看到：
```
todo_checklists
todo_checklist_items
```

### 步骤 2：重启应用

```bash
# 如果使用 systemd
sudo systemctl restart your-app-service

# 如果使用 supervisor
sudo supervisorctl restart your-app

# 或手动重启
```

### 步骤 3：设置自动任务生成（推荐）

在**服务器**上设置 cron 任务，每天自动运行：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天早上 8:00 执行）
0 8 * * * cd /path/to/MyTravelPanel && /usr/bin/python3 scripts/generate_recurring_todos.py >> logs/recurring_tasks.log 2>&1
```

或者每小时执行一次：
```bash
0 * * * * cd /path/to/MyTravelPanel && /usr/bin/python3 scripts/generate_recurring_todos.py >> logs/recurring_tasks.log 2>&1
```

确保日志目录存在：
```bash
mkdir -p logs
chmod 755 logs
```

### 步骤 4：测试功能

1. **访问任务清单管理页面**
   ```
   http://192.168.5.59:5000/utils/checklists/
   ```

2. **创建测试清单**
   - 点击"创建新清单"
   - 名称：测试清单
   - 勾选"启用重复任务"
   - 选择"每天"
   - 添加几个任务项
   - 保存

3. **手动测试生成**
   - 在清单列表中找到刚创建的清单
   - 点击"生成待办事项"按钮
   - 访问待办事项列表 `/utils/todos`，应该能看到新生成的任务

4. **测试自动生成**（如果设置了 cron）
   ```bash
   # 手动运行脚本测试
   cd /path/to/MyTravelPanel
   python3 scripts/generate_recurring_todos.py
   
   # 查看日志
   tail -f logs/recurring_tasks.log
   ```

## 🚀 使用指南

### 创建每周账单核对清单

1. 访问 `/utils/checklists/`
2. 点击"创建新清单"
3. 填写信息：
   - **名称**：每周账单核对
   - **分类**：公司日常  
   - **描述**：每周核对所有银行和航空公司账户
   - **勾选**"启用重复任务"
   - **重复类型**：每周
   - **选择日期**：勾选"周一"（或您希望的日期）
   - **生成时间**：09:00

4. 添加任务项（点击"添加任务"按钮）：
   ```
   任务 1: 核对 UOB 账户 - 高优先级
   任务 2: 核对 OCBC 账户 - 高优先级  
   任务 3: 核对 US AIRLINE 账户 - 中优先级
   任务 4: 核对 Indigo airline 账户 - 中优先级
   任务 5: 核对 Scoot airline 账户 - 中优先级
   ```

5. 点击"保存"

### 访问入口

- **从导航菜单**：工具 → 待办事项 → 任务清单管理
- **直接访问**：`/utils/checklists/`
- **从待办事项页面**：点击右上角"任务清单管理"按钮

## 📁 新增文件清单

1. **数据库模型**
   - `App_new/shared/models/Utilsmodels.py` (已更新)

2. **路由和API**
   - `App_new/utils/routes/checklist.py` (新建)

3. **前端页面**
   - `App_new/templates/shared/utils/checklist_list.html` (新建)
   - `App_new/templates/shared/utils/todo_list.html` (已更新 - 添加入口)

4. **数据库迁移**
   - `migrations/create_todo_checklists_tables.sql` (新建)

5. **自动化脚本**
   - `scripts/generate_recurring_todos.py` (新建)

6. **文档**
   - `docs/RECURRING_TASKS_GUIDE.md` (新建 - 详细使用指南)
   - `SETUP_RECURRING_TASKS.md` (本文件)

7. **配置更新**
   - `App_new/__init__.py` (已更新 - 注册蓝图和模型)
   - `App_new/shared/models/__init__.py` (已更新 - 导出模型)

## ⚠️ 注意事项

1. **数据库同步**：
   - 本地和服务器共用同一个数据库文件
   - 迁移脚本只需在服务器执行一次
   - 两边都能看到相同的任务清单

2. **文件同步**：
   - 确保所有新文件都已上传到服务器
   - 特别是 `App_new/utils/routes/checklist.py`
   - 和 `scripts/generate_recurring_todos.py`

3. **权限检查**：
   ```bash
   # 确保脚本有执行权限
   chmod +x scripts/generate_recurring_todos.py
   
   # 确保数据库可写
   chmod 664 instance/travel_panel_new.db
   ```

## 🔧 故障排查

### 问题：访问 /utils/checklists/ 出现 404

**解决方案：**
```bash
# 检查蓝图是否正确注册
grep -n "checklist_bp" App_new/__init__.py

# 重启应用
sudo systemctl restart your-app
```

### 问题：自动生成不工作

**解决方案：**
```bash
# 检查 cron 任务
crontab -l

# 手动运行脚本看是否有错误
cd /path/to/MyTravelPanel
python3 scripts/generate_recurring_todos.py

# 检查日志
tail -100 logs/recurring_tasks.log
```

### 问题：数据库表不存在

**解决方案：**
```bash
# 重新执行迁移脚本
sqlite3 instance/travel_panel_new.db < migrations/create_todo_checklists_tables.sql

# 验证
sqlite3 instance/travel_panel_new.db "SELECT COUNT(*) FROM todo_checklists;"
```

## 📞 需要帮助？

如果遇到问题，请检查：
1. 应用日志：`logs/travelpanel.log`
2. 任务生成日志：`logs/recurring_tasks.log`
3. 数据库表是否创建：使用上面的验证命令

## ✅ 部署完成检查清单

- [ ] 数据库表已创建
- [ ] 应用已重启
- [ ] Cron 任务已设置
- [ ] 可以访问 `/utils/checklists/` 页面
- [ ] 可以创建新清单
- [ ] 可以手动生成待办事项
- [ ] 自动生成脚本可以正常运行

完成以上检查后，您就可以开始使用重复任务功能了！🎉











