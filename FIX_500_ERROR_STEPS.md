# 修复 500 错误 - 分步骤指南

## 🔍 第一步：查看错误日志

### 命令 1: 查看应用日志（最近的错误）

```bash
tail -100 logs/travelpanel.log
```

如果日志文件不存在或路径不同，尝试：

```bash
# 查找日志文件
find . -name "*.log" -type f | head -5

# 或查看系统日志
sudo journalctl -u mytravelpanel -n 100 --no-pager
```

**记录下看到的错误信息**

---

### 命令 2: 查看最近的系统日志

```bash
# 查看 systemd 服务日志
sudo journalctl -u mytravelpanel -n 50 --no-pager | grep -i error

# 查看所有相关错误
sudo journalctl -u mytravelpanel --since "1 hour ago" | grep -i -E "error|exception|traceback"
```

---

### 命令 3: 查看 Nginx/Apache 错误日志

```bash
# 如果使用 Nginx
sudo tail -50 /var/log/nginx/error.log

# 如果使用 Apache
sudo tail -50 /var/log/apache2/error.log
```

---

## 🔍 第二步：检查服务是否正常运行

### 命令 1: 检查进程是否运行

```bash
ps aux | grep -E 'gunicorn|python.*app_new' | grep -v grep
```

**预期输出：** 应该看到 gunicorn 或 python 进程

---

### 命令 2: 检查服务状态

```bash
# 如果使用 systemd
sudo systemctl status mytravelpanel

# 如果使用 supervisor
sudo supervisorctl status mytravelpanel

# 如果使用 pm2
pm2 status mytravelpanel
```

---

## 🔍 第三步：进入项目目录并检查代码

### 命令 1: 进入项目目录（请修改为你的实际路径）

```bash
cd /var/www/MyTravelPanel
```

---

### 命令 2: 检查当前代码版本

```bash
git log --oneline -3
git status
```

---

### 命令 3: 检查 Python 环境

```bash
# 检查 Python 版本
python3 --version

# 检查关键包是否安装
python3 -c "import flask; print('Flask:', flask.__version__)"
python3 -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)"
```

---

## 🔍 第四步：检查数据库连接

### 命令 1: 测试数据库连接

```bash
# 如果有数据库配置文件，查看配置
grep -r "SQLALCHEMY_DATABASE_URI" . --include="*.py" --include="*.env" | head -3

# 测试 MySQL 连接（如果有 MySQL）
mysql -u用户名 -p数据库名 -e "SELECT 1;"
```

---

### 命令 2: 检查数据库表是否存在

```bash
# 查看配置文件中的数据库设置
cat .env | grep -i database
# 或
cat config.py | grep -i database
```

---

## 🔍 第五步：查看具体错误（Python 调试）

### 命令 1: 手动测试导入

```bash
cd /var/www/MyTravelPanel

# 如果有虚拟环境，先激活
# source venv/bin/activate

# 测试导入关键模块
python3 -c "from App_new.staff.routes.staff import staff; print('导入成功')"
```

---

### 命令 2: 查看路由注册

```bash
# 检查路由文件是否存在
ls -la App_new/staff/routes/staff.py

# 查看路由定义
grep -n "def dashboard" App_new/staff/routes/staff.py
```

---

## 🛠️ 第六步：常见问题修复

### 问题 1: 缺少依赖包

```bash
# 检查并安装依赖
pip3 list | grep -E "Flask|SQLAlchemy|pandas|openpyxl"

# 如果缺少，安装
pip3 install -r requirements.txt
```

---

### 问题 2: 数据库表不存在

```bash
# 运行数据库迁移
# 如果有虚拟环境，先激活
# source venv/bin/activate

flask db upgrade
```

---

### 问题 3: 模板文件缺失

```bash
# 检查模板文件是否存在
ls -la App_new/templates/staff/staff_dashboard.html

# 如果不存在，检查其他模板
find App_new/templates -name "*dashboard*" -type f
```

---

### 问题 4: 权限问题

```bash
# 检查文件权限
ls -la App_new/staff/routes/staff.py

# 修复权限（如果需要）
sudo chown -R www-data:www-data /var/www/MyTravelPanel
sudo chmod -R 755 /var/www/MyTravelPanel
```

---

## 🔄 第七步：重启服务

### 命令 1: 重启应用服务

```bash
# 根据你的服务管理方式选择：

# systemd:
sudo systemctl restart mytravelpanel
sleep 3
sudo systemctl status mytravelpanel

# supervisor:
sudo supervisorctl restart mytravelpanel
sleep 3
sudo supervisorctl status mytravelpanel

# pm2:
pm2 restart mytravelpanel
sleep 3
pm2 status mytravelpanel

# gunicorn (直接运行):
ps aux | grep gunicorn | grep -v grep
kill -HUP <主进程PID>
```

---

### 命令 2: 重新加载 Nginx（如果使用）

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📊 第八步：实时监控日志

### 命令 1: 实时查看应用日志

```bash
# 在新终端窗口中运行（不要关闭）
tail -f logs/travelpanel.log
```

---

### 命令 2: 实时查看系统日志

```bash
# 在新终端窗口中运行
sudo journalctl -u mytravelpanel -f
```

---

### 命令 3: 再次访问网站测试

在另一个终端或浏览器中访问：
```
https://www.joyesc.com/staff/dashboard
```

同时观察日志输出，查看具体错误信息。

---

## 🔧 第九步：根据错误信息修复

根据日志中的具体错误，执行相应的修复命令：

### 如果是数据库连接错误：

```bash
# 检查数据库配置
cat .env | grep DATABASE
# 或
cat App_new/config.py | grep -A 5 DATABASE
```

### 如果是导入错误：

```bash
# 检查 Python 路径
python3 -c "import sys; print('\n'.join(sys.path))"

# 检查模块是否存在
python3 -c "from App_new.business.projects.models.project import ProjectHeader; print('OK')"
```

### 如果是模板错误：

```bash
# 检查模板文件
ls -la App_new/templates/staff/staff_dashboard.html

# 查看模板语法
python3 -c "from jinja2 import Template; Template(open('App_new/templates/staff/staff_dashboard.html').read())"
```

---

## ✅ 第十步：验证修复

### 命令 1: 检查服务状态

```bash
sudo systemctl status mytravelpanel
# 或
sudo supervisorctl status mytravelpanel
```

---

### 命令 2: 测试 HTTP 响应

```bash
curl -I http://localhost:8000/staff/dashboard
# 或
curl -I https://www.joyesc.com/staff/dashboard
```

---

### 命令 3: 查看进程和端口

```bash
ps aux | grep gunicorn | grep -v grep
netstat -tlnp | grep :8000
```

---

## 📝 完整诊断脚本（可选）

如果需要，我可以创建一个自动诊断脚本，运行后会收集所有信息。

---

## 🆘 如果问题仍然存在

请提供以下信息：

1. **错误日志的完整内容**（从步骤1获取）
2. **服务状态输出**（从步骤2获取）
3. **Python 版本和关键包版本**（从步骤3获取）
4. **具体的错误堆栈信息**

这样我可以更准确地帮你定位问题。

