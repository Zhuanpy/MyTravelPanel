# 🏗️ TravelPanel 新架构启动指南

## 📋 概述

这是 TravelPanel 项目的重构版本，采用模块化设计，按业务领域分离关注点。

## 🚀 快速启动

### 1. 启动新架构应用
```bash
python app_new.py
```

### 2. 访问应用
- 地址: http://localhost:5000
- 架构版本: App_new (重构版)

## 📁 新架构目录结构

```
App_new/
├── __init__.py                 # 应用工厂
├── config.py                   # 配置文件
├── exts.py                     # 扩展管理
├── 
├── auth/                       # 认证模块
│   ├── models/                 # 认证相关模型
│   │   ├── __init__.py
│   │   ├── auth.py            # AuthUser, Role
│   │   └── User.py
│   ├── routes.py              # 认证路由
│   └── ...
├── 
├── finance/                    # 财务模块
│   ├── models/                 # 财务相关模型
│   │   ├── __init__.py
│   │   ├── project.py         # 项目、客户模型
│   │   ├── receipt.py         # 收款模型
│   │   ├── statement.py       # 对账模型
│   │   └── ...
│   ├── routes/
│   └── services/
├── 
├── business/                   # 业务模块
│   ├── flight/                 # 机票业务
│   │   ├── models/
│   │   │   └── flight.py      # 机票相关模型
│   │   ├── routes/
│   │   └── services/
│   ├── visa/                   # 签证业务
│   ├── tour/                   # 旅游业务
│   └── ...
├── 
├── shared/                     # 共享模块
│   ├── models/                 # 共享模型
│   │   ├── BusinessType.py    # 业务类型
│   │   ├── Suppliers.py       # 供应商
│   │   └── ...
│   ├── routes/
│   └── services/
├── 
├── member/                     # 会员模块
├── staff/                      # 员工模块  
├── admin/                      # 管理模块
├── guest/                      # 访客模块
└── utils/                      # 工具模块
```

## 🎯 架构原则

### 1. 模块化设计
- **按业务领域分离**: 每个模块负责特定的业务领域
- **单一职责**: 每个文件/类只负责一个明确的职责
- **松耦合**: 模块间通过明确的接口交互

### 2. 模型分布策略
- **业务模型**: 放在对应的业务模块中 (如 `business/flight/models/`)
- **核心模型**: 放在 `finance/models/` (项目、客户、收款等)
- **共享模型**: 放在 `shared/models/` (供应商、业务类型等)
- **认证模型**: 放在 `auth/models/`

### 3. 导入规范
- 使用相对导入: `from ...exts import db`
- 避免循环导入: 在需要时使用延迟导入
- 统一入口: 每个模块的 `__init__.py` 提供统一导入接口

## 📊 模型重构对比

### 原架构 (App/)
```
App/finance/models/receipt.py  (864行)
├── CustomerCompany
├── Customer  
├── ProjectHeader
├── ProjectRef
├── ProjectEO
├── RefOrderItem
├── ProjectFlightPassenger
├── ProjectFlightSegment
└── ProjectReceipt
```

### 新架构 (App_new/)
```
finance/models/
├── project.py          # CustomerCompany, Customer, ProjectHeader
├── receipt.py          # ProjectReceipt
└── statement.py        # 银行对账、供应商对账

business/flight/models/
└── flight.py           # ProjectFlightPassenger, ProjectFlightSegment

shared/models/
├── Suppliers.py        # 供应商相关
├── BusinessType.py     # 业务类型
└── ...
```

## ✅ 当前状态

### 已完成
- ✅ 应用工厂配置
- ✅ 数据库和扩展初始化  
- ✅ 基础配置管理
- ✅ 模型文件重构和分离
- ✅ 导入路径修复
- ✅ 基础启动功能

### 待完善
- 🔄 业务模块路由
- 🔄 模板文件组织
- 🔄 服务层实现
- 🔄 表单验证
- 🔄 权限控制

## 🔧 开发建议

### 1. 添加新功能
```python
# 在对应的业务模块中添加
business/your_module/
├── models/
├── routes/  
├── services/
├── forms/
└── templates/
```

### 2. 模型开发
```python
# 使用相对导入
from ...exts import db

# 避免循环导入
def get_related_data(self):
    from ..other_module.models import OtherModel
    return OtherModel.query.filter_by(...)
```

### 3. 路由注册
```python
# 在 __init__.py 中注册新的蓝图
from .business.your_module.routes import your_bp
app.register_blueprint(your_bp, url_prefix='/business/your_module')
```

## 🎉 总结

新架构成功实现了：
- 📦 **模块化设计**: 清晰的业务边界
- 🔧 **可维护性**: 单一职责，易于修改
- 🚀 **可扩展性**: 新功能可独立开发
- 👥 **团队协作**: 不同开发者可专注不同模块

下一步可以逐步迁移旧架构的路由和业务逻辑到新架构中！
