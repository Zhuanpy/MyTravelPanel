# MyTravelPanel 项目结构分析

## 项目概述
MyTravelPanel 是一个基于 Flask 的旅游管理系统，主要功能包括签证管理、机票管理、旅游项目管理等。

## 整体架构

```
MyTravelPanel/
├── App/                          # 主应用目录
│   ├── __init__.py              # Flask应用初始化
│   ├── app.py                   # 应用入口
│   ├── exts.py                  # 扩展配置
│   ├── code/                    # 核心业务逻辑
│   │   ├── FlightTicket/        # 机票相关功能
│   │   │   ├── ConvertFlight/   # 机票转换
│   │   │   └── TicketScalping/  # 机票抢票
│   │   ├── Invoice.py          # 发票管理
│   │   ├── Package/            # 旅游套餐
│   │   ├── Statement.py        # 财务报表
│   │   ├── utils/              # 工具函数
│   │   │   ├── cache.py        # 缓存管理
│   │   │   ├── flightradar24.py # 航班雷达
│   │   │   ├── screenshot_splitter.py # 截图分割
│   │   │   └── template/       # 模板工具
│   │   └── Visa/               # 签证相关
│   │       └── Others.py       # 其他签证功能
│   ├── forms/                   # 表单定义
│   │   ├── company_forms.py    # 公司表单
│   │   ├── eo_forms.py         # EO表单
│   │   └── ...                 # 其他表单
│   ├── models/                  # 数据模型
│   │   ├── account.py          # 账户模型
│   │   ├── Accountsmodels.py   # 账户相关模型
│   │   ├── Product/            # 产品模型
│   │   │   ├── BusinessType.py # 业务类型
│   │   │   ├── PackageBudget.py # 套餐预算
│   │   │   └── Visamodels.py   # 签证模型
│   │   └── projects/           # 项目模型
│   │       ├── BookingProject.py # 预订项目
│   │       └── TourProject.py  # 旅游项目
│   ├── routes/                  # 路由定义
│   │   ├── business_type.py    # 业务类型路由
│   │   ├── company.py          # 公司路由
│   │   ├── projects/           # 项目路由
│   │   │   ├── BookingProject/ # 预订项目路由
│   │   │   ├── FlightProjects/ # 机票项目路由
│   │   │   ├── TourProjects/   # 旅游项目路由
│   │   │   └── VisaProjects/   # 签证项目路由
│   │   └── Utils/              # 工具路由
│   │       ├── account.py      # 账户工具
│   │       └── statement.py    # 报表工具
│   ├── services/               # 服务层
│   │   ├── base_service.py     # 基础服务
│   │   └── flight_service.py   # 机票服务
│   ├── static/                 # 静态资源
│   │   ├── css/               # 样式文件
│   │   ├── Js/                # JavaScript文件
│   │   ├── images/            # 图片资源
│   │   ├── uploads/           # 上传文件
│   │   └── 资源/              # 中文资源
│   │       ├── Project/       # 项目资源
│   │       ├── Visa/          # 签证资源
│   │       └── 机票/          # 机票资源
│   ├── templates/              # 模板文件
│   │   ├── base.html          # 基础模板
│   │   ├── index.html         # 首页模板
│   │   ├── business_types/    # 业务类型模板
│   │   ├── company/           # 公司模板
│   │   ├── flights/           # 机票模板
│   │   ├── package/           # 套餐模板
│   │   ├── projects/          # 项目模板
│   │   ├── statement/         # 报表模板
│   │   ├── utils/             # 工具模板
│   │   └── visas/             # 签证模板
│   └── utils/                 # 应用工具
│       ├── background_tasks.py # 后台任务
│       └── cache.py           # 缓存工具
├── docs/                       # 文档目录
├── logs/                       # 日志目录
├── migrations/                 # 数据库迁移
├── scripts/                    # 脚本文件
├── 资源/                       # 项目资源
│   ├── Project/               # 项目资源
│   ├── 客户资料/              # 客户资料
│   ├── 旅游产品/              # 旅游产品
│   ├── 机票产品/              # 机票产品
│   ├── 签证/                  # 签证资源
│   └── 账单/                  # 账单资源
├── app.py                      # 应用启动文件
└── README.md                   # 项目说明
```

## 技术栈

### 后端
- **框架**: Flask (Python)
- **数据库**: SQLAlchemy ORM
- **迁移**: Alembic
- **认证**: Flask-Login (待实现)
- **表单**: Flask-WTF
- **缓存**: Redis (可选)

### 前端
- **模板引擎**: Jinja2
- **样式**: CSS3 + 自定义样式
- **JavaScript**: 原生JS + 部分库
- **图标**: FontAwesome
- **日期选择**: Flatpickr

### 数据库
- **主数据库**: PostgreSQL/MySQL
- **缓存**: Redis (可选)

## 核心功能模块

### 1. 签证管理模块
- 签证类型管理
- 签证项目管理
- 文档配置
- 模板文件管理
- HID/REF编号管理

### 2. 机票管理模块
- 机票预订
- 机票转换
- 机票抢票
- 航班信息查询

### 3. 旅游项目管理模块
- 旅游套餐管理
- 预订项目管理
- 客户管理
- 财务统计

### 4. 公司管理模块
- 公司信息管理
- 业务类型管理
- 员工管理

### 5. 财务管理模块
- 发票管理
- 财务报表
- 账单管理

## 数据模型关系

```
User (用户)
├── Account (账户)
├── Company (公司)
└── Role (角色)

VisaTypes (签证类型)
├── VisaSingaporeIdentity (新加坡身份)
├── VisaDocuments (签证文档)
└── VisaTemplateFiles (模板文件)

VisaProject (签证项目)
├── VisaLinks (签证链接)
└── VisaDocumentsList (文档列表)

FlightProject (机票项目)
├── FlightRef (机票参考)
└── FlightSegment (航班段)

TourProject (旅游项目)
├── TourRef (旅游参考)
└── TourSegment (旅游段)
```

## 当前状态

### 已实现功能
- ✅ 签证类型管理
- ✅ 签证项目管理
- ✅ 机票项目管理
- ✅ 旅游项目管理
- ✅ 公司管理
- ✅ 基础UI界面

### 待实现功能
- ❌ 用户认证系统
- ❌ 权限管理
- ❌ 管理员界面
- ❌ 访客浏览功能
- ❌ 数据安全保护 