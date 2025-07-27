# 用户认证系统设计

## 系统概述

为 MyTravelPanel 设计一个完整的用户认证和权限管理系统，支持访客浏览、用户注册登录、管理员权限等功能。

## 用户角色设计

### 1. 访客 (Guest)
- **权限**: 仅可浏览公开页面
- **功能**:
  - 查看旅游产品介绍
  - 浏览签证类型信息
  - 查看公司介绍
  - 联系信息查看

### 2. 注册用户 (Registered User)
- **权限**: 基础功能访问
- **功能**:
  - 所有访客功能
  - 个人资料管理
  - 查看自己的项目
  - 基础数据查询

### 3. 高级用户 (Premium User)
- **权限**: 扩展功能访问
- **功能**:
  - 所有注册用户功能
  - 创建和管理项目
  - 文件上传下载
  - 报表查看

### 4. 管理员 (Admin)
- **权限**: 系统管理权限
- **功能**:
  - 所有高级用户功能
  - 用户管理
  - 系统配置
  - 数据管理

### 5. 超级管理员 (Super Admin)
- **权限**: 完全系统控制
- **功能**:
  - 所有管理员功能
  - 系统备份恢复
  - 权限分配
  - 系统监控

## 数据模型设计

### User 模型
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # 关系
    role = db.relationship('Role', backref='users')
    profile = db.relationship('UserProfile', backref='user', uselist=False)
```

### Role 模型
```python
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    permissions = db.Column(db.JSON)  # 存储权限列表
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### UserProfile 模型
```python
class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(100))
    position = db.Column(db.String(50))
    avatar = db.Column(db.String(255))
    preferences = db.Column(db.JSON)
```

## 权限系统设计

### 权限定义
```python
PERMISSIONS = {
    # 基础权限
    'view_public': '查看公开页面',
    'view_profile': '查看个人资料',
    'edit_profile': '编辑个人资料',
    
    # 项目权限
    'view_projects': '查看项目',
    'create_projects': '创建项目',
    'edit_projects': '编辑项目',
    'delete_projects': '删除项目',
    
    # 签证权限
    'view_visa_types': '查看签证类型',
    'manage_visa_types': '管理签证类型',
    'view_visa_projects': '查看签证项目',
    'manage_visa_projects': '管理签证项目',
    
    # 机票权限
    'view_flight_projects': '查看机票项目',
    'manage_flight_projects': '管理机票项目',
    
    # 旅游权限
    'view_tour_projects': '查看旅游项目',
    'manage_tour_projects': '管理旅游项目',
    
    # 公司权限
    'view_companies': '查看公司信息',
    'manage_companies': '管理公司信息',
    
    # 财务权限
    'view_financial': '查看财务信息',
    'manage_financial': '管理财务信息',
    
    # 系统权限
    'manage_users': '管理用户',
    'manage_roles': '管理角色',
    'system_config': '系统配置',
    'view_logs': '查看日志',
}
```

### 角色权限分配
```python
ROLE_PERMISSIONS = {
    'guest': [
        'view_public'
    ],
    'user': [
        'view_public',
        'view_profile',
        'edit_profile',
        'view_projects',
        'view_visa_types',
        'view_visa_projects',
        'view_flight_projects',
        'view_tour_projects',
        'view_companies'
    ],
    'premium': [
        'view_public',
        'view_profile',
        'edit_profile',
        'view_projects',
        'create_projects',
        'edit_projects',
        'view_visa_types',
        'view_visa_projects',
        'create_visa_projects',
        'edit_visa_projects',
        'view_flight_projects',
        'create_flight_projects',
        'edit_flight_projects',
        'view_tour_projects',
        'create_tour_projects',
        'edit_tour_projects',
        'view_companies',
        'view_financial'
    ],
    'admin': [
        'view_public',
        'view_profile',
        'edit_profile',
        'view_projects',
        'create_projects',
        'edit_projects',
        'delete_projects',
        'view_visa_types',
        'manage_visa_types',
        'view_visa_projects',
        'manage_visa_projects',
        'view_flight_projects',
        'manage_flight_projects',
        'view_tour_projects',
        'manage_tour_projects',
        'view_companies',
        'manage_companies',
        'view_financial',
        'manage_financial',
        'manage_users',
        'view_logs'
    ],
    'super_admin': [
        # 所有权限
    ]
}
```

## 页面访问控制

### 公开页面 (无需登录)
- `/` - 首页
- `/about` - 关于我们
- `/services` - 服务介绍
- `/contact` - 联系我们
- `/visa/types` - 签证类型浏览
- `/tours/public` - 公开旅游产品
- `/flights/public` - 公开机票信息

### 需要登录的页面
- `/dashboard` - 用户仪表板
- `/profile` - 个人资料
- `/projects/*` - 项目管理
- `/visa/projects/*` - 签证项目
- `/flight/projects/*` - 机票项目
- `/tour/projects/*` - 旅游项目

### 需要特定权限的页面
- `/admin/*` - 管理员页面
- `/system/*` - 系统管理
- `/financial/*` - 财务管理

## 认证流程

### 1. 用户注册
```
访客 → 填写注册信息 → 邮箱验证 → 激活账户 → 成为注册用户
```

### 2. 用户登录
```
用户 → 输入用户名密码 → 验证身份 → 创建会话 → 跳转到仪表板
```

### 3. 权限验证
```
请求 → 检查登录状态 → 验证权限 → 允许/拒绝访问
```

## 安全措施

### 1. 密码安全
- 密码加密存储 (bcrypt)
- 密码强度要求
- 定期密码更新提醒

### 2. 会话管理
- JWT Token 或 Session
- 会话超时设置
- 并发登录控制

### 3. 访问控制
- CSRF 保护
- XSS 防护
- SQL 注入防护

### 4. 日志记录
- 登录日志
- 操作日志
- 错误日志

## 实现计划

### 第一阶段：基础认证
1. 实现用户注册/登录
2. 基础权限控制
3. 访客浏览功能

### 第二阶段：权限管理
1. 角色权限系统
2. 用户管理界面
3. 权限验证中间件

### 第三阶段：管理员功能
1. 管理员仪表板
2. 系统配置
3. 用户管理

### 第四阶段：高级功能
1. 审计日志
2. 安全增强
3. 性能优化 