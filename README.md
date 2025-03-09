# MyTravelPanel

一个用于管理旅行社业务的 Web 应用程序。

## 功能特点

- 签证申请管理
- 航班预订管理
- 旅游产品管理
- 文件资源管理
- 供应商管理

## 技术栈

- Python Flask
- SQLAlchemy
- HTML/CSS/JavaScript
- Bootstrap

## 安装说明

1. 克隆仓库
```bash
git clone [repository-url]
cd MyTravelPanel
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 初始化数据库
```bash
flask db upgrade
```

5. 运行应用
```bash
flask run
```

## 项目结构

```
MyTravelPanel/
├── App/
│   ├── static/
│   ├── templates/
│   ├── routes/
│   ├── models/
│   └── code/
├── migrations/
├── requirements.txt
└── README.md
```

## 配置说明

1. 复制 `.env.example` 文件为 `.env`
2. 修改 `.env` 文件中的配置信息

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License 