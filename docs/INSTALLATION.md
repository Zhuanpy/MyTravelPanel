# MyTravelPanel 安装指南

## 系统要求

- Python 3.8 或更高版本
- MySQL 数据库
- Git

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/Zhuanpy/MyTravelPanel.git
cd MyTravelPanel
```

### 2. 创建虚拟环境

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

1. 复制环境变量示例文件：
```bash
cp env.example .env
```

2. 编辑 `.env` 文件，配置以下信息：
   - 数据库连接信息
   - 邮件服务器配置
   - API密钥等敏感信息

### 5. 数据库设置

1. 创建MySQL数据库
2. 运行数据库迁移：
```bash
flask db upgrade
```

### 6. 运行应用

```bash
flask run
```

应用将在 `http://localhost:5000` 启动

## 常见问题

### 问题1: 找不到 background_tasks.py 文件

**原因**: 项目缺少 requirements.txt 文件，导致依赖包未正确安装

**解决方案**:
1. 确保已安装所有依赖：`pip install -r requirements.txt`
2. 检查虚拟环境是否正确激活
3. 重新克隆项目并安装依赖

### 问题2: 模块导入错误

**解决方案**:
1. 检查Python路径设置
2. 确保在项目根目录运行命令
3. 验证虚拟环境中的包安装情况

### 问题3: 数据库连接失败

**解决方案**:
1. 检查 `.env` 文件中的数据库配置
2. 确保MySQL服务正在运行
3. 验证数据库用户权限

## 开发环境设置

### 使用PyCharm

1. 打开PyCharm
2. 选择 "Open" 并选择项目文件夹
3. 配置Python解释器为项目的虚拟环境
4. 安装项目依赖

### 使用VS Code

1. 打开VS Code
2. 打开项目文件夹
3. 选择Python解释器（Ctrl+Shift+P → "Python: Select Interpreter"）
4. 安装项目依赖

## 项目结构

```
MyTravelPanel/
├── App/                    # 主应用目录
│   ├── config.py          # 配置文件（包含敏感信息）
│   ├── config_template.py # 配置模板（安全版本）
│   ├── utils/             # 工具模块
│   ├── models/            # 数据模型
│   ├── routes/            # 路由控制器
│   └── templates/         # 模板文件
├── requirements.txt        # 项目依赖
├── env.example           # 环境变量示例
├── .env                  # 环境变量文件（本地）
└── README.md            # 项目说明
```

## 安全注意事项

- 不要将 `.env` 文件提交到Git
- 不要将包含真实密码的 `config.py` 提交到Git
- 使用环境变量管理敏感信息
- 定期更新依赖包版本 