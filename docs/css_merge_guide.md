# CSS 合并指南 - staff_common.css 统一设计系统

## 概述

已将 `visa_common.css` 和 `staff_common.css` 合并为统一的 `staff_common.css`，实现全系统设计统一。

## 合并内容

### ✅ 已合并的组件

#### 从 visa_common.css 合并：
1. **CSS 变量系统**
   - `--visa-*` 系列变量（颜色、间距、圆角、阴影）
   - 紫色渐变主题变量

2. **容器布局**
   - `.visa-container` / `.visa-container-lg` / `.visa-container-sm`

3. **卡片组件**
   - `.visa-card` + `.visa-card-header` + `.visa-card-body` + `.visa-card-footer`
   - `.visa-card-simple` / `.visa-card-accent` / `.visa-card-hover`

4. **按钮系统**
   - `.visa-btn` + 颜色变体（primary/success/warning/danger/info/secondary）
   - `.visa-btn-sm` / `.visa-btn-lg`
   - `.visa-btn-link` 系列

5. **表格组件**
   - `.visa-table` 统一表格样式

6. **表单组件**
   - `.visa-form-control` / `.visa-form-select` / `.visa-form-textarea`
   - `.visa-form-label` / `.visa-form-group`

7. **徽章组件**
   - `.visa-badge` + 颜色变体

8. **筛选栏**
   - `.visa-filter-bar` / `.visa-search-box` / `.visa-filter-item`

9. **分页组件**
   - `.visa-pagination` / `.visa-pagination-btn`

10. **网格布局**
    - `.visa-grid` / `.visa-grid-2` / `.visa-grid-3` / `.visa-grid-4`
    - `.visa-grid-auto-fit` / `.visa-grid-responsive`

11. **工具类**
    - Flex 布局：`.visa-flex-*`
    - 间距：`.visa-mt-*` / `.visa-mb-*`
    - 文本对齐：`.visa-text-*`
    - Gap：`.visa-gap-*`

12. **其他组件**
    - `.visa-loading` 加载状态
    - `.visa-flash` 消息提示
    - `.visa-info-box` 信息框

#### 保留的 staff 特定组件：
1. 导航栏和侧边栏样式
2. Logo 样式
3. Profile 模块样式
4. 统计卡片 `.stats-card`
5. 项目卡片 `.project-card`
6. 任务卡片 `.task-card`
7. 文件上传 `.upload-area`
8. Modern 系列组件（`.common-btn`, `.form-modern` 等）

## 使用方法

### 1. 在模板中引入 CSS

**旧方式**（需要更新）：
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/visa_common.css') }}">
```

**新方式**（统一）：
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/staff_common.css') }}">
```

### 2. 组件使用示例

#### 卡片组件
```html
<div class="visa-card">
    <div class="visa-card-header">
        <h3><i class="fas fa-info-circle"></i> 标题</h3>
    </div>
    <div class="visa-card-body">
        内容
    </div>
</div>
```

#### 按钮组件
```html
<button class="visa-btn visa-btn-primary">主按钮</button>
<button class="visa-btn visa-btn-success visa-btn-lg">大按钮</button>
<button class="visa-btn visa-btn-danger visa-btn-sm">小按钮</button>
```

#### 表格组件
```html
<table class="visa-table">
    <thead>
        <tr>
            <th>列1</th>
            <th>列2</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>数据1</td>
            <td>数据2</td>
        </tr>
    </tbody>
</table>
```

#### 筛选栏
```html
<div class="visa-filter-bar">
    <div class="visa-search-box">
        <i class="fas fa-search"></i>
        <input type="text" class="visa-form-control" placeholder="搜索...">
    </div>
    <div class="visa-filter-item">
        <label class="visa-form-label">筛选</label>
        <select class="visa-form-select">
            <option>选项1</option>
        </select>
    </div>
</div>
```

#### 网格布局
```html
<div class="visa-grid-3">
    <div>项目1</div>
    <div>项目2</div>
    <div>项目3</div>
</div>
```

## 需要更新的模板文件

### 已更新：
- ✅ `App_new/templates/shared/supplier/supplier_list.html`
- ✅ `App_new/templates/shared/supplier/supplier_detail.html`

### 需要更新的模板（如果使用了 visa_common.css）：
```bash
# 搜索所有引用 visa_common.css 的文件
grep -r "visa_common.css" App_new/templates/
```

**批量替换方法**：
将所有 `visa_common.css` 引用替换为 `staff_common.css`

## 设计系统对照表

| 功能 | 旧类名 (多个系统) | 新类名 (统一) |
|------|------------------|--------------|
| 容器 | `.container-fluid` | `.visa-container-lg` |
| 卡片 | `.card` | `.visa-card` |
| 卡片头部 | `.card-header` | `.visa-card-header` |
| 卡片内容 | `.card-body` | `.visa-card-body` |
| 按钮 | `.btn .btn-primary` | `.visa-btn .visa-btn-primary` |
| 小按钮 | `.btn .btn-sm` | `.visa-btn .visa-btn-sm` |
| 表格 | `.table` | `.visa-table` |
| 表单控件 | `.form-control` | `.visa-form-control` |
| 下拉框 | `.form-select` | `.visa-form-select` |
| 徽章 | `.badge .bg-info` | `.visa-badge .visa-badge-info` |
| 分页 | `.pagination` | `.visa-pagination` |

## CSS 变量使用指南

### 颜色系统
```css
/* Staff 主题（绿色） */
var(--primary-color)      /* #28a745 */
var(--success-color)      /* #28a745 */

/* Visa 主题（蓝紫色） */
var(--visa-primary)       /* #1a56db */
var(--visa-success)       /* #10b981 */

/* 紫色渐变（Profile、Supplier 等） */
var(--visa-gradient-start)  /* #667eea */
var(--visa-gradient-end)    /* #764ba2 */
```

### 间距系统
```css
var(--visa-spacing-xs)    /* 0.5rem */
var(--visa-spacing-sm)    /* 1rem */
var(--visa-spacing-md)    /* 1.5rem */
var(--visa-spacing-lg)    /* 2rem */
```

### 圆角系统
```css
var(--visa-radius-sm)     /* 6px */
var(--visa-radius-md)     /* 10px */
var(--visa-radius-lg)     /* 15px */
```

### 阴影系统
```css
var(--visa-shadow-sm)     /* 小阴影 */
var(--visa-shadow-md)     /* 中阴影 */
var(--visa-shadow-lg)     /* 大阴影 */
var(--visa-shadow-hover)  /* 悬停阴影 */
```

## 优势

### ✅ 单一来源
- 所有样式统一管理
- 避免重复代码
- 易于维护和更新

### ✅ 向后兼容
- 保留了所有 staff 原有组件
- 保留了所有 visa 组件
- 不会影响现有页面

### ✅ 灵活性
- 可以混用 staff 和 visa 组件
- 支持多主题（绿色 Staff、紫色 Visa）
- 丰富的工具类

### ✅ 性能
- 减少 CSS 文件数量
- 减少 HTTP 请求
- 统一的浏览器缓存

## 迁移清单

- [ ] 检查所有使用 `visa_common.css` 的模板
- [ ] 将引用改为 `staff_common.css`
- [ ] 测试所有页面样式是否正常
- [ ] 删除或归档 `visa_common.css`（可选）

## 注意事项

1. **不要删除 visa_common.css**（暂时保留作为备份）
2. **逐步迁移**：先测试几个页面，确认无误后再全面推广
3. **清除浏览器缓存**：更新后需要强制刷新（Ctrl + F5）
4. **CSS 优先级**：如果有冲突，页面内联样式优先级最高

## 后续优化建议

1. **创建组件库文档** - 记录所有可用组件和使用方法
2. **建立设计规范** - 统一颜色、间距、圆角等使用规则
3. **代码审查** - 逐步将旧样式替换为新组件
4. **性能监控** - 监控 CSS 文件大小和加载时间

---

**更新日期**：2025-01-15  
**版本**：2.0  
**维护者**：开发团队

