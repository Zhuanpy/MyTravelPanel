# 旅游配套数据库表结构分析与重新设计

## 当前表结构分析

### 1. **tour_products** (TourProduct) ✅ **主要使用中**
**位置**: `App_new/business/tour/models/Packagemodels.py`
**用途**: 产品展示模板 - 用于生成PDF展示文档
**字段**:
- title, country, city
- itinerary, included, not_included
- price, duration
- created_at, updated_at

**使用场景**:
- ✅ `/tour_product_list` - 产品列表页
- ✅ `/tour_product_detail/<id>` - 产品详情页
- ✅ PDF导出功能
- ✅ 按国家/城市筛选

**评价**: **保留** - 这是展示型产品模板，用于客户查看和PDF导出

---

### 2. **travelproducts** (Product) ✅ **主要使用中**
**位置**: `App_new/business/tour/models/Packagemodels.py`
**用途**: 完整的旅游产品管理 - 包含详细的产品信息和定价
**字段**:
- 基本信息: city_name, company_name, product_name, product_type
- 行程信息: duration_days, departure_city, destination_city
- 人数限制: min_pax, max_pax
- 价格体系: base_price, single_room_supplement, child_price, infant_price, currency
- 详细描述: product_description, highlights, included_services, excluded_services
- 状态管理: product_status, created_at, valid_until
- 联系信息: contact_person, contact_phone, contact_email

**使用场景**:
- ✅ `/package/add_product` - 添加配套产品
- ✅ `/package/all_packages` - 配套列表展示
- ✅ `/package/more_packages/<country>` - 按国家查看配套
- ✅ 与 ProductCity 关联 (多对一)
- ✅ 与 ProductPrice, ProductItinerary 关联 (一对多)

**评价**: **保留** - 这是核心产品数据表，包含完整的产品管理功能

---

### 3. **tour_project** (TourProject) ✅ **项目管理使用中**
**位置**: `App_new/business/tour/models/TourProject.py`
**用途**: 旅游项目管理 - 管理具体的旅游项目订单
**字段**:
- project_name, project_hid, project_type
- project_status, budget, departure_date
- folder_name (关联文件系统)
- contact_person, contact_info, remarks
- created_at, updated_at

**关联**:
- 一对多: tour_group (一个项目可以有多个团)

**使用场景**:
- ✅ `/tour/projects/list` - 项目列表
- ✅ `/tour/projects/create` - 创建项目
- ✅ `/tour/projects/detail/<id>` - 项目详情
- ✅ 文件夹自动创建和管理

**评价**: **保留** - 项目管理核心表，用于管理实际的旅游订单

---

### 4. **tour_group** (TourGroup) ✅ **团队管理使用中**
**位置**: `App_new/business/tour/models/TourProject.py`
**用途**: 行程团信息 - 管理项目下的具体团队信息
**字段**:
- title, departure_date, return_date, pax
- agency (旅行社), operator (地接社)
- hotel_info, transport, meals, attractions
- included_items, excluded_items, important_notes
- group_code, group_status, created_by
- project_id (外键 -> tour_project)

**使用场景**:
- ✅ `/tour/groups/list` - 团队列表
- ✅ 行程单打印
- ✅ 确认函打印

**评价**: **保留** - 团队管理表，是项目管理的重要组成部分

---

### 5. **tour_product_data** (TourProductData) ❌ **未使用/重复**
**位置**: `App_new/shared/models/Accountsmodels.py`
**字段**:
- name, description, destination
- departure_date, return_date
- price, available_seats

**问题**:
- ❌ 只在模型中定义，**没有实际路由或页面使用**
- ❌ 字段与 `travelproducts` (Product) 高度重复
- ❌ 功能被 `Product` 表完全覆盖
- ❌ 放在 `Accountsmodels.py` 中，位置不合理

**评价**: **删除** - 完全未使用且重复

---

## 数据表关系图

```
┌─────────────────────┐
│   travelproducts    │ (Product) - 产品模板库
│  (核心产品数据)     │
└──────────┬──────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐
│   product_city      │ - 城市分类
└─────────────────────┘

┌─────────────────────┐
│   tour_products     │ (TourProduct) - 展示模板
│  (PDF展示专用)      │ 
└─────────────────────┘

┌─────────────────────┐
│   tour_project      │ (TourProject) - 项目管理
│  (实际订单项目)     │
└──────────┬──────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐
│   tour_group        │ (TourGroup) - 团队管理
│  (项目下的团队)     │
└─────────────────────┘

┌─────────────────────┐
│ tour_product_data   │ ❌ 未使用，建议删除
└─────────────────────┘
```

---

## 重新设计建议

### ✅ 保留表 (4个)

#### 1. **travelproducts** (Product)
- **用途**: 产品模板库
- **功能**: 存储可复用的旅游产品模板，包含完整的价格、行程等信息
- **优化**: 无需改动

#### 2. **tour_products** (TourProduct)
- **用途**: 展示专用模板
- **功能**: 简化的产品信息，用于快速生成PDF展示文档
- **优化**: 已添加 country, city 字段，支持筛选

#### 3. **tour_project** (TourProject)
- **用途**: 项目管理
- **功能**: 管理实际的旅游订单项目
- **优化**: 无需改动

#### 4. **tour_group** (TourGroup)
- **用途**: 团队管理
- **功能**: 管理项目下的具体团队
- **优化**: 无需改动

---

### ❌ 删除表 (1个)

#### **tour_product_data** (TourProductData)
- **原因**: 
  1. 没有任何路由或页面使用
  2. 功能完全被 `travelproducts` (Product) 覆盖
  3. 字段定义简陋且重复
  4. 位置放置不当 (在 Accountsmodels.py 中)

---

## 业务逻辑梳理

### 1. 产品管理流程
```
创建产品模板 (travelproducts)
    ↓
按城市/国家分类展示
    ↓
客户选择产品
    ↓
创建项目 (tour_project)
    ↓
创建团队 (tour_group)
    ↓
生成确认函/行程单
```

### 2. 展示文档流程
```
创建展示模板 (tour_products)
    ↓
按国家/城市筛选
    ↓
查看产品详情
    ↓
导出 PDF 展示文档
```

---

## 表的职责划分

| 表名 | 职责 | 使用场景 |
|------|------|----------|
| **travelproducts** | 产品模板库 | 配套管理、产品选择、价格报价 |
| **tour_products** | 展示模板 | PDF导出、客户展示、快速浏览 |
| **tour_project** | 项目管理 | 订单管理、项目跟踪、文件管理 |
| **tour_group** | 团队管理 | 行程管理、确认函生成、团队信息 |
| ~~tour_product_data~~ | ❌ 删除 | 无实际使用 |

---

## 迁移步骤

### 第一步：备份数据
```sql
-- 检查 tour_product_data 是否有数据
SELECT COUNT(*) FROM tour_product_data;

-- 如果有数据，导出备份
MYSQLDUMP -u root -p mytraveldb tour_product_data > tour_product_data_backup.sql
```

### 第二步：检查依赖
```sql
-- 检查是否有外键引用
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE
    REFERENCED_TABLE_NAME = 'tour_product_data';
```

### 第三步：删除表
```sql
-- 删除 tour_product_data 表
DROP TABLE IF EXISTS tour_product_data;
```

### 第四步：删除模型定义
- 从 `App_new/shared/models/Accountsmodels.py` 中删除 `TourProductData` 类

---

## 总结

### ✅ 保留的表 (合理分工)
1. **travelproducts** - 完整的产品管理（包含价格、行程等详细信息）
2. **tour_products** - 简化的展示模板（用于PDF导出和快速浏览）
3. **tour_project** - 项目管理（实际订单）
4. **tour_group** - 团队管理（项目下的具体团队）

### ❌ 删除的表
1. **tour_product_data** - 未使用且重复

### 优势
- ✅ 职责清晰：产品模板 vs 展示模板 vs 项目管理 vs 团队管理
- ✅ 避免重复：删除未使用的冗余表
- ✅ 易于维护：每个表有明确的用途
- ✅ 灵活扩展：可以根据需要添加新功能

