# CSS重构执行指南

## 🎯 目标

将所有staff模板的内联CSS迁移到共享样式文件，实现：
1. 代码复用，减少重复
2. 风格统一，提升用户体验
3. 易于维护，降低成本

---

## 📚 CSS文件体系

### 核心CSS文件

```
App_new/static/css/
├── staff_common.css (1893行)
│   ├── 全局变量和基础样式
│   ├── 导航栏和侧边栏
│   ├── 按钮系统（现代+传统）
│   ├── 表单系统（输入框、选择框、验证）
│   ├── 卡片组件（统计、项目、工具）
│   ├── 表格样式（现代+数据表格）
│   ├── 模态框、分页、徽章
│   ├── 提示消息、空状态
│   └── 完整响应式设计
│
└── home_common.css (632行)
    ├── 首页快速操作
    ├── 工具卡片（多色主题）
    └── 签证页面特定样式
```

### 模块专用CSS（待创建）

```
App_new/static/css/
├── visa_module.css - 签证模块特定样式
├── flight_module.css - 机票模块特定样式
└── project_module.css - 项目管理特定样式
```

---

## 🔧 重构步骤模板

### 步骤1：分析现有样式

检查模板文件的 `<style>` 标签内容：

```html
{% block extra_css %}
<style>
    /* 分析这里的样式 */
    .custom-container { ... }
    .special-button { ... }
</style>
{% endblock %}
```

**分类：**
- ✅ **通用样式** → 移到 `staff_common.css`
- ✅ **模块共享** → 移到模块CSS（如 `visa_module.css`）
- ⚠️ **页面特定** → 保留在模板中

### 步骤2：提取通用样式

**判断标准：**

| 样式类型 | 是否通用 | 处理方式 |
|---------|---------|----------|
| 按钮样式 | ✅ | 移到staff_common.css |
| 表单输入框 | ✅ | 移到staff_common.css |
| 表格样式 | ✅ | 移到staff_common.css |
| 卡片容器 | ✅ | 移到staff_common.css |
| 特殊布局 | ❌ | 保留在模板 |
| 页面特定动画 | ❌ | 保留在模板 |
| 业务逻辑相关 | ⚠️ | 移到模块CSS |

### 步骤3：更新模板引用

**Before:**
```html
{% block extra_css %}
<style>
    .container { max-width: 1200px; }
    .btn-custom { padding: 0.5rem 1rem; }
    .table-custom { width: 100%; }
    /* 100+ 行重复样式 */
</style>
{% endblock %}
```

**After:**
```html
{% block extra_css %}
<!-- 如果需要模块CSS -->
<link href="{{ url_for('static', filename='css/visa_module.css') }}" rel="stylesheet">

<style>
    /* 只保留页面特定的样式 */
    .special-layout-for-this-page-only {
        /* ... */
    }
</style>
{% endblock %}
```

### 步骤4：替换类名

将自定义类名替换为标准类名：

| 旧类名 | 新类名 | 说明 |
|-------|-------|------|
| `.btn-custom` | `.common-btn.btn-primary-modern` | 使用通用按钮 |
| `.my-input` | `.form-control-modern` | 使用通用输入框 |
| `.data-card` | `.card-modern` | 使用通用卡片 |
| `.my-table` | `.table-modern` | 使用通用表格 |

### 步骤5：测试验证

- [ ] 页面布局正常
- [ ] 响应式设计正常
- [ ] 交互功能正常
- [ ] 颜色主题一致

---

## 📖 常用样式速查

### 按钮

```html
<!-- 现代风格按钮 -->
<button class="common-btn btn-primary-modern">
    <i class="fas fa-save"></i> 保存
</button>

<button class="common-btn btn-success-modern">成功</button>
<button class="common-btn btn-warning-modern">警告</button>
<button class="common-btn btn-danger-modern">删除</button>

<!-- 传统风格按钮 -->
<button class="btn-staff btn-staff-primary">保存</button>

<!-- 轮廓按钮 -->
<button class="common-btn btn-outline-modern">取消</button>

<!-- 尺寸 -->
<button class="common-btn btn-primary-modern btn-sm-modern">小按钮</button>
<button class="common-btn btn-primary-modern btn-lg-modern">大按钮</button>
```

### 表单

```html
<div class="form-group-modern">
    <label class="form-label-modern required">姓名</label>
    <input type="text" class="form-control-modern" placeholder="请输入姓名">
    <div class="form-error-message">
        <i class="fas fa-exclamation-circle"></i> 必填项
    </div>
</div>

<div class="form-group-modern">
    <label class="form-label-modern">国家</label>
    <select class="form-select-modern">
        <option>请选择</option>
    </select>
</div>
```

### 卡片

```html
<div class="card-modern">
    <div class="card-header-modern">
        <h3>卡片标题</h3>
        <button class="common-btn btn-sm-modern">操作</button>
    </div>
    <div class="card-body-modern">
        内容区域
    </div>
    <div class="card-footer-modern">
        底部区域
    </div>
</div>

<!-- 统计卡片 -->
<div class="stat-card-modern">
    <div class="stat-card-header">
        <div>
            <div class="stat-card-value">128</div>
            <div class="stat-card-label">总项目数</div>
        </div>
        <div class="stat-card-icon blue">
            <i class="fas fa-project-diagram"></i>
        </div>
    </div>
</div>
```

### 表格

```html
<div class="table-responsive-modern">
    <table class="table-modern">
        <thead>
            <tr>
                <th>列1</th>
                <th>列2</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>数据1</td>
                <td>数据2</td>
                <td>
                    <div class="table-actions">
                        <button class="common-btn btn-warning-modern btn-sm-modern">编辑</button>
                        <button class="common-btn btn-danger-modern btn-sm-modern">删除</button>
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

### 提示消息

```html
<div class="alert-modern alert-success-modern">
    <i class="fas fa-check-circle"></i>
    <div>操作成功！</div>
</div>

<div class="alert-modern alert-warning-modern">
    <i class="fas fa-exclamation-triangle"></i>
    <div>请注意！</div>
</div>

<div class="alert-modern alert-danger-modern">
    <i class="fas fa-times-circle"></i>
    <div>操作失败！</div>
</div>
```

### 模态框

```html
<div class="modal-modern" id="myModal">
    <div class="modal-dialog-modern">
        <div class="modal-header-modern">
            <h3 class="modal-title-modern">标题</h3>
            <button class="modal-close-modern">&times;</button>
        </div>
        <div class="modal-body-modern">
            内容区域
        </div>
        <div class="modal-footer-modern">
            <button class="common-btn btn-secondary-modern">取消</button>
            <button class="common-btn btn-primary-modern">确定</button>
        </div>
    </div>
</div>
```

### 徽章

```html
<span class="badge-modern badge-primary-modern">进行中</span>
<span class="badge-modern badge-success-modern">已完成</span>
<span class="badge-modern badge-warning-modern">待处理</span>
<span class="badge-modern badge-danger-modern">已取消</span>
```

### 空状态

```html
<div class="empty-state-modern">
    <i class="fas fa-inbox"></i>
    <h3>暂无数据</h3>
    <p>还没有任何记录</p>
    <button class="common-btn btn-primary-modern">立即创建</button>
</div>
```

---

## ✅ 优化检查清单

完成每个模板优化后，检查：

- [ ] 删除了重复的通用样式
- [ ] 更新了类名为标准类名
- [ ] 保留了页面特定样式
- [ ] 测试了页面显示正常
- [ ] 测试了响应式布局
- [ ] 测试了交互功能
- [ ] 代码比之前更简洁

---

## 📝 实例：优化一个模板

### Before (200行)

```html
{% extends "shared/staff_base.html" %}

{% block extra_css %}
<style>
    .page-wrapper { max-width: 1200px; margin: 0 auto; }
    .my-btn { padding: 0.5rem 1rem; border-radius: 8px; }
    .my-table { width: 100%; border-collapse: collapse; }
    .my-card { background: white; padding: 1.5rem; }
    /* ... 100+ 行 */
</style>
{% endblock %}

{% block content %}
<div class="page-wrapper">
    <button class="my-btn">保存</button>
    <table class="my-table">...</table>
</div>
{% endblock %}
```

### After (100行)

```html
{% extends "shared/staff_base.html" %}

{% block extra_css %}
<style>
    /* 只保留页面特定样式 */
    .special-feature-only-for-this-page {
        /* 特殊布局 */
    }
</style>
{% endblock %}

{% block content %}
<div class="page-container">
    <button class="common-btn btn-primary-modern">
        <i class="fas fa-save"></i> 保存
    </button>
    <table class="table-modern">...</table>
</div>
{% endblock %}
```

**改进：**
- ✅ 删除100行重复样式
- ✅ 代码减少50%
- ✅ 可维护性提升
- ✅ 风格统一

---

## 🎨 设计原则

1. **一致性优先** - 相同功能使用相同样式
2. **语义化类名** - 类名要清晰表达用途
3. **响应式优先** - 确保移动端体验
4. **性能考虑** - 避免过度复杂的样式
5. **可维护性** - 样式应该易于理解和修改

---

*最后更新: 2025-10-11*

