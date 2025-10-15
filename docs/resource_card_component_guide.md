# 资源卡片组件使用指南

## 🎨 组件说明

从 `package_home` 页面提取的精美卡片样式，已集成到 `staff_common.css`。

这套组件提供了：
- ✅ 渐变背景卡片
- ✅ 彩色图标容器
- ✅ 分类标题（带左边框）
- ✅ 快速操作按钮
- ✅ 8种颜色主题

---

## 📦 组件1：资源卡片（Resource Card）

### 基础用法

```html
<div class="resource-card resource-card-blue">
    <div class="resource-card-header">
        <div class="resource-card-icon resource-icon-blue">
            <i class="fas fa-city"></i>
        </div>
        <h4 class="resource-card-title">城市资源管理</h4>
    </div>
    <p class="resource-card-description">
        管理旅游城市、景点和资源信息，为客户提供最新的目的地内容。
    </p>
    <div class="resource-card-footer">
        <a href="#" class="visa-btn visa-btn-primary visa-btn-sm">
            <i class="fas fa-arrow-right"></i> 前往管理
        </a>
        <span class="resource-card-stats">
            <i class="fas fa-users"></i> 12个城市
        </span>
    </div>
</div>
```

### 8种颜色主题

| 卡片类 | 图标类 | 按钮推荐 | 适用场景 |
|--------|--------|----------|----------|
| `resource-card-blue` | `resource-icon-blue` | `visa-btn-primary` | 资源、信息 |
| `resource-card-green` | `resource-icon-green` | `visa-btn-success` | 成功、环保 |
| `resource-card-pink` | `resource-icon-pink` | `visa-btn-danger` | 产品、女性 |
| `resource-card-purple` | `resource-icon-purple` | `visa-btn-primary` | 创意、设计 |
| `resource-card-yellow` | `resource-icon-yellow` | `visa-btn-warning` | 警告、待办 |
| `resource-card-indigo` | `resource-icon-indigo` | `visa-btn-info` | 项目、专业 |
| `resource-card-red` | `resource-icon-red` | `visa-btn-danger` | 重要、紧急 |
| `resource-card-orange` | `resource-icon-orange` | `visa-btn-warning` | 活力、热情 |

### 示例：不同颜色卡片

```html
<!-- 蓝色卡片 - 资源管理 -->
<div class="resource-card resource-card-blue">
    <div class="resource-card-header">
        <div class="resource-card-icon resource-icon-blue">
            <i class="fas fa-database"></i>
        </div>
        <h4 class="resource-card-title">数据管理</h4>
    </div>
    <p class="resource-card-description">管理系统数据...</p>
    <div class="resource-card-footer">
        <a href="#" class="visa-btn visa-btn-primary visa-btn-sm">进入</a>
        <span class="resource-card-stats">
            <i class="fas fa-chart-line"></i> 1000条
        </span>
    </div>
</div>

<!-- 绿色卡片 - 供应商 -->
<div class="resource-card resource-card-green">
    <div class="resource-card-header">
        <div class="resource-card-icon resource-icon-green">
            <i class="fas fa-truck"></i>
        </div>
        <h4 class="resource-card-title">供应商管理</h4>
    </div>
    <p class="resource-card-description">管理供应商信息...</p>
    <div class="resource-card-footer">
        <a href="#" class="visa-btn visa-btn-success visa-btn-sm">进入</a>
        <span class="resource-card-stats">
            <i class="fas fa-building"></i> 45个
        </span>
    </div>
</div>

<!-- 粉色卡片 - 产品展示 -->
<div class="resource-card resource-card-pink">
    <div class="resource-card-header">
        <div class="resource-card-icon resource-icon-pink">
            <i class="fas fa-gift"></i>
        </div>
        <h4 class="resource-card-title">产品展示</h4>
    </div>
    <p class="resource-card-description">展示旅游产品...</p>
    <div class="resource-card-footer">
        <a href="#" class="visa-btn visa-btn-danger visa-btn-sm">查看</a>
        <span class="resource-card-stats">
            <i class="fas fa-box"></i> 28个
        </span>
    </div>
</div>
```

---

## 📦 组件2：快速操作按钮（Quick Action Button）

### 基础用法

```html
<div class="visa-grid-auto-fit">
    <a href="#" class="quick-action-btn btn-blue">
        <i class="fas fa-folder"></i> 资源文件夹
    </a>
    <a href="#" class="quick-action-btn btn-green">
        <i class="fas fa-truck"></i> 供应商
    </a>
    <a href="#" class="quick-action-btn btn-purple">
        <i class="fas fa-images"></i> 产品展示
    </a>
</div>
```

### 7种颜色变体

```html
<a href="#" class="quick-action-btn btn-blue">蓝色按钮</a>
<a href="#" class="quick-action-btn btn-green">绿色按钮</a>
<a href="#" class="quick-action-btn btn-purple">紫色按钮</a>
<a href="#" class="quick-action-btn btn-yellow">黄色按钮</a>
<a href="#" class="quick-action-btn btn-pink">粉色按钮</a>
<a href="#" class="quick-action-btn btn-indigo">靛蓝按钮</a>
<a href="#" class="quick-action-btn btn-red">红色按钮</a>
```

---

## 📦 组件3：分类标题（Category Header）

### 基础用法

```html
<div class="category-resources">
    <div class="category-header">
        <h3><i class="fas fa-database"></i> 资源管理</h3>
        <p>管理旅游目的地、供应商和产品信息</p>
    </div>
</div>
```

### 5种分类颜色

| 类名 | 左边框颜色 | 适用场景 |
|------|-----------|----------|
| `category-resources` | 蓝色 (#3b82f6) | 资源管理 |
| `category-management` | 绿色 (#10b981) | 项目管理 |
| `category-creation` | 黄色 (#f59e0b) | 创建/新建 |
| `category-info` | 青色 (#06b6d4) | 信息/统计 |
| `category-danger` | 红色 (#ef4444) | 危险/删除 |

### 示例

```html
<!-- 资源管理分类 - 蓝色 -->
<div class="category-resources">
    <div class="category-header">
        <h3><i class="fas fa-database"></i> 资源管理</h3>
        <p>管理各类系统资源</p>
    </div>
</div>

<!-- 项目管理分类 - 绿色 -->
<div class="category-management">
    <div class="category-header">
        <h3><i class="fas fa-tasks"></i> 项目管理</h3>
        <p>创建和管理项目，跟踪进度</p>
    </div>
</div>

<!-- 创建分类 - 黄色 -->
<div class="category-creation">
    <div class="category-header">
        <h3><i class="fas fa-plus"></i> 快速创建</h3>
        <p>快速创建新的资源和项目</p>
    </div>
</div>
```

---

## 🎯 完整示例

### 资源管理页面布局

```html
<div class="visa-container">
    <h1 class="visa-page-title">资源管理中心</h1>
    <p class="visa-text-center visa-text-muted visa-mb-4">统一管理系统资源</p>
    
    <!-- 快速操作 -->
    <div class="visa-card visa-mb-4">
        <div class="visa-card-header">
            <h2><i class="fas fa-bolt"></i> 快速操作</h2>
        </div>
        <div class="visa-card-body">
            <div class="visa-grid-auto-fit">
                <a href="#" class="quick-action-btn btn-blue">
                    <i class="fas fa-folder"></i> 资源文件夹
                </a>
                <a href="#" class="quick-action-btn btn-green">
                    <i class="fas fa-city"></i> 城市资源
                </a>
                <a href="#" class="quick-action-btn btn-purple">
                    <i class="fas fa-truck"></i> 供应商
                </a>
                <a href="#" class="quick-action-btn btn-pink">
                    <i class="fas fa-images"></i> 产品展示
                </a>
            </div>
        </div>
    </div>
    
    <!-- 资源管理分类 -->
    <div class="category-resources">
        <div class="category-header">
            <h3><i class="fas fa-database"></i> 资源管理</h3>
            <p>管理旅游目的地、供应商和产品信息</p>
        </div>
    </div>
    
    <div class="visa-grid-3">
        <!-- 城市资源卡片 -->
        <div class="resource-card resource-card-blue">
            <div class="resource-card-header">
                <div class="resource-card-icon resource-icon-blue">
                    <i class="fas fa-city"></i>
                </div>
                <h4 class="resource-card-title">城市资源管理</h4>
            </div>
            <p class="resource-card-description">
                管理旅游城市、景点和资源信息，为客户提供最新的目的地内容。
            </p>
            <div class="resource-card-footer">
                <a href="#" class="visa-btn visa-btn-primary visa-btn-sm">
                    <i class="fas fa-arrow-right"></i> 前往管理
                </a>
                <span class="resource-card-stats">
                    <i class="fas fa-users"></i> 12个城市
                </span>
            </div>
        </div>
        
        <!-- 供应商卡片 -->
        <div class="resource-card resource-card-green">
            <div class="resource-card-header">
                <div class="resource-card-icon resource-icon-green">
                    <i class="fas fa-truck"></i>
                </div>
                <h4 class="resource-card-title">供应商管理</h4>
            </div>
            <p class="resource-card-description">
                管理酒店、交通、餐饮等服务供应商信息，保持资源稳定。
            </p>
            <div class="resource-card-footer">
                <a href="#" class="visa-btn visa-btn-success visa-btn-sm">
                    <i class="fas fa-arrow-right"></i> 前往管理
                </a>
                <span class="resource-card-stats">
                    <i class="fas fa-building"></i> 45个供应商
                </span>
            </div>
        </div>
        
        <!-- 产品展示卡片 -->
        <div class="resource-card resource-card-pink">
            <div class="resource-card-header">
                <div class="resource-card-icon resource-icon-pink">
                    <i class="fas fa-images"></i>
                </div>
                <h4 class="resource-card-title">产品展示</h4>
            </div>
            <p class="resource-card-description">
                展示旅游产品信息，包括行程、价格与特色，吸引潜在客户。
            </p>
            <div class="resource-card-footer">
                <a href="#" class="visa-btn visa-btn-danger visa-btn-sm">
                    <i class="fas fa-arrow-right"></i> 前往管理
                </a>
                <span class="resource-card-stats">
                    <i class="fas fa-box"></i> 28个产品
                </span>
            </div>
        </div>
    </div>
</div>
```

---

## 🎨 视觉效果

### 卡片特点

1. **渐变背景** - 从浅色渐变到白色
2. **Hover效果** - 上浮 + 增强阴影
3. **彩色图标** - 圆角容器 + 对比色图标
4. **清晰层次** - 标题、描述、操作区分明显

### 颜色搭配建议

| 功能类型 | 推荐颜色 | 示例 |
|----------|----------|------|
| 数据/信息 | Blue | 城市资源、数据库 |
| 成功/环保 | Green | 供应商、完成状态 |
| 产品/女性 | Pink | 产品展示、客户 |
| 创意/设计 | Purple | 图片处理、设计 |
| 待办/警告 | Yellow | 待办事项、提醒 |
| 专业/项目 | Indigo | 项目管理、文档 |
| 重要/紧急 | Red | PDF处理、紧急 |
| 活力/热情 | Orange | 活动、推广 |

---

## 📐 网格布局

### 推荐布局

```html
<!-- 3列网格 - 适合功能卡片 -->
<div class="visa-grid-3">
    <div class="resource-card resource-card-blue">...</div>
    <div class="resource-card resource-card-green">...</div>
    <div class="resource-card resource-card-pink">...</div>
</div>

<!-- 自适应网格 - 根据屏幕自动调整 -->
<div class="visa-grid-auto-fit">
    <div class="resource-card">...</div>
    <div class="resource-card">...</div>
    <div class="resource-card">...</div>
</div>

<!-- 快速操作按钮网格 -->
<div class="visa-grid-auto-fit">
    <a href="#" class="quick-action-btn btn-blue">...</a>
    <a href="#" class="quick-action-btn btn-green">...</a>
</div>
```

---

## 🌈 组合使用

### 完整页面示例

```html
{% extends "staff_base.html" %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/staff_common.css') }}">
{% endblock %}

{% block content %}
<div class="visa-container">
    <h1 class="visa-page-title">资源中心</h1>
    
    <!-- 快速操作区 -->
    <div class="visa-card visa-mb-4">
        <div class="visa-card-header">
            <h2><i class="fas fa-bolt"></i> 快速操作</h2>
        </div>
        <div class="visa-card-body">
            <div class="visa-grid-auto-fit">
                <a href="#" class="quick-action-btn btn-blue">
                    <i class="fas fa-folder"></i> 文件夹
                </a>
                <a href="#" class="quick-action-btn btn-green">
                    <i class="fas fa-plus"></i> 新建
                </a>
            </div>
        </div>
    </div>
    
    <!-- 资源管理分类 -->
    <div class="category-resources">
        <div class="category-header">
            <h3><i class="fas fa-database"></i> 资源管理</h3>
            <p>管理系统资源和数据</p>
        </div>
    </div>
    
    <!-- 功能卡片 -->
    <div class="visa-grid-3">
        <div class="resource-card resource-card-blue">
            <div class="resource-card-header">
                <div class="resource-card-icon resource-icon-blue">
                    <i class="fas fa-city"></i>
                </div>
                <h4 class="resource-card-title">功能模块</h4>
            </div>
            <p class="resource-card-description">
                功能描述文字...
            </p>
            <div class="resource-card-footer">
                <a href="#" class="visa-btn visa-btn-primary visa-btn-sm">
                    前往
                </a>
                <span class="resource-card-stats">
                    <i class="fas fa-chart-line"></i> 统计
                </span>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

## 💡 使用技巧

### 1. 合理选择颜色

根据功能性质选择颜色：
- 📘 蓝色：资源、数据、信息类
- 🟢 绿色：供应商、成功、完成类
- 💗 粉色：产品、客户、女性化
- 🟣 紫色：创意、设计、图片类
- 🟡 黄色：待办、警告、提醒类
- 🔵 靛蓝：项目、专业、文档类
- 🔴 红色：PDF、重要、紧急类
- 🟠 橙色：活动、推广、热情类

### 2. 保持一致性

同一分类下的卡片使用相同颜色系：

```html
<div class="category-resources">
    <div class="category-header">...</div>
</div>

<!-- 同一分类用相同颜色 -->
<div class="visa-grid-3">
    <div class="resource-card resource-card-blue">...</div>
    <div class="resource-card resource-card-blue">...</div>
    <div class="resource-card resource-card-blue">...</div>
</div>
```

### 3. 统计信息可选

```html
<!-- 带统计信息 -->
<div class="resource-card-footer">
    <a href="#" class="visa-btn visa-btn-primary visa-btn-sm">进入</a>
    <span class="resource-card-stats">
        <i class="fas fa-users"></i> 12个
    </span>
</div>

<!-- 不带统计信息 -->
<div class="resource-card-footer">
    <a href="#" class="visa-btn visa-btn-primary visa-btn-sm">进入</a>
</div>
```

---

## 📱 响应式设计

组件已内置响应式设计：

- **桌面端（>768px）**：3列网格
- **平板端（≤768px）**：2列网格
- **手机端（≤480px）**：1列网格

图标和文字大小也会自动调整。

---

## ✅ 已应用的页面

1. ✅ `文件处理首页.html` - 文件处理服务
2. ✅ `package_home.html` - 配套管理（原始页面）

---

## 🎉 效果展示

使用这套组件后，页面将呈现：

- 🎨 **专业的视觉设计** - 渐变背景 + 彩色图标
- ✨ **流畅的动画效果** - Hover上浮 + 阴影变化
- 📱 **完美的响应式** - 自适应各种屏幕
- 🎯 **清晰的信息层次** - 图标、标题、描述、操作

---

**更新时间**：2025-01-15  
**组件来源**：package_home 页面  
**集成位置**：staff_common.css（第2123行起）

