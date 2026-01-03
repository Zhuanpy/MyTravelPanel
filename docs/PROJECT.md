# MyTravelPanel 项目文档

## 项目概述

旅行业务管理系统，基于 Flask + MySQL，涵盖机票、酒店、签证、旅游等业务模块。

## 技术栈

- **后端**: Flask 2.3 + SQLAlchemy 2.0 + Flask-Login
- **数据库**: MySQL (PyMySQL)
- **前端**: Jinja2 模板 + Bootstrap
- **工具**: Pandas, OpenPyXL, ReportLab, Selenium

## 项目结构

```
App_new/
├── auth/           # 认证和权限
├── admin/          # 管理后台
├── business/       # 业务核心
│   ├── finance/    # 财务管理
│   ├── flight/     # 航班管理
│   ├── tour/       # 旅游产品
│   ├── visa/       # 签证服务
│   └── projects/   # 项目管理 (REF)
├── guest/          # 游客管理
├── member/         # 会员管理
├── staff/          # 员工管理
├── shared/         # 共享模块
├── utils/          # 工具库
├── templates/      # HTML模板
└── static/         # 静态资源

scripts/            # 脚本文件目录
docs/               # 文档目录
```

## 业务类型代码 (BusinessType)

| code | name | 说明 |
|------|------|------|
| flight | 机票 | 航空机票服务 |
| hotel | 酒店 | 酒店预订服务 |
| visa | 签证 | 签证申请服务 |
| tour | 旅游团 | 旅游团服务 |
| insurance | 保险 | 旅游保险服务 |
| transport | 交通 | 交通服务 |
| attraction | 景点/活动 | 景点门票和活动 |
| cruise | 邮轮 | 邮轮旅游服务 |
| other | 其他 | 其他服务 |

## 常用命令

```bash
# 运行开发服务器
python run.py

# 运行脚本
python scripts/sync_city_name_en.py

# 数据库迁移
python scripts/add_city_name_en.py
```
