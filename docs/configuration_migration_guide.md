# 配置文件优化指南

## 当前问题

1. **配置分散**：敏感信息硬编码在 `config.py` 中
2. **环境变量缺失**：没有实际的 `.env` 文件
3. **重复配置**：两个 `config.py` 文件有重复内容

## 优化方案

### 推荐方案：环境变量 + 配置文件分离

```
项目根目录/
├── .env                    # 环境变量（敏感信息）
├── .env.example           # 环境变量模板
├── App_new/
│   └── config.py          # 应用配置（非敏感信息）
└── App/
    └── config.py          # 旧架构配置（逐步废弃）
```

## 实施步骤

### 1. 创建 .env 文件

在项目根目录创建 `.env` 文件：

```bash
# 数据库配置
DB_USER=root
DB_PASSWORD=***REMOVED****
DB_HOST=47.84.177.3
DB_PORT=3306
DB_NAME=travelindustry

# Flask 安全配置
SECRET_KEY=your_secure_secret_key_here

# 邮件服务器配置
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_email_password

# 域名配置
DOMAIN=joyesc.com
BASE_URL=https://joyesc.com

# Flask 环境
FLASK_ENV=development
```

### 2. 更新 .gitignore

确保 `.env` 文件不被提交到版本控制：

```gitignore
# 环境变量文件
.env
.env.local
.env.production
```

### 3. 替换配置文件

将 `App_new/config.py` 替换为 `App_new/config_optimized.py`

### 4. 验证配置

运行配置验证：

```python
from App_new.config import Config
Config.validate_config()
```

## 配置分类

### 环境变量（.env）- 敏感信息
- 数据库密码
- API密钥
- 邮件密码
- 密钥和令牌

### 配置文件（config.py）- 非敏感信息
- 路径配置
- 功能开关
- 默认值
- 业务逻辑配置

## 优势

1. **安全性**：敏感信息不进入版本控制
2. **灵活性**：不同环境使用不同配置
3. **维护性**：配置集中管理
4. **标准化**：符合12-Factor App原则

## 注意事项

1. **备份**：迁移前备份现有配置
2. **测试**：在测试环境验证配置
3. **文档**：更新部署文档
4. **团队**：通知团队成员配置变更

## 邮件功能测试

配置完成后，可以通过以下方式测试邮件功能：

1. 访问 `/utils/email-test/` 页面
2. 检查邮件配置
3. 测试邮件连接
4. 发送测试邮件



