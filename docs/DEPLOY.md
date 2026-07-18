# 部署运维指南

## 目录结构

```
/var/www/MyTravelPanel/        # 项目根目录
├── .env                       # 服务器环境变量（不入 git，含密码）
├── App_new/
│   └── config.py              # 配置类，从 .env 读取
├── venv/                      # Python 虚拟环境
└── ...

/etc/systemd/system/
└── mytravelpanel.service      # systemd 服务定义
```

## 关键原则

- **`.env` 永远不进 git** ── 含密码、密钥等敏感信息
- **服务器代码必须从 git 拉取**，不能在服务器上直接改源码（之前出过问题：服务器 `.env` 里的 `DB_PASSWORD` 与某些脚本硬编码值不一致，浪费排查时间。现所有密码统一走 `.env`，不再硬编码）
- **修改配置 → 改 `.env`，不改 `config.py`**

## 日常部署流程

### 1. 本地开发并提交

```bash
# 本地修改代码、测试
python app_new.py
# 测试通过后
git add <改动的文件>
git commit -m "你的提交信息"
git push origin <branch>
```

### 2. 服务器拉取并重启

```bash
ssh root@<server>
cd /var/www/MyTravelPanel

# 备份当前 .env（保险）
cp .env .env.bak.$(date +%Y%m%d_%H%M%S)

# 拉取最新代码
git fetch origin
git pull origin <branch>

# 重启服务
sudo systemctl restart mytravelpanel

# 验证
sudo systemctl status mytravelpanel --no-pager | head -10
sudo netstat -tnp | grep :3306 | grep ESTABLISHED   # gunicorn 重新连上 MySQL
```

### 3. 浏览器测试核心功能

- 登录
- 项目列表
- 任意一个数据相关页面
- （如果改动涉及邮件）发一封测试邮件

## 修改 `.env`（环境变量）

```bash
ssh root@<server>
cp /var/www/MyTravelPanel/.env /var/www/MyTravelPanel/.env.bak.$(date +%Y%m%d_%H%M%S)
nano /var/www/MyTravelPanel/.env

# 改完重启
sudo systemctl restart mytravelpanel
```

## 回滚

```bash
cd /var/www/MyTravelPanel
git log --oneline -5             # 找到要回滚到的 commit hash
git reset --hard <commit-hash>
sudo systemctl restart mytravelpanel
```

如果 `.env` 被改坏：

```bash
# 找到最近备份还原
ls -t /var/www/MyTravelPanel/.env.bak.* | head -1 | xargs -I{} cp {} /var/www/MyTravelPanel/.env
sudo systemctl restart mytravelpanel
```

## 必须的 `.env` 变量

参考项目根目录的 `.env.example`。最少需要：

```
DB_USER=root
DB_PASSWORD=<真实密码>
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=travelindustry

SECRET_KEY=<随机生成的强密钥>

MAIL_SERVER=smtp.qiye.aliyun.com
MAIL_PORT=465
MAIL_USE_SSL=true
MAIL_USERNAME=<邮箱>
MAIL_PASSWORD=<邮箱授权码>
MAIL_DEFAULT_SENDER=<邮箱>
```

## 服务管理常用命令

```bash
# 启动 / 停止 / 重启
sudo systemctl start mytravelpanel
sudo systemctl stop mytravelpanel
sudo systemctl restart mytravelpanel

# 查看状态
sudo systemctl status mytravelpanel --no-pager

# 查看日志
sudo journalctl -u mytravelpanel --since "10 minutes ago" --no-pager
sudo journalctl -u mytravelpanel -f          # 实时

# 看 worker 进程
ps aux | grep gunicorn | grep -v grep
```

## MySQL 密码轮换

由于历史 commit 里曾硬编码过 MySQL 密码（已在 commit `a51eaca` 之后的修复中清除），**强烈建议轮换一次密码**：

```bash
# 1. 登录 MySQL
sudo mysql

# 2. 生成新密码（在终端外用密码生成工具，或用：openssl rand -base64 24）
# 假设新密码为 NEW_PASSWORD

# 3. 修改 root 密码
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NEW_PASSWORD';
FLUSH PRIVILEGES;
EXIT;

# 4. 立刻更新 .env
nano /var/www/MyTravelPanel/.env
# 修改 DB_PASSWORD=NEW_PASSWORD

# 5. 重启服务
sudo systemctl restart mytravelpanel

# 6. 验证连接
sudo netstat -tnp | grep :3306 | grep ESTABLISHED
```

## 性能监控

慢请求日志：`logs/slow_request.log`
慢 SQL 日志：`logs/slow_query.log`

聚合分析：

```bash
cd /var/www/MyTravelPanel
python3 scripts/analyze_perf_logs.py --days 1 --top 20
```

## 服务器层关键配置（已完成的加固）

- MySQL `bind-address = 127.0.0.1`（不暴露公网）
- 阿里云安全组关闭 3306 入方向公网规则
- 2 GB swap（防 OOM 卡死）
- gunicorn `--max-requests 500 --max-requests-jitter 50`（worker 自动回收防内存泄漏）
- APScheduler 文件锁（仅一个 worker 启动调度）

## 故障排查速查

| 症状 | 第一步检查 |
|------|------|
| 网站打不开 | `sudo systemctl status mytravelpanel` |
| MySQL 连接失败 | `sudo systemctl status mysql` + `sudo netstat -tlnp \| grep 3306` |
| CPU 飙高 | `ps aux --sort=-%cpu \| head` + `python3 scripts/analyze_perf_logs.py --days 1` |
| 内存爆了 | `free -h` + `sudo dmesg -T \| grep -iE "oom\|killed" \| tail` |
| 邮件没发出 | 看 `journalctl -u mytravelpanel \| grep -i email` |
