# MyTravelPanel 项目参考文档

> 生成日期: 2025-12-30

## 1. 项目概述

| 项目 | 说明 |
|------|------|
| **项目名称** | MyTravelPanel (Joyeful Escapes) |
| **类型** | 旅行行业企业管理系统 |
| **生产域名** | https://joyesc.com |
| **架构** | 模块化 Flask Web 应用 |
| **Python版本** | 3.10.7 |
| **数据库** | MySQL (travelindustry) |

---

## 2. 技术栈

### 2.1 核心框架
```
Flask 2.3.3              - Web框架
Flask-SQLAlchemy 3.0.5   - ORM数据库管理
Flask-Migrate 4.0.5      - 数据库迁移
Flask-Login 0.6.3        - 用户认证与授权
Flask-WTF 1.1.1          - 表单处理与CSRF保护
Flask-Mail 0.9.1         - 邮件发送
Flask-Caching 2.1.0      - 缓存管理
```

### 2.2 数据库
```
SQLAlchemy 2.0.21        - SQL工具包和ORM
PyMySQL 1.1.0            - MySQL数据库驱动
```

### 2.3 数据处理
```
Pandas 2.0.3             - 数据分析与处理
NumPy 1.24.3             - 数值计算
Pillow 10.3.0            - 图像处理
OpenPyXL 3.1.2           - Excel读写
Python-Docx 0.8.11       - Word文档处理
PyPDF2 3.0.1             - PDF处理
ReportLab 4.1.0          - PDF生成
```

### 2.4 爬虫与自动化
```
Selenium 4.21.0          - 浏览器自动化
Requests 2.31.0          - HTTP库
BeautifulSoup4 4.12.3    - HTML解析
WebDriver-Manager 4.0.2  - 浏览器驱动管理
```

### 2.5 定时任务
```
APScheduler              - 后台定时任务调度
```

### 2.6 前端
```
Tailwind CSS             - CSS框架
原生 JavaScript          - 交互逻辑
Jinja2 3.1.2             - 模板引擎
```

---

## 3. 项目目录结构

```
MyTravelPanel/
├── app_new.py                    # 应用入口
├── App_new/                      # 主应用目录
│   ├── __init__.py               # 应用工厂 (蓝图注册)
│   ├── config.py                 # 配置文件
│   ├── exts.py                   # Flask扩展初始化
│   │
│   ├── auth/                     # 认证模块
│   │   ├── models/               # 认证模型 (AuthUser, Role)
│   │   ├── routes/               # 认证路由
│   │   ├── decorators.py         # 权限装饰器
│   │   └── permissions.py        # 权限管理
│   │
│   ├── business/                 # 业务模块 (核心)
│   │   ├── projects/             # 项目管理
│   │   │   ├── models/           # 项目模型
│   │   │   ├── routes/           # 项目路由 (12个文件)
│   │   │   ├── forms/            # 项目表单
│   │   │   └── services/         # 项目服务
│   │   │
│   │   ├── flight/               # 机票模块
│   │   │   ├── models/           # 机票模型
│   │   │   ├── routes/           # 机票路由 (5个文件)
│   │   │   └── services/         # 机票服务
│   │   │
│   │   ├── tour/                 # 旅游产品模块
│   │   │   ├── models/           # 旅游模型
│   │   │   ├── routes/           # 旅游路由 (5个文件)
│   │   │   └── services/         # 旅游服务
│   │   │
│   │   └── visa/                 # 签证模块
│   │       ├── models/           # 签证模型
│   │       ├── routes/           # 签证路由 (9个文件)
│   │       └── services/         # 签证服务
│   │
│   ├── finance/                  # 财务模块
│   │   ├── models/               # 财务模型
│   │   ├── routes/               # 银行对账路由
│   │   └── services/             # 财务服务
│   │
│   ├── admin/                    # 管理后台
│   ├── member/                   # 会员模块
│   ├── staff/                    # 员工模块
│   ├── guest/                    # 游客/公众模块
│   │
│   ├── shared/                   # 共享模块
│   │   ├── models/               # 共享模型 (账户、供应商等)
│   │   ├── routes/               # 共享路由 (20个文件)
│   │   └── services/             # 共享服务
│   │
│   ├── utils/                    # 工具库 (46个文件)
│   │   ├── email.py              # 邮件服务
│   │   ├── scheduler.py          # 定时调度
│   │   ├── file.py               # 文件处理
│   │   ├── Invoice.py            # 发票生成
│   │   └── scrapers/             # 网页爬虫
│   │
│   ├── templates/                # HTML模板 (256个文件)
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── business/
│   │   ├── finance/
│   │   └── shared/
│   │
│   └── static/                   # 静态资源
│       ├── css/                  # 样式表 (17个)
│       ├── js/                   # JavaScript (18个)
│       └── images/               # 图片资源
│
├── migrations/                   # 数据库迁移脚本
├── docs/                         # 文档
├── scripts/                      # 工具脚本
├── logs/                         # 日志目录
├── 资源/                         # 业务资源文件
│   ├── Project/
│   ├── 旅游产品/
│   ├── 签证/
│   └── 账单/
│
├── requirements.txt              # Python依赖
├── .env                          # 环境配置
├── nginx.conf                    # Nginx配置
└── server_update.sh              # 服务器更新脚本
```

---

## 4. 核心功能模块

### 4.1 项目管理 (Projects)
- 项目列表、创建、编辑、详情
- 项目筛选与导出
- 项目成员管理
- REF (Reference) 明细管理
- EO (Executive Order) 合同管理
- 发票与收据管理
- 项目统计与分析

**关键路由文件:**
- `App_new/business/projects/routes/project_list.py` - 项目列表
- `App_new/business/projects/routes/project_detail.py` - 项目详情
- `App_new/business/projects/routes/project_ref.py` - REF管理

### 4.2 旅游产品 (Tour)
- 旅游项目管理
- 行程团管理
- 每日行程编辑
- 产品目录管理
- 预算分配与管理
- 人均预算计算

**关键路由文件:**
- `App_new/business/tour/routes/tour_projects.py` - 旅游项目
- `App_new/business/tour/routes/tour_package.py` - 旅游包
- `App_new/business/tour/routes/package_budget.py` - 预算管理

### 4.3 签证管理 (Visa)
- 签证项目创建与编辑
- 国家与签证类型管理
- 申请文件管理
- 文档链接管理
- 访问统计跟踪

**关键路由文件:**
- `App_new/business/visa/routes/visa_project.py` - 签证项目
- `App_new/business/visa/routes/visa_documents.py` - 文档管理

### 4.4 机票管理 (Flight)
- 机票项目管理
- 航班信息录入
- 乘客信息管理
- 航段管理
- Athina系统集成
- 航班日程表

**关键路由文件:**
- `App_new/business/flight/routes/flight_routes.py` - 机票管理
- `App_new/business/flight/routes/flights_athina_routes.py` - Athina集成

### 4.5 财务管理 (Finance)
- 银行对账单导入与处理
- 多银行支持 (CMB招商, OCBC, UOB)
- Athina系统预订数据导入
- 供应商对账
- 银行关键词分类

**关键路由文件:**
- `App_new/finance/routes/cmb_routes.py` - 招商银行
- `App_new/finance/routes/athina_routes.py` - Athina导入

### 4.6 其他模块
| 模块 | 功能 |
|------|------|
| **admin** | 用户管理、角色管理、权限控制 |
| **member** | 会员信息、订单管理 |
| **staff** | 员工信息管理 |
| **shared** | 公司信息、供应商、账户、待办事项 |

---

## 5. 数据模型关系

### 5.1 项目核心三层结构
```
ProjectHeader (项目主表)
├── CustomerCompany (客户公司)
├── Customer (客户)
├── ProjectMember (项目成员)
├── ProjectRef (项目明细) ─── 二级表
│   ├── ProjectFlightPassenger (机票乘客) ─── 三级表
│   └── ProjectFlightSegment (机票航段) ─── 三级表
├── ProjectEO (EO合同)
├── ProjectInvoice (发票)
└── ProjectReceipt (收据)
```

### 5.2 旅游模块
```
TourProject (旅游项目)
├── TourGroup (行程团)
│   ├── TourItinerary (每日行程)
│   └── BudgetHeader (预算主表)
│       └── BudgetItem (预算明细)
├── Product (产品)
└── ProductCity (城市)
```

### 5.3 签证模块
```
VisaProject (签证项目)
├── VisaCountries (国家)
├── VisaTypes (签证类型)
└── VisaSingaporeIdentity (身份信息)
```

### 5.4 财务模块
```
BankStatement (银行对账单)
├── BankTransaction (银行交易)
└── BankStatementKeyword (关键词)

AthinaBookingHeader (Athina预订)
└── AthinaBookingDetail (预订明细)
```

### 5.5 共享模型
```
Account (账户)
Supplier (供应商)
├── SupplierService (服务)
├── SupplierPrice (价格)
├── SupplierContract (合同)
└── SupplierPayment (付款)

BusinessType (业务类型)
Todo (待办事项)
└── TodoChecklist (检查表)
```

---

## 6. 认证与权限

### 6.1 用户类型
- 管理员 (Admin)
- 员工 (Staff)
- 会员 (Member)
- 游客 (Guest)

### 6.2 权限装饰器
```python
@login_required          # 需要登录
@staff_only              # 仅员工
@admin_only              # 仅管理员
@permission_required()   # 自定义权限
```

### 6.3 认证流程
- 登录入口: `/auth/login`
- 管理员登录: `/auth/admin-login`
- 会员登录: `/auth/member-login`

---

## 7. 定时任务

| 任务 | 频率 | 说明 |
|------|------|------|
| 待办事项提醒 | 每15分钟 | 检查并发送邮件提醒 |
| 自动生成任务 | 每天凌晨2点 | 生成新的提醒任务 |

配置文件: `App_new/utils/scheduler.py`

---

## 8. 配置说明

### 8.1 环境变量 (.env)
```bash
# 数据库
DB_USER=root
DB_PASSWORD=xxx
DB_HOST=47.84.177.3
DB_PORT=3306
DB_NAME=travelindustry

# Flask
SECRET_KEY=xxx
FLASK_ENV=development

# 邮件
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=xxx
MAIL_PASSWORD=xxx

# 待办通知
TODO_NOTIFICATION_ENABLED=True
```

### 8.2 应用配置
- 数据库连接池: `pool_size=10, max_overflow=20`
- 会话有效期: 7天
- 文件上传限制: 16MB

---

## 9. 代码统计

| 类型 | 数量 |
|------|------|
| Python代码 | 8,585+ 行 |
| HTML模板 | 256 个 |
| CSS文件 | 17 个 |
| JavaScript文件 | 18 个 |
| 路由文件 | 73 个 |
| 模型文件 | 40+ 个 |
| 工具模块 | 46 个 |

---

## 10. 关键文件路径

| 文件 | 说明 |
|------|------|
| `app_new.py` | 应用入口 |
| `App_new/__init__.py` | 应用工厂与蓝图注册 |
| `App_new/config.py` | 应用配置 |
| `App_new/exts.py` | Flask扩展初始化 |
| `requirements.txt` | Python依赖 |
| `.env` | 环境配置 |
| `nginx.conf` | Nginx配置 |
| `migrations/` | 数据库迁移 |

---

## 11. 部署信息

### 11.1 服务器
- 使用 Nginx 反向代理
- 配置文件: `nginx.conf`
- 更新脚本: `server_update.sh`

### 11.2 日志
- 日志目录: `logs/`
- 查看指南: `查看服务器日志指南.md`

---

## 12. 开发规范

### 12.1 模块结构
每个业务模块应包含:
```
module/
├── models/       # 数据模型
├── routes/       # 路由处理
├── forms/        # 表单定义
├── services/     # 业务逻辑
└── __init__.py   # 蓝图注册
```

### 12.2 命名规范
- 路由文件: `{功能}_routes.py`
- 模型文件: `{实体}.py`
- 服务文件: `{功能}_service.py`
- 表单文件: `{功能}_forms.py`

### 12.3 模板组织
```
templates/
└── {module}/
    ├── list.html
    ├── detail.html
    ├── create.html
    └── edit.html
```

---

*本文档由 Claude Code 自动生成*
