# Linux 服务器更新指南

## 在 Linux 上运行 server_update.sh

### 1. 准备工作

#### 检查脚本路径和配置
确保脚本中的配置正确：
- `PROJECT_DIR`: 项目目录路径（默认：`/var/www/MyTravelPanel`）
- `BRANCH`: Git 分支名（默认：`wip/backup-20250825-235609`）

#### 给脚本添加执行权限
```bash
chmod +x server_update.sh
```

#### 确保用户权限
- 需要有 sudo 权限来重启 nginx
- 需要有项目目录的读写权限

### 2. 运行脚本

#### 方法一：直接运行
```bash
./server_update.sh
```

#### 方法二：使用 bash 运行
```bash
bash server_update.sh
```

#### 方法三：使用完整路径
```bash
/var/www/MyTravelPanel/server_update.sh
```

### 3. 脚本执行流程

脚本会自动执行以下步骤：
1. ✅ 进入项目目录
2. ✅ 拉取最新代码（git fetch & pull）
3. ✅ 激活虚拟环境
4. ✅ 安装/更新 Python 依赖
5. ✅ 重启 gunicorn 服务
6. ✅ 重启 nginx 服务
7. ✅ 显示更新状态

### 4. 常见问题处理

#### 如果脚本执行失败

**问题 1: 权限不足**
```bash
# 确保脚本有执行权限
chmod +x server_update.sh

# 确保有 sudo 权限（用于重启 nginx）
sudo -v
```

**问题 2: 项目目录不存在**
```bash
# 检查并修改脚本中的 PROJECT_DIR 变量
vim server_update.sh
# 或
nano server_update.sh
```

**问题 3: 虚拟环境路径错误**
```bash
# 检查虚拟环境是否存在
ls -la /var/www/MyTravelPanel/venv

# 如果不存在，需要创建
cd /var/www/MyTravelPanel
python3 -m venv venv
```

**问题 4: Git 分支不存在**
```bash
# 检查远程分支
git branch -r | grep backup

# 如果需要切换分支，先更新
git fetch origin
```

**问题 5: 服务重启失败**
```bash
# 手动重启 gunicorn
pkill -f gunicorn
cd /var/www/MyTravelPanel
source venv/bin/activate
gunicorn --workers 3 --bind 127.0.0.1:8000 app_new:app --daemon

# 手动重启 nginx
sudo systemctl restart nginx
```

### 5. 验证更新

更新完成后，检查以下内容：

```bash
# 检查最新提交
cd /var/www/MyTravelPanel
git log -1 --oneline

# 检查 nginx 状态
sudo systemctl status nginx

# 检查 gunicorn 进程
ps aux | grep gunicorn

# 检查端口监听
netstat -tlnp | grep 8000
# 或
ss -tlnp | grep 8000

# 查看应用日志（如果有）
tail -f /var/log/travelpanel.log
```

### 6. 自动化部署（可选）

#### 使用 cron 定时更新
```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 3 点自动更新（示例）
0 3 * * * cd /var/www/MyTravelPanel && ./server_update.sh >> /var/log/update.log 2>&1
```

#### 使用 webhook 自动更新
创建一个简单的 webhook 接收脚本，当收到 GitHub webhook 时自动执行更新。

### 7. 推荐使用方式

#### 推荐：使用 quick_update.sh（更安全）
```bash
chmod +x quick_update.sh
./quick_update.sh
```

`quick_update.sh` 的优势：
- ✅ 交互式确认，避免误操作
- ✅ 自动检测服务管理方式（systemd/supervisor/pm2）
- ✅ 自动保存本地更改（stash）
- ✅ 更详细的错误处理和状态显示

### 8. 安全注意事项

1. **备份数据**：更新前建议备份数据库和重要配置文件
2. **测试环境**：先在测试环境运行，确认无误后再在生产环境执行
3. **权限管理**：不要给脚本过高的权限，只给必要的 sudo 权限
4. **日志记录**：建议将更新过程记录到日志文件

#### 带日志的更新命令
```bash
./server_update.sh 2>&1 | tee -a /var/log/travelpanel_update.log
```

### 9. 示例执行输出

```
==========================================
       MyTravelPanel 项目更新脚本
==========================================

[1/5] 进入项目目录...
当前目录: /var/www/MyTravelPanel

[2/5] 拉取最新代码...
From https://github.com/Zhuanpy/MyTravelPanel
 * branch            wip/backup-20250825-235609 -> FETCH_HEAD
Already up to date.

[3/5] 激活虚拟环境...

[4/5] 安装/更新依赖...
Requirement already satisfied: ...

[5/5] 重启服务...
>>> 停止旧的 gunicorn 进程...
>>> 启动 gunicorn...
>>> 重启 nginx...
>>> 服务重启完成

==========================================
           更新完成!
==========================================

当前分支: wip/backup-20250825-235609
最新提交:
8647631 优化首页设计：精简重复内容，添加首页轮播图管理功能

nginx 状态:
● nginx.service - A high performance web server and a reverse proxy server
   Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
   Active: active (running) since ...

请访问网站检查是否正常运行
```

