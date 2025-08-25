# -*- coding: utf-8 -*-
"""
├── finance/                     # 财务模块（独立）
│   ├── models/
│   │   ├── account.py          # 账户模型
│   │   ├── receipt.py          # 收款记录
│   │   ├── statement.py        # 账单模型
│   │   └── invoice.py          # 发票模型
│   ├── routes/
│   │   ├── account.py          # 账户管理路由
│   │   ├── statement.py        # 账单管理路由
│   │   ├── receipt.py          # 收款管理路由
│   │   └── reports.py          # 财务报表路由
│   ├── services/
│   │   ├── account_service.py  # 账户服务
│   │   ├── payment_service.py  # 支付服务
│   │   └── report_service.py   # 报表服务
│   └── templates/

"""