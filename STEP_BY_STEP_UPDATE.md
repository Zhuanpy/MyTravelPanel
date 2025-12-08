# 分步更新项目指南

## 📋 准备工作

### 步骤 0: 确认你已在服务器上

```bash
# 确认当前用户和位置
whoami
pwd

# 确认可以访问项目
ls -la
```

---

## 🔍 第一步：查看当前状态

### 命令 1: 进入项目目录

```bash
# 请根据你的实际路径修改
cd /var/www/MyTravelPanel
```

### 命令 2: 查看当前分支

```bash
git branch
```

**预期输出示例：**
```
* wip/backup-20250825-235609
```

### 命令 3: 查看当前状态

```bash
git status
```

**预期输出：**
- 如果显示 "nothing to commit, working tree clean" → ✅ 可以继续
- 如果有未提交的更改 → 需要先处理（见下方）

### 命令 4: 如果有未提交的更改，先保存

```bash
# 查看有哪些更改
git status

# 保存当前更改（可选）
git stash save "Backup before update - $(date '+%Y-%m-%d %H:%M:%S')"

# 或者如果确定要丢弃本地更改（谨慎使用）
# git reset --hard HEAD
```

**完成后确认：**
```bash
git status
# 应该显示 "working tree clean"
```

---

## 📥 第二步：拉取最新代码

### 命令 1: 查看远程更新

```bash
git fetch origin
```

### 命令 2: 查看本地和远程的差异

```bash
git log HEAD..origin/wip/backup-20250825-235609 --oneline
```

**预期输出：**
- 如果显示提交列表 → 有新更新
- 如果显示空 → 已经是最新的

### 命令 3: 拉取最新代码

```bash
git pull origin wip/backup-20250825-235609
```

**预期输出示例：**
```
Updating 3948dcb..新commit哈希
Fast-forward
 App_new/finance/routes/athina_routes.py | 1234 ++++++++---
 ...
 X files changed, Y insertions(+), Z deletions(-)
```

**如果遇到冲突：**
```bash
# 查看冲突文件
git status

# 如果有冲突，先保存本地更改
git stash

# 重新拉取
git pull origin wip/backup-20250825-235609

# 恢复本地更改（如果需要）
git stash pop
```

### 命令 4: 确认更新成功

```bash
# 查看最近的提交
git log --oneline -3

# 查看最新提交的详细信息
git show HEAD
```

---

## 🔧 第三步：检查是否需要安装依赖

### 命令 1: 查看是否有新依赖

```bash
# 查看 requirements.txt 是否有变化
git diff HEAD~1 HEAD -- requirements.txt
```

### 命令 2: 如果需要，安装新依赖

```bash
# 如果有虚拟环境，先激活
# source venv/bin/activate

# 安装依赖（如果需要）
pip3 install -r requirements.txt

# 或者只安装新添加的包
pip3 install -r requirements.txt --upgrade
```

**验证：**
```bash
# 检查关键包是否已安装
pip3 list | grep -E "Flask|pandas|openpyxl"
```

---

## 🗄️ 第四步：检查是否需要数据库迁移

### 命令 1: 查看是否有数据库迁移文件

```bash
# 查看 migrations 目录是否有新文件
ls -la migrations/versions/ | tail -5

# 或查看 SQL 文件
ls -la *.sql
```

### 命令 2: 如果需要，运行数据库迁移

```bash
# 如果有虚拟环境，先激活
# source venv/bin/activate

# 检查迁移状态
flask db current

# 运行迁移（如果有新的）
flask db upgrade
```

**重要提示：**
- 如果有新的 SQL 迁移脚本（如 `add_order_type_column.sql`），需要手动执行
- 查看 SQL 文件内容，确认是否需要执行

```bash
# 查看 SQL 文件内容
cat add_order_type_column.sql

# 如果需要执行，连接到数据库执行
# mysql -u用户名 -p 数据库名 < add_order_type_column.sql
```

---

## 🔍 第五步：查找服务管理方式

### 命令 1: 检查是否使用 systemd

```bash
# 列出所有相关服务
systemctl list-units --type=service | grep -i travel
# 或
systemctl list-units --type=service | grep -i mytravel

# 查看特定服务状态
sudo systemctl status mytravelpanel
```

**如果有服务：**
```bash
# 记录服务名称，例如：mytravelpanel.service
```

### 命令 2: 检查是否使用 supervisor

```bash
# 查看 supervisor 配置的服务
sudo supervisorctl status

# 或查看特定服务
sudo supervisorctl status mytravelpanel
```

**如果有服务：**
```bash
# 记录服务名称，例如：mytravelpanel
```

### 命令 3: 检查是否使用 pm2

```bash
# 查看 pm2 进程列表
pm2 list

# 查看特定服务
pm2 describe mytravelpanel
```

### 命令 4: 检查是否直接运行 gunicorn

```bash
# 查找 gunicorn 进程
ps aux | grep gunicorn | grep -v grep
```

**预期输出示例：**
```
www-data  1234  0.5  2.1  gunicorn: master [app_new:app]
www-data  1235  0.2  1.5  gunicorn: worker [app_new:app]
```

**记录主进程 PID（第一个数字）**

---

## 🔄 第六步：重启服务（根据实际情况选择）

### 方式 A: 使用 systemd（如果检测到 systemd 服务）

```bash
# 步骤 1: 重启服务
sudo systemctl restart mytravelpanel

# 步骤 2: 等待 2 秒
sleep 2

# 步骤 3: 查看状态
sudo systemctl status mytravelpanel
```

**预期输出：**
```
● mytravelpanel.service - MyTravelPanel Application
   Loaded: loaded (/etc/systemd/system/mytravelpanel.service)
   Active: active (running) since ...
```

**如果显示 active (running) → ✅ 成功**

---

### 方式 B: 使用 supervisor（如果检测到 supervisor 服务）

```bash
# 步骤 1: 重启服务
sudo supervisorctl restart mytravelpanel

# 步骤 2: 等待 2 秒
sleep 2

# 步骤 3: 查看状态
sudo supervisorctl status mytravelpanel
```

**预期输出：**
```
mytravelpanel                    RUNNING   pid 1234, uptime 0:00:05
```

**如果显示 RUNNING → ✅ 成功**

---

### 方式 C: 使用 pm2（如果检测到 pm2 服务）

```bash
# 步骤 1: 重启服务
pm2 restart mytravelpanel

# 步骤 2: 等待 2 秒
sleep 2

# 步骤 3: 查看状态
pm2 status mytravelpanel
```

**预期输出：**
```
┌─────┬──────────────┬─────────┐
│ id  │ name         │ status  │
├─────┼──────────────┼─────────┤
│ 0   │ mytravelpanel│ online  │
└─────┴──────────────┴─────────┘
```

**如果显示 online → ✅ 成功**

---

### 方式 D: 手动管理 gunicorn（如果直接运行 gunicorn）

```bash
# 步骤 1: 找到 gunicorn 主进程 PID
ps aux | grep '[g]unicorn.*master' | awk '{print $2}'

# 步骤 2: 记录 PID（例如：1234），然后发送 HUP 信号重新加载
kill -HUP <PID>

# 示例：
# kill -HUP 1234
```

**或者完全重启：**

```bash
# 步骤 1: 停止所有 gunicorn 进程
pkill gunicorn

# 步骤 2: 等待进程完全停止
sleep 2

# 步骤 3: 重新启动（请根据你的实际启动命令修改）
cd /var/www/MyTravelPanel
# 如果有虚拟环境
source venv/bin/activate
# 启动 gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app_new:app
```

---

## ✅ 第七步：验证服务运行

### 命令 1: 检查进程是否运行

```bash
ps aux | grep -E '[g]unicorn|[p]ython.*app_new' | grep -v grep
```

**预期输出：**
- 应该看到 gunicorn 或 python 进程
- 如果没有任何输出 → ⚠️ 服务可能未启动

### 命令 2: 检查端口是否监听

```bash
# 检查常用端口（请根据你的实际端口修改）
netstat -tlnp | grep :8000
# 或
ss -tlnp | grep :8000
```

**预期输出：**
```
tcp  0  0  0.0.0.0:8000  0.0.0.0:*  LISTEN  1234/gunicorn
```

### 命令 3: 测试 HTTP 响应

```bash
# 测试本地访问
curl -I http://localhost:8000

# 或测试完整 URL（如果有域名）
curl -I http://your-domain.com
```

**预期输出：**
```
HTTP/1.1 200 OK
...
```

### 命令 4: 查看服务日志（最后几行）

```bash
# 如果是 systemd
sudo journalctl -u mytravelpanel -n 20 --no-pager

# 如果是 supervisor
sudo supervisorctl tail -20 mytravelpanel

# 如果是 pm2
pm2 logs mytravelpanel --lines 20

# 如果是应用日志文件
tail -20 logs/travelpanel.log
```

**检查是否有错误：**
- 如果有 ERROR 或 Exception → ⚠️ 需要检查
- 如果只有正常的 INFO 日志 → ✅ 正常

---

## 📊 第八步：最终验证

### 命令 1: 查看最近的提交记录

```bash
git log --oneline -3
```

**确认最新提交是否包含本次更新**

### 命令 2: 查看更新的文件列表

```bash
# 查看最近一次提交更改了哪些文件
git show HEAD --stat
```

### 命令 3: 访问网站测试功能

1. 在浏览器中访问你的网站
2. 测试关键功能是否正常
3. 检查控制台是否有错误（F12）

---

## 🆘 如果遇到问题

### 问题 1: Git Pull 失败

```bash
# 查看具体错误
git pull origin wip/backup-20250825-235609

# 如果有冲突，查看冲突文件
git status

# 解决冲突后
git add .
git commit -m "Resolve conflicts"
git pull origin wip/backup-20250825-235609
```

### 问题 2: 服务启动失败

```bash
# 查看详细错误日志
sudo journalctl -u mytravelpanel -n 50 --no-pager

# 检查配置文件
sudo systemctl cat mytravelpanel

# 重新加载配置并重启
sudo systemctl daemon-reload
sudo systemctl restart mytravelpanel
```

### 问题 3: 端口被占用

```bash
# 查看占用端口的进程
sudo lsof -i :8000

# 如果需要，停止占用进程
sudo kill -9 <PID>
```

### 问题 4: 权限问题

```bash
# 检查文件权限
ls -la

# 修复权限（请根据实际情况修改用户和路径）
sudo chown -R www-data:www-data /var/www/MyTravelPanel
sudo chmod -R 755 /var/www/MyTravelPanel
```

---

## 📝 更新完成检查清单

- [ ] 代码已成功拉取
- [ ] 依赖已安装（如果需要）
- [ ] 数据库迁移已完成（如果需要）
- [ ] 服务已成功重启
- [ ] 进程正在运行
- [ ] 端口正在监听
- [ ] HTTP 响应正常
- [ ] 日志无严重错误
- [ ] 网站功能正常

---

## 💡 快速参考

### 一条命令完成所有步骤（谨慎使用）

```bash
cd /var/www/MyTravelPanel && \
git pull origin wip/backup-20250825-235609 && \
sudo systemctl restart mytravelpanel && \
sleep 3 && \
sudo systemctl status mytravelpanel
```

### 查看帮助命令

```bash
# Git 帮助
git --help
git pull --help

# Systemd 帮助
systemctl --help
systemctl status --help

# 服务管理帮助
supervisorctl --help
pm2 --help
```

---

**完成所有步骤后，你的项目应该已经成功更新并运行了！** 🎉

