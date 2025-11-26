# 服务器部署步骤

## ✅ 本地已完成：
- 代码已提交并推送到 GitHub
- 分支：wip/backup-20250825-235609
- Commit: 44b29c8

## 🖥️ 服务器端操作：

### 1. SSH 连接到服务器
```bash
ssh your_username@your_server_ip
```

### 2. 进入项目目录
```bash
cd /path/to/MyTravelPanel
# 例如：cd /var/www/MyTravelPanel
```

### 3. 拉取最新代码
```bash
git pull origin wip/backup-20250825-235609
```

### 4. 确认文件夹重命名成功
```bash
# 检查是否存在小写的 js 文件夹
ls -la App_new/static/js

# 应该能看到所有 .js 文件
```

### 5. 重启应用服务

#### 如果使用 systemd：
```bash
sudo systemctl restart mytravelpanel
# 或者你的服务名称，例如：
# sudo systemctl restart gunicorn
# sudo systemctl restart mytravelpanel.service
```

#### 如果使用 supervisord：
```bash
sudo supervisorctl restart mytravelpanel
```

#### 如果使用 pm2：
```bash
pm2 restart mytravelpanel
```

#### 如果直接运行 gunicorn：
```bash
# 找到进程
ps aux | grep gunicorn

# 杀死进程
kill -HUP <pid>

# 或重新启动
pkill gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app_new:app
```

### 6. 验证部署

访问你的网站并打开浏览器开发者工具（F12）：

1. 打开 Console 标签
2. 刷新页面（Ctrl+F5 强制刷新）
3. 检查是否还有 404 错误

#### 预期结果：
- ✅ `/static/js/project_detail.js` 应该返回 200
- ✅ `/static/JE/LOGO.png` 应该返回 200
- ✅ `/favicon.ico` 应该返回 200

#### 可能的警告（可以忽略）：
- ⚠️ Tailwind CSS CDN 警告（不影响功能）

### 7. 如果遇到问题

#### 问题 1：git pull 冲突
```bash
# 先备份当前更改
git stash

# 拉取更新
git pull

# 如果需要，恢复更改
git stash pop
```

#### 问题 2：文件权限问题
```bash
# 确保 Web 服务器用户有权限读取静态文件
sudo chown -R www-data:www-data App_new/static/
# 或者
sudo chown -R nginx:nginx App_new/static/
```

#### 问题 3：Nginx 缓存
```bash
# 清除 Nginx 缓存
sudo nginx -t
sudo systemctl reload nginx
```

### 8. 监控日志

```bash
# 查看应用日志
tail -f logs/travelpanel.log

# 查看 Nginx 错误日志
tail -f /var/log/nginx/error.log

# 查看 systemd 服务日志
sudo journalctl -u mytravelpanel -f
```

## 🔄 回滚方案（如果出现问题）

```bash
# 回退到上一个版本
git log --oneline -5  # 查看最近的提交
git checkout 6243686  # 回退到修复前的版本

# 重启服务
sudo systemctl restart mytravelpanel
```

## 📞 需要帮助？

如果部署过程中遇到任何问题，请提供：
1. 错误日志内容
2. 服务器操作系统版本
3. 使用的 Web 服务器（Nginx/Apache）
4. 应用服务管理方式（systemd/supervisord/pm2）



