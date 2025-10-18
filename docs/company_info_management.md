# 公司信息管理功能

## 📋 功能概述

完整的公司信息和Logo管理系统，支持在系统中管理公司基本信息和Logo，并在公司抬头等位置自动显示。

## 🎯 功能特性

### 1. 公司信息管理
- ✅ 公司名称
- ✅ 公司简介
- ✅ 联系电话
- ✅ 电子邮箱
- ✅ 公司地址
- ✅ 公司Logo上传

### 2. 访问入口

**位置：** 顶部导航栏 → **业务管理** → **公司信息管理**

或直接访问：`/company/edit`

### 3. Logo上传说明

- **支持格式：** JPG、PNG、GIF
- **建议尺寸：** 200x200 像素
- **存储路径：** `App_new/static/company/`
- **命名规则：** `company_logo_时间戳.扩展名`
- **实时预览：** 选择文件后立即显示预览

## 📁 文件结构

```
App_new/
├── shared/
│   └── routes/
│       └── own_company.py          # 公司信息路由
├── templates/
│   └── shared/
│       └── own_company/
│           ├── own_company_form.html              # 编辑表单
│           ├── own_company_header.html            # 公司抬头页面
│           └── own_company_header_component.html  # 公司抬头组件
├── static/
│   └── company/                    # Logo存储目录
│       └── company_logo_*.jpg
└── business/
    └── tour/
        └── models/
            └── Packagemodels.py    # CompanyInfo模型
```

## 🗄️ 数据库

### 表名：`company_info`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT | 主键ID |
| `company_name` | VARCHAR(100) | 公司名称 |
| `company_description` | TEXT | 公司简介 |
| `phone` | VARCHAR(20) | 联系电话 |
| `email` | VARCHAR(100) | 电子邮箱 |
| `address` | TEXT | 公司地址 |
| `logo_path` | VARCHAR(200) | Logo路径（相对于static）|
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

### 初始化数据库

```sql
-- 执行迁移脚本
SOURCE migrations/ensure_company_info_table.sql;
```

## 🚀 使用说明

### 1. 首次设置

1. 登录系统
2. 点击顶部导航 **业务管理** → **公司信息管理**
3. 填写公司基本信息
4. 上传公司Logo（可选）
5. 点击 **保存更改**

### 2. 更新信息

1. 进入公司信息管理页面
2. 修改需要更新的字段
3. 如需更新Logo，重新上传新Logo文件
4. 点击 **保存更改**

### 3. 在模板中使用

#### 方式1：使用公司抬头组件

```html
{% include 'shared/own_company/own_company_header_component.html' %}
```

#### 方式2：直接获取公司信息

```html
{% set company = get_company_info() %}
{% if company %}
    <div class="company-info">
        <h1>{{ company.company_name }}</h1>
        {% if company.logo_path %}
            <img src="{{ url_for('static', filename=company.logo_path) }}" 
                 alt="{{ company.company_name }}">
        {% endif %}
        <p>电话：{{ company.phone }}</p>
        <p>邮箱：{{ company.email }}</p>
        <p>地址：{{ company.address }}</p>
    </div>
{% endif %}
```

## 🔧 技术实现

### 1. Context Processor

所有模板可以直接调用 `get_company_info()` 函数：

```python
@own_company.app_context_processor
def inject_company_info():
    return dict(get_company_info=get_company_info)
```

### 2. Logo上传处理

```python
def edit_company_info():
    # Logo上传逻辑
    if 'logo' in request.files:
        logo = request.files['logo']
        if logo and logo.filename != '':
            # 生成唯一文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_filename = f'company_logo_{timestamp}{ext}'
            
            # 保存到 App_new/static/company/
            logo_path = os.path.join('company', new_filename)
            full_path = os.path.join('App_new', 'static', 'company', new_filename)
            
            # 保存文件
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            logo.save(full_path)
            
            # 保存相对路径到数据库
            company.logo_path = logo_path
```

### 3. 路径标准化

```python
def normalize_path(path):
    """统一路径格式，将反斜杠转换为正斜杠"""
    return path.replace('\\', '/')
```

## 📸 Logo显示位置

公司Logo和信息会自动显示在以下位置：

### 后台（员工系统）
1. ✅ **公司抬头页面** - 用于打印或展示
2. ✅ **公司抬头组件** - 可嵌入任何模板
3. ✅ **报价单/文档** - （通过组件引入）

### 前台（Public页面）
1. ✅ **导航栏Logo** - 自动显示在顶部导航栏
2. ✅ **页脚Logo和信息** - 自动显示在页面底部
3. ✅ **联系信息** - 电话、邮箱、地址自动从数据库读取
4. ✅ **关于我们页面** - 公司简介自动显示

## ⚠️ 注意事项

1. **Logo文件大小**
   - 建议不超过 2MB
   - 系统会自动处理，但过大文件影响加载速度

2. **路径问题**
   - Logo路径存储为相对路径（如：`company/company_logo_20251018_120000.jpg`）
   - 在模板中使用时会自动添加 `static/` 前缀

3. **唯一性**
   - 系统中只维护一条公司信息记录
   - 更新时会覆盖原有信息

4. **备份建议**
   - 定期备份 `App_new/static/company/` 目录
   - 导出公司信息数据

## 🐛 故障排查

### Logo不显示

1. 检查文件是否上传成功
   ```bash
   ls App_new/static/company/
   ```

2. 检查数据库路径
   ```sql
   SELECT logo_path FROM company_info;
   ```

3. 检查模板路径
   ```html
   <!-- 正确 -->
   <img src="{{ url_for('static', filename=company.logo_path) }}">
   
   <!-- 错误 -->
   <img src="{{ url_for('static', filename='static/' + company.logo_path) }}">
   ```

### 路径错误

如果Logo路径包含反斜杠或多余的前缀，运行：

```sql
UPDATE company_info 
SET logo_path = REPLACE(logo_path, '\\', '/');

UPDATE company_info 
SET logo_path = REPLACE(logo_path, 'App_new/static/', '');

UPDATE company_info 
SET logo_path = REPLACE(logo_path, 'static/', '');
```

## 📝 更新日志

### v1.1 (2025-10-18)
- ✅ 前台(Public)页面集成公司信息
- ✅ 前台导航栏和页脚自动显示Logo
- ✅ 前台联系信息自动从数据库读取
- ✅ 全局context processor支持
- ✅ 优化Logo显示逻辑

### v1.0 (2025-10-18)
- ✅ 初始版本发布
- ✅ 公司信息CRUD功能
- ✅ Logo上传和预览
- ✅ 导航菜单入口
- ✅ 模板context processor
- ✅ 公司抬头组件
- ✅ 路径标准化处理

## 🔜 未来计划

- [ ] 支持多个Logo（黑白版、彩色版等）
- [ ] Logo裁剪功能
- [ ] 公司资质文件管理
- [ ] 公司历史版本记录
- [ ] API接口支持

## 📞 技术支持

如有问题，请联系技术团队。

