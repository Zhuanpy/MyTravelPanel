# CSS 样式统一性状态报告

## ❌ 结论：目前**不统一**

虽然 `staff_common.css` 包含了所有样式定义，但模板中使用的CSS类名**非常混乱**！

---

## 📊 当前问题

### 问题1：按钮样式有 4 种不同写法

```html
<!-- 写法1: Bootstrap原生 -->
<button class="btn btn-primary">按钮</button>

<!-- 写法2: Visa统一系统 -->
<button class="visa-btn visa-btn-primary">按钮</button>

<!-- 写法3: Modern系列 -->
<button class="common-btn btn-primary-modern">按钮</button>

<!-- 写法4: Staff专用 -->
<button class="btn-staff btn-staff-primary">按钮</button>
```

**结果**: 同样功能的按钮，在不同页面看起来**完全不一样**！

---

### 问题2：表单控件有 3 种不同写法

```html
<!-- 写法1: Bootstrap原生 -->
<input class="form-control" />

<!-- 写法2: Visa统一系统 -->
<input class="visa-form-control" />

<!-- 写法3: Modern系列 -->
<input class="form-control-modern" />
```

**结果**: 输入框的**高度、边框、圆角**都不一样！

---

### 问题3：卡片组件有 3 种写法

```html
<!-- Bootstrap原生 -->
<div class="card">
    <div class="card-header">标题</div>
    <div class="card-body">内容</div>
</div>

<!-- Visa统一 -->
<div class="visa-card">
    <div class="visa-card-header">标题</div>
    <div class="visa-card-body">内容</div>
</div>

<!-- Modern系列 -->
<div class="card-modern">
    <div class="card-header-modern">标题</div>
    <div class="card-body-modern">内容</div>
</div>
```

---

## 🔍 实际使用情况

### 已统一的页面 ✅

这些页面已经使用 **Visa 统一样式**：

1. ✅ `supplier_list.html` - 供应商列表
2. ✅ `supplier_detail.html` - 供应商详情
3. ✅ `todo_list.html` - 待办事项
4. ✅ `visa_project_list.html` - 签证项目列表
5. ✅ `visa_project_detail.html` - 签证项目详情
6. ✅ `visa_project_create.html` - 签证项目创建
7. ✅ 大部分 Visa 管理页面

### 未统一的页面 ❌

这些页面仍在使用 **混杂的样式**：

1. ❌ `account_manage.html` - 账号管理（用 `form-control`, `btn btn-primary`）
2. ❌ `visa_visit_stats.html` - 访问统计（用 `btn btn-primary`）
3. ❌ 大部分 Admin 页面
4. ❌ 大部分 Finance 页面
5. ❌ 大部分 Member 页面
6. ❌ 很多旧的业务页面

---

## 💡 统一样式的好处

### 视觉一致性
- 所有按钮高度一致（40px）
- 所有输入框样式一致
- 所有卡片圆角、阴影一致
- **用户体验更专业！**

### 开发效率
- 只需记住一套class名
- 复制粘贴不会出错
- 新页面开发更快

### 维护成本
- 修改样式只需改一个地方
- 不会遗漏某些页面
- 更容易培训新人

---

## 🎯 推荐统一方案

### 统一使用：**Visa 样式系统**

**原因**:
1. ✅ 最现代化、最完整
2. ✅ 命名清晰（visa-btn, visa-form-control）
3. ✅ 已在新页面中使用
4. ✅ 支持所有功能

### 统一后的写法：

```html
<!-- 按钮 -->
<button class="visa-btn visa-btn-primary">主要按钮</button>
<button class="visa-btn visa-btn-success">成功按钮</button>
<button class="visa-btn visa-btn-sm visa-btn-primary">小按钮</button>

<!-- 表单 -->
<div class="visa-form-group">
    <label class="visa-form-label">标签</label>
    <input type="text" class="visa-form-control" />
</div>

<!-- 下拉框 -->
<select class="visa-form-select">
    <option>选项</option>
</select>

<!-- 卡片 -->
<div class="visa-card">
    <div class="visa-card-header"><h3>标题</h3></div>
    <div class="visa-card-body">内容</div>
    <div class="visa-card-footer">
        <button class="visa-btn visa-btn-primary">操作</button>
    </div>
</div>

<!-- 表格 -->
<table class="visa-table">
    <thead>
        <tr><th>列名</th></tr>
    </thead>
    <tbody>
        <tr><td>数据</td></tr>
    </tbody>
</table>
```

---

## 📋 执行计划

### 方案A：手动逐个优化（推荐，安全）

1. 先优化 `account_manage.html`
2. 测试确认无问题
3. 再优化其他页面

### 方案B：批量自动替换（快速，需谨慎）

使用脚本批量替换：
```bash
py scripts/unify_css_classes.py
```

**注意**: 会自动跳过关键文件（login, base等）

---

## 🚀 立即开始

要不要我帮你：
1. 先统一 `account_manage.html`？（核心页面）
2. 或者统一所有 staff 模板？（一次性解决）

---

**当前状态**: ❌ 不统一  
**建议行动**: 立即统一核心页面

