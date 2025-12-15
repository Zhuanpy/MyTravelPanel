# 阿里云服务器更新和重启指南

## 📋 快速更新命令（推荐）

如果你已经在服务器上，可以直接复制以下命令：

```bash
# 1. 进入项目目录（请根据实际情况修改路径）
cd /var/www/MyTravelPanel

# 2. 拉取最新代码
git pull origin wip/backup-20250825-235609

# 3. 重启服务（根据你的服务管理方式选择其中一个）

# 方式A: 如果使用 systemd
sudo systemctl restart mytravelpanel
sudo systemctl status mytravelpanel

# 方式B: 如果使用 supervisor
sudo supervisorctl restart mytravelpanel
sudo supervisorctl status mytravelpanel

# 方式C: 如果使用 pm2
pm2 restart mytravelpanel
pm2 status mytravelpanel

# 方式D: 如果直接运行 gunicorn，重新加载配置
ps aux | grep gunicorn
kill -HUP <gunicorn主进程PID>
```

## 🚀 使用自动化脚本

### 步骤 1: 上传脚本到服务器

将 `update_and_restart.sh` 上传到服务器，或者直接在服务器上创建：

```bash
# 在服务器上创建脚本
nano update_and_restart.sh
# 粘贴脚本内容，保存退出 (Ctrl+X, Y, Enter)
```

### 步骤 2: 修改脚本配置

编辑脚本，修改以下变量：

```bash
nano update_and_restart.sh
```

需要修改的地方：
- `PROJECT_DIR`: 你的项目实际路径（例如：`/var/www/MyTravelPanel`）
- `BRANCH`: 分支名称（当前是：`wip/backup-20250825-235609`）
- `SERVICE_NAME`: 你的服务名称（例如：`mytravelpanel`）

### 步骤 3: 添加执行权限并运行

```bash
chmod +x update_and_restart.sh
./update_and_restart.sh
```

## 📝 详细步骤说明

### 1. 连接到服务器

```bash
ssh your_username@your_server_ip
```

### 2. 进入项目目录

```bash
cd /path/to/MyTravelPanel
# 常见路径示例：
# cd /var/www/MyTravelPanel
# cd /home/username/MyTravelPanel
```

### 3. 查看当前状态

```bash
# 查看当前分支
git branch

# 查看当前状态
git status

# 查看最近的提交
git log --oneline -5
```

### 4. 保存当前更改（如果有）

如果服务器上有未提交的本地修改：

```bash
# 保存更改
git stash save "Backup before update - $(date)"

# 或者如果确定要丢弃本地更改
git reset --hard HEAD
```

### 5. 拉取最新代码

```bash
# 拉取指定分支
git pull origin wip/backup-20250825-235609

# 或者如果已经在正确的分支上
git pull
```

### 6. 检查更新内容

```bash
# 查看最近5次提交
git log --oneline -5

# 查看具体更改的文件
git diff HEAD~1 HEAD --stat
```

### 7. 安装新依赖（如果需要）

```bash
# 如果有新的 Python 包
pip3 install -r requirements.txt

# 或者使用虚拟环境
source venv/bin/activate  # 如果你的项目使用虚拟环境
pip install -r requirements.txt
```

### 8. 运行数据库迁移（如果需要）

如果代码中包含数据库结构变更：

```bash
# 激活虚拟环境（如果使用）
source venv/bin/activate

# 运行迁移
flask db upgrade
```

### 9. 重启应用服务

根据你的服务管理方式选择：

#### 方式 A: Systemd 服务

```bash
# 重启服务
sudo systemctl restart mytravelpanel

# 查看状态
sudo systemctl status mytravelpanel

# 查看日志
sudo journalctl -u mytravelpanel -f
```

#### 方式 B: Supervisor

```bash
# 重启服务
sudo supervisorctl restart mytravelpanel

# 查看状态
sudo supervisorctl status mytravelpanel

# 查看日志
sudo supervisorctl tail -f mytravelpanel
```

#### 方式 C: PM2

```bash
# 重启服务
pm2 restart mytravelpanel

# 查看状态
pm2 status mytravelpanel

# 查看日志
pm2 logs mytravelpanel
```

#### 方式 D: 手动管理 Gunicorn

```bash
# 找到 gunicorn 主进程
ps aux | grep gunicorn

# 方法1: 发送 HUP 信号重新加载（推荐，不中断服务）
kill -HUP <主进程PID>

# 方法2: 完全重启
pkill gunicorn
# 然后重新启动（根据你的启动命令）
gunicorn -w 4 -b 0.0.0.0:8000 app_new:app
```

### 10. 验证服务运行

```bash
# 检查进程是否运行
ps aux | grep -E 'gunicorn|python.*app_new' | grep -v grep

# 检查端口是否监听
netstat -tlnp | grep :8000
# 或
ss -tlnp | grep :8000

# 测试 HTTP 响应
curl -I http://localhost:8000
```

### 11. 查看日志

```bash
# 应用日志
tail -f logs/travelpanel.log

# 或 systemd 日志
sudo journalctl -u mytravelpanel -f

# 或 Nginx 日志（如果使用）
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## ⚠️ 常见问题处理

### 问题 1: Git Pull 冲突

```bash
# 查看冲突文件
git status

# 如果需要，保存当前更改
git stash

# 重新拉取
git pull origin wip/backup-20250825-235609

# 恢复保存的更改（如果需要）
git stash pop
```

### 问题 2: 服务启动失败

```bash
# 查看详细错误日志
sudo journalctl -u mytravelpanel -n 100 --no-pager

# 检查配置文件
sudo systemctl cat mytravelpanel

# 测试服务配置
sudo systemctl daemon-reload
```

### 问题 3: 权限问题

```bash
# 确保文件权限正确
sudo chown -R www-data:www-data /path/to/MyTravelPanel
sudo chmod -R 755 /path/to/MyTravelPanel

# 确保日志目录可写
mkdir -p logs
chmod 755 logs
```

### 问题 4: 端口被占用

```bash
# 查看端口占用
sudo lsof -i :8000
# 或
sudo netstat -tlnp | grep :8000

# 如果需要，修改配置文件中的端口
```

## 🔄 回滚操作

如果更新后出现问题，可以回滚：

```bash
# 1. 查看提交历史
git log --oneline -10

# 2. 回滚到上一个版本
git checkout <上一个版本的commit-hash>

# 3. 重启服务
sudo systemctl restart mytravelpanel

# 4. 验证
curl -I http://localhost:8000
```

## 📊 监控和验证

更新后，建议：

1. **检查网站是否正常访问**
2. **检查关键功能是否正常**
3. **查看日志是否有错误**
4. **监控资源使用情况**（CPU、内存）

```bash
# 实时监控资源
top

# 或使用 htop（如果已安装）
htop
```

## 🔗 相关文档

- `SERVER_DEPLOY_STEPS.md` - 详细的部署步骤
- `requirements.txt` - Python 依赖列表
- `nginx.conf` - Nginx 配置示例

## 📞 需要帮助？

如果遇到问题，请提供：
1. 错误日志内容
2. 服务状态输出
3. 系统信息（`uname -a`）
4. Python 版本（`python3 --version`）









