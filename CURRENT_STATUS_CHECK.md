# 当前系统状态检查

## 从 top 输出分析

### CPU 状态：✅ 正常
- CPU 空闲率：97.6%
- 用户空间：1.5%
- 系统空间：0.8%
- **结论：CPU 使用率正常，不是 100%**

### 内存状态：⚠️ 使用率较高
- 总内存：1613.1 MB
- 已使用：1134.9 MB (70%)
- 空闲：76.9 MB
- **结论：内存使用率较高，需要关注**

### 负载平均值：⚠️ 略高
- 1 分钟：1.06
- 5 分钟：1.21
- 15 分钟：0.53
- **结论：对于 2 核系统，负载略高但可接受**

## 需要执行的检查命令

### 1. 检查 Gunicorn 进程是否存在
```bash
ps aux | grep gunicorn | grep -v grep
```

### 2. 如果 gunicorn 不存在，检查服务状态
```bash
sudo systemctl status mytravelpanel
```

### 3. 查看完整的进程列表（按 CPU 排序）
```bash
ps aux --sort=-%cpu | head -30
```

### 4. 查看内存占用最高的进程
```bash
ps aux --sort=-%mem | head -20
```

### 5. 检查是否有 gunicorn 进程但 CPU 很高
```bash
# 查看所有 gunicorn 相关进程
ps aux | grep -E "gunicorn|python.*app_new" | grep -v grep

# 如果找到进程，查看其详细信息
ps -eo pid,ppid,cmd,%mem,%cpu,etime --sort=-%cpu | grep gunicorn
```

### 6. 检查系统日志
```bash
# 查看服务日志
sudo journalctl -u mytravelpanel -n 50 --no-pager

# 查看最近的错误
sudo journalctl -u mytravelpanel --since "10 minutes ago" | grep -i error
```

## 可能的情况

### 情况 1: Gunicorn 服务未运行
如果 `ps aux | grep gunicorn` 没有输出，说明服务可能：
- 崩溃了
- 被手动停止了
- 启动失败

**解决：**
```bash
# 检查服务状态
sudo systemctl status mytravelpanel

# 如果服务失败，查看日志
sudo journalctl -u mytravelpanel -n 100

# 尝试启动服务
sudo systemctl start mytravelpanel

# 查看启动日志
sudo journalctl -u mytravelpanel -f
```

### 情况 2: Gunicorn 进程存在但不在 top 前几行
可能进程 CPU 使用率已经降下来了。

**检查：**
```bash
# 查看所有 gunicorn 进程的 CPU 使用率
ps aux | grep gunicorn | grep -v grep | awk '{print $2, $3, $11}'
```

### 情况 3: CPU 高是间歇性的
可能之前 CPU 高，现在已经降下来了。

**监控：**
```bash
# 持续监控 1 分钟
for i in {1..12}; do
    echo "=== $(date) ==="
    ps aux --sort=-%cpu | head -10
    echo ""
    sleep 5
done
```

## 内存优化建议

当前内存使用率 70%，需要注意：

### 1. MySQL 内存占用（423MB）
这是正常的，MySQL 会使用较多内存。

### 2. 检查是否有内存泄漏
```bash
# 查看内存占用最高的进程
ps aux --sort=-%mem | head -10

# 监控内存使用趋势
watch -n 5 'free -h'
```

### 3. 如果内存不足，可以：
- 减少 Gunicorn worker 数量
- 优化 MySQL 配置
- 增加 swap 空间（当前为 0）

## 下一步操作

根据检查结果：

1. **如果 gunicorn 未运行**：启动服务并检查日志
2. **如果 gunicorn 运行但 CPU 正常**：继续监控，可能问题已解决
3. **如果 gunicorn 运行但 CPU 仍高**：应用之前的修复并重启

