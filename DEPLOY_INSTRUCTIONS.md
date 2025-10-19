# 部署说明 - 修复 404 错误

## 修改内容
1. 将 `App_new/static/Js/` 重命名为 `App_new/static/js/`（小写）
2. 修复了多个模板文件中的 JavaScript 引用路径
3. 在所有基础模板中添加了 favicon.ico 引用

## 部署步骤

### 方案 1: 使用 Git 部署（推荐）

```bash
# 1. 添加所有修改到 Git
git add .

# 2. 提交修改
git commit -m "修复静态资源路径大小写问题和 404 错误"

# 3. 推送到远程仓库
git push

# 4. 在服务器上拉取最新代码
# SSH 连接到服务器后执行：
cd /path/to/MyTravelPanel
git pull

# 5. 重启应用
# 如果使用 systemd:
sudo systemctl restart mytravelpanel

# 或者如果使用 gunicorn:
sudo supervisorctl restart mytravelpanel
```

### 方案 2: 手动部署

如果 Git 在 Windows 上无法正确识别文件夹重命名，请按以下步骤：

1. **在服务器上手动重命名文件夹：**
```bash
# SSH 连接到服务器
cd /path/to/MyTravelPanel/App_new/static
mv Js js
```

2. **上传修改的模板文件：**
使用 FTP/SFTP 工具上传以下文件到服务器：
- `App_new/templates/admin/base.html`
- `App_new/templates/auth/base.html`
- `App_new/templates/guest/shared/base.html`
- `App_new/templates/shared/staff_base.html`
- `App_new/templates/business/flight/flight_home.html`
- `App_new/templates/business/tour/package/TourProjects/tour_project_list.html`
- `App_new/templates/shared/utils/account_manage.html`

3. **重启应用服务**

### 验证部署

部署完成后，在浏览器中访问网站并：
1. 打开浏览器开发者工具（F12）
2. 切换到 Console 标签
3. 刷新页面
4. 确认没有 404 错误（除了 Tailwind CSS CDN 的警告）

## 注意事项

- **Tailwind CSS CDN 警告**：这只是一个警告，不影响功能。如需解决，可以安装 Tailwind CSS 作为项目依赖。
- **文件权限**：确保服务器上的静态文件有正确的读取权限
- **Nginx 配置**：如果使用 Nginx，确保静态文件路径配置正确

## 回滚方案

如果部署后出现问题：
```bash
# 回退到上一个版本
git revert HEAD
git push

# 在服务器上
git pull
sudo systemctl restart mytravelpanel
```

