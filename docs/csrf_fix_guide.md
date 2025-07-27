# CSRF令牌修复指南

## 🛡️ 问题描述

用户访问 `http://127.0.0.1:5000/auth/login` 时遇到：

```
HTTP 错误 400
Bad Request
The CSRF token is missing.
```

## ✅ 解决方案

### 1. CSRF配置验证

系统已正确配置CSRF保护：

**App/exts.py**:
```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

def init_exts(app):
    csrf.init_app(app)
```

**App/__init__.py**:
```python
from .exts import csrf
csrf.init_app(app)
```

### 2. 表单修复

#### ✅ 已修复的表单

1. **登录表单** (`App/templates/auth/login.html`)
```html
<form method="POST" class="auth-form" id="loginForm">
    <!-- CSRF令牌 -->
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- 其他表单字段 -->
</form>
```

2. **注册表单** (`App/templates/auth/register.html`)
```html
<form method="POST" class="auth-form" id="registerForm">
    <!-- CSRF令牌 -->
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- 其他表单字段 -->
</form>
```

3. **员工创建项目表单** (`App/templates/staff/create_project.html`)
```html
<form method="POST" class="needs-validation" novalidate>
    <!-- CSRF令牌 -->
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- 其他表单字段 -->
</form>
```

#### ⚠️ 需要修复的表单

脚本检测到32个文件包含未保护的POST表单，主要包括：

- 业务类型管理表单
- 公司信息管理表单
- 机票管理表单
- 配套管理表单
- 银行账单处理表单
- 签证项目管理表单
- 预订项目管理表单

### 3. 修复模板

对于所有包含 `method="POST"` 的表单，需要添加：

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

### 4. AJAX请求修复

如果使用AJAX提交表单，需要在请求头中包含CSRF令牌：

```javascript
// 方法1：从meta标签获取
const csrfToken = document.querySelector('meta[name=csrf-token]').getAttribute('content');

fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(data)
});

// 方法2：从隐藏字段获取
const csrfToken = document.querySelector('input[name="csrf_token"]').value;
```

### 5. 基础模板修复

确保 `base.html` 包含CSRF元标签：

```html
<head>
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <!-- 其他head内容 -->
</head>
```

## 🧪 测试结果

```bash
$ python scripts/fix_csrf_tokens.py

🛡️  CSRF令牌检查和修复工具
============================================================
🔒 检查CSRF配置...
  ✅ CSRF保护已配置
  ✅ CSRF已在应用中初始化

🧪 测试CSRF端点...
  ✅ 登录页面包含CSRF令牌
  ✅ 注册页面包含CSRF令牌
  ✅ 员工创建项目页面正确重定向
```

## 🎯 当前状态

### ✅ 已解决
- 用户认证系统（登录/注册）CSRF保护完整
- 员工功能关键表单已保护
- 新功能开发已按CSRF最佳实践实施

### ⚠️ 待处理
- 原有系统的32个表单需要逐步添加CSRF令牌
- 建议按优先级修复：
  1. 高频使用的管理表单
  2. 涉及敏感操作的表单
  3. 其他辅助功能表单

## 💡 最佳实践

1. **新表单开发**：始终包含CSRF令牌
2. **AJAX请求**：正确传递CSRF令牌
3. **API端点**：谨慎使用 `@csrf.exempt`
4. **测试**：定期运行CSRF检查脚本

## 🔗 相关文件

- `App/exts.py` - CSRF配置
- `App/__init__.py` - CSRF初始化
- `scripts/fix_csrf_tokens.py` - CSRF检查工具
- `App/templates/auth/` - 已修复的认证表单
- `App/templates/staff/` - 已修复的员工表单

---

**结论**：用户现在可以正常访问登录页面和其他认证功能。新开发的分层用户系统已完全支持CSRF保护。 