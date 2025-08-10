# 登录锁定功能说明

## 功能概述

登录锁定功能是一个安全机制，当用户连续登录失败5次后，系统会自动锁定该账户24小时，防止暴力破解攻击。

## 主要特性

- **自动锁定**: 连续登录失败5次后自动锁定账户
- **时间锁定**: 默认锁定24小时，可配置
- **自动解锁**: 锁定时间到期后自动解锁
- **管理员控制**: 管理员可以手动解锁账户或重置失败次数
- **实时监控**: 管理员可以实时查看所有被锁定的账户

## 数据库字段

系统在 `auth_users` 表中添加了以下字段：

```sql
ALTER TABLE auth_users ADD COLUMN login_attempts INT DEFAULT 0 COMMENT '登录失败次数';
ALTER TABLE auth_users ADD COLUMN is_locked BOOLEAN DEFAULT FALSE COMMENT '账户是否被锁定';
ALTER TABLE auth_users ADD COLUMN locked_at DATETIME NULL COMMENT '账户锁定时间';
ALTER TABLE auth_users ADD COLUMN unlock_at DATETIME NULL COMMENT '账户解锁时间';
```

## 使用方法

### 1. 数据库迁移

运行迁移脚本添加新字段：

```bash
cd scripts
python add_login_lock_fields.py
```

### 2. 功能测试

测试登录锁定功能是否正常工作：

```bash
cd scripts
python test_login_lock.py
```

### 3. 管理员管理

管理员可以通过以下路径管理被锁定的账户：

- **路径**: `/admin/users/locked`
- **功能**: 查看所有被锁定的用户
- **操作**: 解锁账户、重置失败次数

## 用户界面

### 登录页面提示

- 登录失败时显示剩余尝试次数
- 账户被锁定时显示剩余锁定时间
- 提供清晰的错误信息

### 管理员界面

- 锁定用户列表页面
- 实时显示锁定状态和剩余时间
- 一键解锁和重置功能

## 配置选项

### 锁定阈值

默认设置为5次失败后锁定，可以在 `AuthUser.record_login_failure()` 方法中修改：

```python
# 在 App/models/auth.py 中
if self.login_attempts >= 5:  # 修改这个数字
    self.lock_account()
```

### 锁定时长

默认锁定24小时，可以在 `AuthUser.lock_account()` 方法中修改：

```python
# 在 App/models/auth.py 中
def lock_account(self, lock_duration_hours=24):  # 修改默认值
    from datetime import timedelta
    self.is_locked = True
    self.locked_at = datetime.utcnow()
    self.unlock_at = datetime.utcnow() + timedelta(hours=lock_duration_hours)
    db.session.commit()
```

## 安全考虑

### 防止绕过

- 锁定检查在密码验证之前进行
- 即使密码正确，被锁定的账户也无法登录
- 锁定状态存储在数据库中，无法通过清除缓存绕过

### 日志记录

- 记录每次登录尝试（成功/失败）
- 记录账户锁定和解锁时间
- 管理员可以查看完整的锁定历史

## 故障排除

### 常见问题

1. **字段不存在错误**
   - 确保运行了数据库迁移脚本
   - 检查数据库表结构

2. **锁定功能不工作**
   - 检查用户模型是否正确导入
   - 验证数据库连接

3. **管理员无法解锁账户**
   - 检查管理员权限
   - 确认路由配置正确

### 调试方法

使用测试脚本检查功能状态：

```bash
python scripts/test_login_lock.py
```

## 扩展功能

### 自定义锁定策略

可以实现更复杂的锁定策略：

- 基于IP地址的锁定
- 渐进式锁定时间
- 白名单用户免锁定

### 通知机制

- 账户被锁定时发送邮件通知
- 管理员解锁账户时通知用户
- 锁定状态变更的实时通知

## 技术实现

### 核心方法

- `is_account_locked()`: 检查账户是否被锁定
- `record_login_failure()`: 记录登录失败
- `record_login_success()`: 记录登录成功
- `lock_account()`: 锁定账户
- `unlock_account()`: 解锁账户
- `get_remaining_lock_time()`: 获取剩余锁定时间

### 数据库操作

- 使用事务确保数据一致性
- 自动时间戳更新
- 索引优化查询性能

## 维护建议

### 定期检查

- 监控被锁定账户数量
- 检查异常锁定模式
- 清理过期的锁定记录

### 性能优化

- 定期清理过期的锁定记录
- 优化查询性能
- 监控数据库负载

## 联系支持

如果在使用过程中遇到问题，请联系系统管理员或查看系统日志获取更多信息。
