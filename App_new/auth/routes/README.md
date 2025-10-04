# Auth Routes 模块结构

## 文件组织

```
App_new/auth/routes/
├── __init__.py          # 路由注册和管理
├── member.py            # 会员认证功能（注册、登录）
├── staff.py             # 员工认证功能（登录）
├── admin.py             # 管理员认证功能（登录）
├── api.py               # 认证API接口（邮箱检查等）
├── common.py            # 通用认证功能（登出等）
└── README.md            # 本文档
```

## 功能划分

### member.py - 会员认证
- `POST /auth/member/login` - 会员登录
- `POST /auth/member/register` - 会员注册

### staff.py - 员工认证  
- `POST /auth/staff/login` - 员工登录

### admin.py - 管理员认证
- `POST /auth/admin/login` - 管理员登录

### api.py - 认证API
- `GET /auth/api/check-email` - 检查邮箱是否可用

### common.py - 通用功能
- `GET /auth/logout` - 用户登出

## 使用方式

在应用初始化时调用：
```python
from App_new.auth import init_auth
init_auth(app)
```

这将自动注册所有认证相关的路由到应用中。
