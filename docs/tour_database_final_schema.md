# 旅游配套数据库最终方案

## 📋 一、表单删除与保留决策

### ❌ 删除的表 (1个)

| 表名 | 删除理由 |
|------|---------|
| `tour_product_data` | 1. 完全未使用<br>2. 功能被 `travelproducts` 覆盖<br>3. 字段设计简陋 |

---

### ✅ 保留的表 (4个)

| 表名 | 用途 | 保留理由 |
|------|------|---------|
| `travelproducts` | 产品模板库 | 核心产品数据，包含完整的产品信息、价格体系 |
| `tour_products` | 展示模板 | PDF导出和客户展示专用，简化版产品信息 |
| `tour_project` | 项目管理 | 管理实际的旅游订单/项目 |
| `tour_group` | 团队管理 | 管理项目下的具体出团信息 |

---

## 📊 二、保留表的完整字段设计

### 1. `travelproducts` - 产品模板库（完整版）

**用途**: 存储可复用的旅游产品模板，是所有产品的数据源

```sql
CREATE TABLE travelproducts (
    -- ========== 基础信息 ==========
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(200) NOT NULL COMMENT '产品名称',
    city_name VARCHAR(100) NOT NULL COMMENT '城市名称',
    company_name VARCHAR(100) NOT NULL COMMENT '公司名称',
    
    -- ========== 产品分类 ==========
    product_type VARCHAR(50) COMMENT '产品类型：跟团游/自由行/定制游',
    difficulty_level VARCHAR(50) COMMENT '难度等级：简单/中等/困难',
    suitable_season VARCHAR(200) COMMENT '适合季节',
    tags JSON COMMENT '产品标签：["honeymoon","family","luxury"]',
    
    -- ========== 行程信息 ==========
    duration_days INT COMMENT '行程天数',
    departure_city VARCHAR(100) COMMENT '出发城市',
    destination_city VARCHAR(100) COMMENT '目的地城市',
    
    -- ========== 人数限制 ==========
    min_pax INT COMMENT '最少成团人数',
    max_pax INT COMMENT '最大成团人数',
    
    -- ========== 价格体系 ==========
    base_price DECIMAL(10,2) COMMENT '基础价格',
    single_room_supplement DECIMAL(10,2) COMMENT '单房差',
    child_price DECIMAL(10,2) COMMENT '儿童价格',
    infant_price DECIMAL(10,2) COMMENT '婴儿价格',
    currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币单位',
    
    -- ========== 详细描述 ==========
    product_description TEXT COMMENT '产品描述',
    highlights TEXT COMMENT '产品亮点',
    included_services TEXT COMMENT '包含服务',
    excluded_services TEXT COMMENT '不包含服务',
    important_notes TEXT COMMENT '重要提示',
    
    -- ========== 联系信息 ==========
    contact_person VARCHAR(100) COMMENT '联系人',
    contact_phone VARCHAR(50) COMMENT '联系电话',
    contact_email VARCHAR(100) COMMENT '联系邮箱',
    
    -- ========== 版本管理（新增） ==========
    version INT DEFAULT 1 COMMENT '版本号',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    parent_product_id INT COMMENT '父产品ID（版本追溯）',
    
    -- ========== 状态管理 ==========
    product_status ENUM('active','inactive','draft','archived') DEFAULT 'active',
    
    -- ========== 使用统计（新增） ==========
    used_count INT DEFAULT 0 COMMENT '被使用次数',
    last_used_at DATETIME COMMENT '最后使用时间',
    
    -- ========== 时间戳 ==========
    created_at DATE COMMENT '创建日期',
    valid_until DATE COMMENT '有效期至',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- ========== 索引 ==========
    INDEX idx_city (city_name),
    INDEX idx_product_type (product_type),
    INDEX idx_status (product_status),
    INDEX idx_version (version, is_active),
    FOREIGN KEY (parent_product_id) REFERENCES travelproducts(id)
);
```

**字段说明**:
- ✅ **保留原有**: 所有现有核心字段
- ➕ **新增字段**: `tags`, `version`, `is_active`, `parent_product_id`, `used_count`, `last_used_at`
- 🎯 **用途**: 作为产品模板库，供项目和展示引用

---

### 2. `tour_products` - 展示模板（简化版）

**用途**: 用于生成PDF和客户展示的简化产品信息

```sql
CREATE TABLE tour_products (
    -- ========== 基础信息 ==========
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL COMMENT '产品标题',
    
    -- ========== 地理信息（新增） ==========
    country VARCHAR(100) COMMENT '国家',
    city VARCHAR(100) COMMENT '城市',
    
    -- ========== 行程内容 ==========
    itinerary TEXT NOT NULL COMMENT '行程安排',
    included TEXT NOT NULL COMMENT '包含项目',
    not_included TEXT NOT NULL COMMENT '不包含项目',
    
    -- ========== 价格与时长 ==========
    price DECIMAL(10,2) NOT NULL COMMENT '价格',
    duration VARCHAR(50) COMMENT '行程时长（如：3天2晚）',
    
    -- ========== 关联关系（新增） ==========
    source_product_id INT COMMENT '来源产品模板ID',
    
    -- ========== 模板类型（新增） ==========
    template_type ENUM('standard','promotion','customized','internal') 
        DEFAULT 'standard' COMMENT '模板类型',
    
    -- ========== PDF管理（新增） ==========
    pdf_url VARCHAR(500) COMMENT 'PDF文件路径',
    pdf_generated_at DATETIME COMMENT 'PDF生成时间',
    pdf_version INT DEFAULT 1 COMMENT 'PDF版本号',
    
    -- ========== 使用统计（新增） ==========
    view_count INT DEFAULT 0 COMMENT '查看次数',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    last_viewed_at DATETIME COMMENT '最后查看时间',
    
    -- ========== 状态（新增） ==========
    status ENUM('active','inactive','draft','archived') DEFAULT 'active',
    is_featured BOOLEAN DEFAULT FALSE COMMENT '是否推荐',
    
    -- ========== 时间戳 ==========
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- ========== 索引 ==========
    INDEX idx_country_city (country, city),
    INDEX idx_template_type (template_type),
    INDEX idx_status (status),
    INDEX idx_is_featured (is_featured),
    FOREIGN KEY (source_product_id) REFERENCES travelproducts(id)
);
```

**字段说明**:
- ✅ **保留原有**: `title`, `itinerary`, `included`, `not_included`, `price`, `duration`
- ➕ **新增字段**: `country`, `city`, `source_product_id`, `template_type`, `pdf_*`, 统计字段, `status`
- 🎯 **用途**: PDF导出、客户展示、快速浏览

---

### 3. `tour_project` - 项目管理（增强版）

**用途**: 管理实际的旅游订单项目

```sql
CREATE TABLE tour_project (
    -- ========== 基础信息 ==========
    id INT PRIMARY KEY AUTO_INCREMENT,
    project_name VARCHAR(100) NOT NULL COMMENT '项目名称',
    project_hid VARCHAR(255) COMMENT '项目HID',
    project_type VARCHAR(50) COMMENT '项目类型',
    
    -- ========== 产品关联（新增） ==========
    base_product_id INT COMMENT '基础产品模板ID',
    
    -- ========== 状态管理（优化） ==========
    project_status VARCHAR(50) COMMENT '项目状态（旧字段）',
    status_enum ENUM('draft','confirmed','in_progress','completed','cancelled') 
        DEFAULT 'draft' COMMENT '项目状态（新枚举）',
    
    -- ========== 财务管理（新增） ==========
    budget DECIMAL(10,2) COMMENT '项目预算（旧字段）',
    total_budget DECIMAL(10,2) COMMENT '总预算（新字段）',
    actual_cost DECIMAL(10,2) COMMENT '实际成本',
    total_revenue DECIMAL(10,2) COMMENT '总收入',
    profit_margin DECIMAL(5,2) COMMENT '利润率(%)',
    currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币单位',
    
    -- ========== 时间管理（优化） ==========
    departure_date DATE COMMENT '出发日期',
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',
    confirmed_at DATETIME COMMENT '确认时间',
    completed_at DATETIME COMMENT '完成时间',
    
    -- ========== 负责人（新增） ==========
    contact_person VARCHAR(100) NOT NULL COMMENT '联系人',
    contact_info VARCHAR(100) NOT NULL COMMENT '联系方式',
    assigned_to VARCHAR(100) COMMENT '分配给（负责人）',
    
    -- ========== 文件管理 ==========
    folder_name VARCHAR(100) NOT NULL COMMENT '项目文件夹名',
    
    -- ========== 备注 ==========
    remarks TEXT COMMENT '备注',
    
    -- ========== 时间戳 ==========
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- ========== 索引 ==========
    INDEX idx_base_product (base_product_id),
    INDEX idx_status (status_enum),
    INDEX idx_dates (start_date, end_date),
    INDEX idx_assigned (assigned_to),
    FOREIGN KEY (base_product_id) REFERENCES travelproducts(id)
);
```

**字段说明**:
- ✅ **保留原有**: 所有现有字段
- ➕ **新增字段**: `base_product_id`, `status_enum`, 财务字段, 时间管理字段, `assigned_to`
- 🎯 **用途**: 订单管理、项目跟踪、财务分析

---

### 4. `tour_group` - 团队管理（增强版）

**用途**: 管理项目下的具体团队出行信息

```sql
CREATE TABLE tour_group (
    -- ========== 基础信息 ==========
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL COMMENT '行程名称',
    
    -- ========== 项目关联 ==========
    project_id INT NOT NULL COMMENT '所属项目ID',
    project_type VARCHAR(50) COMMENT '项目类型',
    
    -- ========== 时间信息 ==========
    departure_date DATE NOT NULL COMMENT '计划出发日期',
    return_date DATE NOT NULL COMMENT '计划返回日期',
    actual_departure_date DATE COMMENT '实际出发日期（新增）',
    actual_return_date DATE COMMENT '实际返回日期（新增）',
    
    -- ========== 人数信息 ==========
    pax INT NOT NULL COMMENT '人数',
    
    -- ========== 状态管理（新增） ==========
    group_status VARCHAR(50) COMMENT '团队状态（旧字段）',
    status_enum ENUM('planning','ready','departed','in_tour','returned','cancelled') 
        DEFAULT 'planning' COMMENT '团队状态（新枚举）',
    
    -- ========== 团编号（优化） ==========
    group_code VARCHAR(100) COMMENT '团编号（手动）',
    auto_code VARCHAR(50) COMMENT '自动生成团号（如 SG2025-001）',
    
    -- ========== 合作方信息 ==========
    agency VARCHAR(200) COMMENT '旅行社',
    operator VARCHAR(200) COMMENT '地接社',
    
    -- ========== 行程详情 ==========
    hotel_info VARCHAR(500) COMMENT '酒店说明',
    transport TEXT COMMENT '交通工具',
    meals TEXT COMMENT '用餐安排',
    attractions TEXT COMMENT '景点/活动',
    included_items TEXT COMMENT '包含项目',
    excluded_items TEXT COMMENT '不包含项目',
    important_notes TEXT COMMENT '注意事项',
    
    -- ========== 成本收益分析（新增） ==========
    group_cost DECIMAL(10,2) COMMENT '团队成本',
    group_revenue DECIMAL(10,2) COMMENT '团队收入',
    group_profit DECIMAL(10,2) COMMENT '团队利润（自动计算）',
    cost_per_pax DECIMAL(10,2) COMMENT '人均成本（自动计算）',
    revenue_per_pax DECIMAL(10,2) COMMENT '人均收入（自动计算）',
    
    -- ========== 其他信息 ==========
    created_by VARCHAR(100) COMMENT '创建人',
    
    -- ========== 时间戳 ==========
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- ========== 索引 ==========
    INDEX idx_project (project_id),
    INDEX idx_status (status_enum),
    INDEX idx_dates (departure_date, return_date),
    INDEX idx_auto_code (auto_code),
    FOREIGN KEY (project_id) REFERENCES tour_project(id)
);
```

**字段说明**:
- ✅ **保留原有**: 所有现有字段
- ➕ **新增字段**: `status_enum`, `auto_code`, 实际日期, 成本收益分析字段
- 🎯 **用途**: 团队管理、行程跟踪、收益分析

---

## 🔄 三、表关系图（最终版）

```
┌─────────────────────┐
│  travelproducts     │ ← 产品模板库（最全面）
│  (Product)          │
└──────┬──────────────┘
       │
       ├──► (1:N) tour_products      ← 展示模板（PDF导出）
       │            source_product_id
       │
       └──► (1:N) tour_project       ← 项目管理（实际订单）
                    base_product_id
                         │
                         └──► (1:N) tour_group  ← 团队管理（出团信息）
                                     project_id
```

**关系说明**:
1. `travelproducts` → `tour_products`: 一个产品模板可以生成多个展示模板
2. `travelproducts` → `tour_project`: 一个产品模板可以被多个项目引用
3. `tour_project` → `tour_group`: 一个项目可以有多个团队

---

## 📋 四、字段变更总结

### travelproducts（产品模板库）
| 变更类型 | 字段名 | 说明 |
|---------|--------|------|
| ➕ 新增 | `tags` | JSON格式标签 |
| ➕ 新增 | `version` | 版本号 |
| ➕ 新增 | `is_active` | 是否激活 |
| ➕ 新增 | `parent_product_id` | 父产品ID |
| ➕ 新增 | `used_count` | 使用次数统计 |
| ➕ 新增 | `last_used_at` | 最后使用时间 |
| ✅ 保留 | 所有现有字段 | 无删除 |

### tour_products（展示模板）
| 变更类型 | 字段名 | 说明 |
|---------|--------|------|
| ➕ 新增 | `country` | 国家 |
| ➕ 新增 | `city` | 城市 |
| ➕ 新增 | `source_product_id` | 来源产品ID |
| ➕ 新增 | `template_type` | 模板类型 |
| ➕ 新增 | `pdf_url` | PDF路径 |
| ➕ 新增 | `pdf_generated_at` | PDF生成时间 |
| ➕ 新增 | `pdf_version` | PDF版本 |
| ➕ 新增 | `view_count` | 查看次数 |
| ➕ 新增 | `download_count` | 下载次数 |
| ➕ 新增 | `status` | 状态 |
| ➕ 新增 | `is_featured` | 是否推荐 |
| ✅ 保留 | 所有现有字段 | 无删除 |

### tour_project（项目管理）
| 变更类型 | 字段名 | 说明 |
|---------|--------|------|
| ➕ 新增 | `base_product_id` | 基础产品ID |
| ➕ 新增 | `status_enum` | 状态枚举（新） |
| ➕ 新增 | `total_budget` | 总预算 |
| ➕ 新增 | `actual_cost` | 实际成本 |
| ➕ 新增 | `total_revenue` | 总收入 |
| ➕ 新增 | `profit_margin` | 利润率 |
| ➕ 新增 | `currency` | 货币单位 |
| ➕ 新增 | `start_date` | 开始日期 |
| ➕ 新增 | `end_date` | 结束日期 |
| ➕ 新增 | `confirmed_at` | 确认时间 |
| ➕ 新增 | `completed_at` | 完成时间 |
| ➕ 新增 | `assigned_to` | 负责人 |
| ⚠️ 保留 | `project_status` | 旧字段（过渡期） |
| ✅ 保留 | 所有其他现有字段 | 无删除 |

### tour_group（团队管理）
| 变更类型 | 字段名 | 说明 |
|---------|--------|------|
| ➕ 新增 | `status_enum` | 状态枚举（新） |
| ➕ 新增 | `auto_code` | 自动团号 |
| ➕ 新增 | `actual_departure_date` | 实际出发日期 |
| ➕ 新增 | `actual_return_date` | 实际返回日期 |
| ➕ 新增 | `group_cost` | 团队成本 |
| ➕ 新增 | `group_revenue` | 团队收入 |
| ➕ 新增 | `group_profit` | 团队利润 |
| ➕ 新增 | `cost_per_pax` | 人均成本 |
| ➕ 新增 | `revenue_per_pax` | 人均收入 |
| ⚠️ 保留 | `group_status` | 旧字段（过渡期） |
| ✅ 保留 | 所有其他现有字段 | 无删除 |

---

## 🎯 五、核心优化点

### 1. 删除冗余
- ❌ 删除 `tour_product_data`（未使用且重复）

### 2. 增强关联
- ✅ `tour_products.source_product_id` → `travelproducts.id`
- ✅ `tour_project.base_product_id` → `travelproducts.id`

### 3. 财务管理
- ✅ `tour_project`: 预算、成本、收入、利润率
- ✅ `tour_group`: 团队成本、收入、利润（自动计算）

### 4. 状态标准化
- ✅ 统一使用枚举类型
- ✅ 保留旧字段用于过渡

### 5. 版本追溯
- ✅ `travelproducts`: 版本管理系统
- ✅ `tour_products`: PDF版本控制

### 6. 使用统计
- ✅ 查看次数、下载次数、使用次数

---

## 📝 六、实施建议

### 阶段1：清理（1周）
1. ✅ 备份数据库
2. ✅ 删除 `tour_product_data` 表
3. ✅ 删除相关Python模型

### 阶段2：增强（2-3周）
1. ✅ 执行 `phase1_all_enhancements.sql`
2. ✅ 更新Python模型
3. ✅ 测试所有功能

### 阶段3：优化（持续）
1. ✅ 添加触发器（自动计算利润）
2. ✅ 创建视图（财务汇总）
3. ✅ 实现新功能（标签、版本等）

---

## ✅ 总结

### 保留表（4个）
1. **travelproducts** - 产品模板库（最核心）
2. **tour_products** - 展示模板（PDF专用）
3. **tour_project** - 项目管理（订单）
4. **tour_group** - 团队管理（出团）

### 删除表（1个）
1. **tour_product_data** - 未使用且重复

### 新增字段总计
- `travelproducts`: +6 个字段
- `tour_products`: +11 个字段
- `tour_project`: +12 个字段
- `tour_group`: +9 个字段

### 优化效果
✅ 职责清晰  
✅ 关联完整  
✅ 财务可控  
✅ 状态规范  
✅ 易于扩展

