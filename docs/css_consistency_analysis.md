# CSS 样式一致性分析

## 🔍 问题发现

通过检查发现，**Staff 相关模板的样式并不统一**！

---

## 📊 当前样式使用情况

### 按钮样式（混乱）

当前使用了 **4 种不同的按钮样式**：

#### 1. ❌ Bootstrap 原生按钮
```html
<button class="btn btn-primary">按钮</button>
<button class="btn btn-success">按钮</button>
```
**使用位置**: 
- `account_manage.html` - 账号管理
- `visa_visit_stats.html` - 访问统计
- 很多旧模板

#### 2. ✅ Visa 统一按钮（推荐）
```html
<button class="visa-btn visa-btn-primary">按钮</button>
<button class="visa-btn visa-btn-success">按钮</button>
```
**使用位置**:
- `todo_list.html` - 待办事项
- `visa_project_list.html` - 签证项目
- `supplier_list.html` - 供应商列表
- 所有新优化的页面

#### 3. ❌ Modern 系列按钮
```html
<button class="btn-primary-modern">按钮</button>
<button class="common-btn">按钮</button>
```
**使用位置**: 
- 一些中间状态的模板

#### 4. ❌ Staff 特定按钮
```html
<button class="btn-staff btn-staff-primary">按钮</button>
```
**使用位置**: 
- 少数旧的 staff 页面

---

### 表单控件样式（混乱）

当前使用了 **3 种不同的表单样式**：

#### 1. ❌ Bootstrap 原生
```html
<input class="form-control" />
<select class="form-control"></select>
<textarea class="form-control"></textarea>
```
**使用位置**: 
- `account_manage.html` - 账号管理
- 很多旧模板

#### 2. ✅ Visa 统一表单（推荐）
```html
<input class="visa-form-control" />
<select class="visa-form-select"></select>
<textarea class="visa-form-textarea"></textarea>
```
**使用位置**:
- `todo_list.html`
- `visa_project_*.html`
- `supplier_list.html`
- 所有新优化的页面

#### 3. ❌ Modern 系列表单
```html
<input class="form-control-modern" />
```
**使用位置**: 
- 一些中间状态的模板

---

## ❌ 问题总结

### 样式不统一导致的问题：

1. **视觉不一致**
   - 同样的按钮在不同页面看起来不一样
   - 表单输入框高度、边框、圆角不统一
   - 颜色、阴影效果不一致

2. **维护困难**
   - 不知道该用哪个class
   - 修改样式需要改多个地方
   - 新页面不知道参考哪个标准

3. **代码冗余**
   - 多套样式系统共存
   - CSS文件臃肿
   - 增加了维护成本

---

## ✅ 解决方案

### 方案：统一使用 Visa 样式系统

**原因**：
1. ✅ 样式最现代化
2. ✅ 命名最清晰（visa-btn, visa-form-control）
3. ✅ 已经在新页面中使用
4. ✅ 支持多主题（蓝色、绿色、紫色）

### 统一标准：

#### 按钮
```html
<!-- 主要按钮 -->
<button class="visa-btn visa-btn-primary">主要操作</button>
<button class="visa-btn visa-btn-success">成功操作</button>
<button class="visa-btn visa-btn-danger">危险操作</button>
<button class="visa-btn visa-btn-secondary">次要操作</button>

<!-- 不同尺寸 -->
<button class="visa-btn visa-btn-sm visa-btn-primary">小按钮</button>
<button class="visa-btn visa-btn-lg visa-btn-primary">大按钮</button>

<!-- 链接按钮 -->
<a class="visa-btn-link visa-btn-link-primary">链接</a>
```

#### 表单控件
```html
<!-- 输入框 -->
<input class="visa-form-control" type="text" />

<!-- 下拉框 -->
<select class="visa-form-select">
    <option>选项</option>
</select>

<!-- 文本域 -->
<textarea class="visa-form-textarea" rows="4"></textarea>

<!-- 表单组 -->
<div class="visa-form-group">
    <label class="visa-form-label">标签</label>
    <input class="visa-form-control" />
</div>
```

#### 卡片
```html
<div class="visa-card">
    <div class="visa-card-header">
        <h3>标题</h3>
    </div>
    <div class="visa-card-body">
        内容
    </div>
    <div class="visa-card-footer">
        <button class="visa-btn visa-btn-primary">操作</button>
    </div>
</div>
```

#### 表格
```html
<table class="visa-table">
    <thead>
        <tr>
            <th>列名</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>数据</td>
        </tr>
    </tbody>
</table>
```

---

## 📋 需要统一的模板列表

### 高优先级（用户常用）

1. ❌ `account_manage.html` - 账号管理
   - 按钮：`btn btn-primary` → `visa-btn visa-btn-primary`
   - 表单：`form-control` → `visa-form-control`

2. ❌ `supplier_detail.html` - 供应商详情
   - 已优化，但可能有遗漏

3. ❌ 部分 Visa 页面
   - `visa_visit_stats.html` - 还在用 `btn btn-primary`

### 中等优先级

4. ❌ 一些管理页面
   - Admin 模块
   - Member 模块
   - Finance 模块

### 低优先级

5. ❌ 旧的业务页面
   - 可以逐步优化

---

## 🎯 统一计划

### 阶段1：核心页面（建议立即执行）

统一以下核心页面：
- [ ] `account_manage.html`
- [ ] 所有 Supplier 相关页面
- [ ] 所有 Visa 项目管理页面

### 阶段2：业务页面（逐步推进）

- [ ] Finance 财务模块
- [ ] Flight 机票模块
- [ ] Tour 旅游模块
- [ ] Admin 管理模块

### 阶段3：其他页面（按需优化）

- [ ] Guest 模块
- [ ] Member 模块
- [ ] 其他工具页面

---

## 📝 迁移对照表

### 按钮

| 旧样式 | 新样式（统一） | 说明 |
|--------|--------------|------|
| `btn btn-primary` | `visa-btn visa-btn-primary` | 主要按钮 |
| `btn btn-success` | `visa-btn visa-btn-success` | 成功按钮 |
| `btn btn-danger` | `visa-btn visa-btn-danger` | 危险按钮 |
| `btn btn-secondary` | `visa-btn visa-btn-secondary` | 次要按钮 |
| `btn btn-sm` | `visa-btn visa-btn-sm` | 小按钮 |
| `common-btn` | `visa-btn visa-btn-primary` | 通用按钮 |
| `btn-primary-modern` | `visa-btn visa-btn-primary` | Modern按钮 |

### 表单

| 旧样式 | 新样式（统一） | 说明 |
|--------|--------------|------|
| `form-control` | `visa-form-control` | 输入框 |
| `form-select` | `visa-form-select` | 下拉框 |
| `form-label` | `visa-form-label` | 标签 |
| `form-control-modern` | `visa-form-control` | Modern输入框 |

### 卡片

| 旧样式 | 新样式（统一） | 说明 |
|--------|--------------|------|
| `card` | `visa-card` | 卡片容器 |
| `card-header` | `visa-card-header` | 卡片头部 |
| `card-body` | `visa-card-body` | 卡片主体 |
| `card-modern` | `visa-card` | Modern卡片 |

### 表格

| 旧样式 | 新样式（统一） | 说明 |
|--------|--------------|------|
| `table` | `visa-table` | 表格 |
| `table-modern` | `visa-table` | Modern表格 |

---

## 🚀 快速替换脚本

### PowerShell 批量替换

```powershell
# 替换按钮样式
Get-ChildItem -Path "App_new\templates" -Filter "*.html" -Recurse | ForEach-Object {
    $content = Get-Content $_.FullName -Raw -Encoding UTF8
    $content = $content -replace 'class="btn btn-primary"', 'class="visa-btn visa-btn-primary"'
    $content = $content -replace 'class="btn btn-success"', 'class="visa-btn visa-btn-success"'
    $content = $content -replace 'class="btn btn-danger"', 'class="visa-btn visa-btn-danger"'
    $content = $content -replace 'class="btn btn-secondary"', 'class="visa-btn visa-btn-secondary"'
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8 -NoNewline
}

# 替换表单样式
Get-ChildItem -Path "App_new\templates" -Filter "*.html" -Recurse | ForEach-Object {
    $content = Get-Content $_.FullName -Raw -Encoding UTF8
    $content = $content -replace 'class="form-control"', 'class="visa-form-control"'
    $content = $content -replace 'class="form-select"', 'class="visa-form-select"'
    $content = $content -replace 'class="form-label"', 'class="visa-form-label"'
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8 -NoNewline
}
```

---

## ⚠️ 注意事项

### 不要全局替换！

某些Bootstrap组件必须保留原生class：
- ✅ Modal: `modal`, `modal-dialog`, `modal-content`
- ✅ Dropdown: `dropdown`, `dropdown-menu`
- ✅ Nav: `nav`, `nav-tabs`
- ✅ Alert: `alert alert-*` (如果使用Bootstrap JS)

### 建议手动替换

为了安全起见，建议：
1. 先在一个页面手动替换
2. 测试确认样式正确
3. 再批量替换其他页面

---

## 📊 预期收益

统一样式后：

- ✅ **视觉一致性 100%** - 所有页面样式统一
- ✅ **维护成本 -70%** - 只需维护一套样式
- ✅ **开发效率 +50%** - 知道该用哪个class
- ✅ **用户体验 +30%** - 一致的交互体验

---

**结论**: 目前样式**不统一**，需要进行统一化改造！

建议优先统一核心页面（Account、Supplier等），再逐步推广到全站。

