# 邮件配置说明

## 问题诊断

您遇到的问题是：验证码已发送到邮箱，但实际没有收到邮件。

## 原因分析

1. **Flask-Mail未初始化** - 已在 `exts.py` 中修复
2. **邮件服务器配置缺失** - 已添加默认配置
3. **邮箱需要授权码** - 需要手动配置

## 解决方案

### 1. 阿里云企业邮箱配置（推荐）

#### 1.1 管理员设置
1. 登录阿里云企业邮箱管理员账号（通常是 `postmaster@您的域名`）
2. 进入"域管后台" → "安全管理" → "账号安全策略"
3. 关闭"禁止使用三方客户端"选项，允许SMTP发送邮件

#### 1.2 获取授权码
1. 使用员工邮箱账号登录阿里云企业邮箱
2. 进入"设置" → "账户与安全" → "三方客户端安全密码"
3. 按照提示生成并获取授权码

#### 1.3 环境变量配置
在项目根目录创建 `.env` 文件：

```env
# 阿里云企业邮箱配置
MAIL_SERVER=smtp.qiye.aliyun.com
MAIL_PORT=465
MAIL_USE_TLS=false
MAIL_USE_SSL=true
MAIL_USERNAME=your_email@yourcompany.com
MAIL_PASSWORD=你的阿里云企业邮箱授权码
MAIL_DEFAULT_SENDER=your_email@yourcompany.com
```

### 2. QQ邮箱配置

#### 2.1 获取授权码
1. 登录QQ邮箱 (651748264@qq.com)
2. 进入"设置" → "账户"
3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
4. 开启"SMTP服务"
5. 获取"授权码"（16位字符）

#### 2.2 环境变量配置
```env
MAIL_SERVER=smtp.qq.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=651748264@qq.com
MAIL_PASSWORD=你的QQ邮箱授权码
MAIL_DEFAULT_SENDER=651748264@qq.com
```

### 3. 临时测试配置

如果需要立即测试，可以修改 `config_optimized.py` 中的默认密码：

```python
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '你的QQ邮箱授权码')
```

## 测试邮件发送

运行测试脚本：

```bash
py test_email_config.py
```

## 注意事项

1. **安全性**：不要将授权码提交到版本控制系统
2. **垃圾邮件**：验证码邮件可能被标记为垃圾邮件，请检查垃圾邮件文件夹
3. **网络连接**：确保服务器可以访问QQ邮箱SMTP服务

## 其他邮箱配置

### 阿里云企业邮箱（备选服务器）
```env
MAIL_SERVER=smtp.mxhichina.com
MAIL_PORT=465
MAIL_USE_TLS=false
MAIL_USE_SSL=true
MAIL_USERNAME=your_email@yourcompany.com
MAIL_PASSWORD=your_authorization_code
```

### Gmail
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
```

### 163邮箱
```env
MAIL_SERVER=smtp.163.com
MAIL_PORT=25
MAIL_USE_TLS=false
MAIL_USE_SSL=false
MAIL_USERNAME=your_email@163.com
MAIL_PASSWORD=your_password
```

### 腾讯企业邮箱
```env
MAIL_SERVER=smtp.exmail.qq.com
MAIL_PORT=465
MAIL_USE_TLS=false
MAIL_USE_SSL=true
MAIL_USERNAME=your_email@yourcompany.com
MAIL_PASSWORD=your_authorization_code
```

## 故障排除

1. **检查控制台输出**：查看详细的错误信息
2. **检查网络连接**：确保可以访问SMTP服务器
3. **检查邮箱设置**：确认SMTP服务已开启
4. **检查授权码**：确保使用正确的授权码而非登录密码
