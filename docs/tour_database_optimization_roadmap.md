# 旅游配套数据库优化路线图

## 📋 优化建议评估与实施方案

### ⭐ 优先级分级

#### 🔴 **P0 - 立即实施**（基础优化，1-2周）
1. ✅ 删除 `tour_product_data` 表
2. ✅ 统一表命名风格
3. ✅ 基础状态枚举优化

#### 🟡 **P1 - 短期实施**（核心功能扩展，2-4周）
1. `tour_project` 财务管理字段
2. `tour_project` 与 `travelproducts` 关联
3. `tour_products` 与 `travelproducts` 关联
4. `tour_group` 成本分析字段
5. 项目/团队状态标准化

#### 🟢 **P2 - 中期规划**（高级功能，1-2个月）
1. 版本管理系统
2. PDF文件管理
3. 辅助表：`product_price_tiers`, `project_documents`
4. 审计日志系统

#### 🔵 **P3 - 长期规划**（国际化/智能化，3-6个月）
1. 多语言支持系统
2. 标签/智能推荐
3. 动态行程结构
4. 供应商管理系统

---

## 🎯 Phase 1: 基础优化（P0）

### 1.1 清理冗余表

```sql
-- ✅ 已创建脚本
-- migrations/cleanup_tour_product_data_table.sql
DROP TABLE IF EXISTS tour_product_data;
```

**Python模型清理**:
```bash
python scripts/cleanup_tour_product_data_model.py
```

### 1.2 状态枚举标准化

**创建枚举定义文件**: `App_new/business/tour/enums.py`

```python
from enum import Enum

class ProjectStatus(str, Enum):
    """项目状态"""
    DRAFT = 'draft'              # 草稿
    CONFIRMED = 'confirmed'      # 已确认
    IN_PROGRESS = 'in_progress'  # 进行中
    COMPLETED = 'completed'      # 已完成
    CANCELLED = 'cancelled'      # 已取消
    
    @property
    def display(self):
        return {
            'draft': '草稿',
            'confirmed': '已确认',
            'in_progress': '进行中',
            'completed': '已完成',
            'cancelled': '已取消'
        }[self.value]
    
    @property
    def color(self):
        return {
            'draft': 'secondary',
            'confirmed': 'primary',
            'in_progress': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        }[self.value]

class GroupStatus(str, Enum):
    """团队状态"""
    PLANNING = 'planning'        # 计划中
    READY = 'ready'             # 准备就绪
    DEPARTED = 'departed'       # 已出发
    IN_TOUR = 'in_tour'         # 行程中
    RETURNED = 'returned'       # 已返回
    CANCELLED = 'cancelled'     # 已取消
    
    @property
    def display(self):
        return {
            'planning': '计划中',
            'ready': '准备就绪',
            'departed': '已出发',
            'in_tour': '行程中',
            'returned': '已返回',
            'cancelled': '已取消'
        }[self.value]

class ProductStatus(str, Enum):
    """产品状态"""
    ACTIVE = 'active'           # 激活
    INACTIVE = 'inactive'       # 停用
    DRAFT = 'draft'             # 草稿
    ARCHIVED = 'archived'       # 归档
    
    @property
    def display(self):
        return {
            'active': '激活',
            'inactive': '停用',
            'draft': '草稿',
            'archived': '归档'
        }[self.value]

class TemplateType(str, Enum):
    """展示模板类型"""
    STANDARD = 'standard'         # 标准模板
    PROMOTION = 'promotion'       # 促销模板
    CUSTOMIZED = 'customized'     # 定制模板
    INTERNAL = 'internal'         # 内部使用
    
    @property
    def display(self):
        return {
            'standard': '标准模板',
            'promotion': '促销模板',
            'customized': '定制模板',
            'internal': '内部使用'
        }[self.value]
```

---

## 🚀 Phase 2: 核心功能扩展（P1）

### 2.1 tour_project 增强

**迁移脚本**: `migrations/phase1_enhance_tour_project.sql`

```sql
-- ========================================
-- Phase 1: tour_project 表增强
-- ========================================

ALTER TABLE tour_project

-- 产品关联
ADD COLUMN base_product_id INT NULL COMMENT '基础产品模板ID',
ADD CONSTRAINT fk_project_base_product 
    FOREIGN KEY (base_product_id) REFERENCES travelproducts(id) 
    ON DELETE SET NULL,

-- 财务管理
ADD COLUMN total_budget DECIMAL(10,2) NULL COMMENT '总预算',
ADD COLUMN actual_cost DECIMAL(10,2) NULL COMMENT '实际成本',
ADD COLUMN total_revenue DECIMAL(10,2) NULL COMMENT '总收入',
ADD COLUMN profit_margin DECIMAL(5,2) NULL COMMENT '利润率(%)',
ADD COLUMN currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币单位',

-- 状态管理（替换原有 project_status）
ADD COLUMN status_new ENUM(
    'draft', 'confirmed', 'in_progress', 
    'completed', 'cancelled'
) DEFAULT 'draft' COMMENT '项目状态（新）',

-- 时间管理
ADD COLUMN start_date DATE NULL COMMENT '开始日期',
ADD COLUMN end_date DATE NULL COMMENT '结束日期',
ADD COLUMN confirmed_at DATETIME NULL COMMENT '确认时间',
ADD COLUMN completed_at DATETIME NULL COMMENT '完成时间',

-- 负责人
ADD COLUMN assigned_to VARCHAR(100) NULL COMMENT '分配给（员工ID或姓名）',

-- 索引
ADD INDEX idx_base_product (base_product_id),
ADD INDEX idx_status (status_new),
ADD INDEX idx_dates (start_date, end_date);

-- 数据迁移：将旧的 project_status 映射到新字段
UPDATE tour_project 
SET status_new = CASE 
    WHEN project_status LIKE '%草稿%' THEN 'draft'
    WHEN project_status LIKE '%确认%' THEN 'confirmed'
    WHEN project_status LIKE '%进行%' THEN 'in_progress'
    WHEN project_status LIKE '%完成%' THEN 'completed'
    WHEN project_status LIKE '%取消%' THEN 'cancelled'
    ELSE 'draft'
END;

-- 可选：删除旧字段（谨慎操作）
-- ALTER TABLE tour_project DROP COLUMN project_status;
```

### 2.2 tour_group 增强

**迁移脚本**: `migrations/phase1_enhance_tour_group.sql`

```sql
-- ========================================
-- Phase 1: tour_group 表增强
-- ========================================

ALTER TABLE tour_group

-- 状态管理
ADD COLUMN status ENUM(
    'planning', 'ready', 'departed', 
    'in_tour', 'returned', 'cancelled'
) DEFAULT 'planning' COMMENT '团队状态',

-- 成本收益分析
ADD COLUMN group_cost DECIMAL(10,2) NULL COMMENT '团队成本',
ADD COLUMN group_revenue DECIMAL(10,2) NULL COMMENT '团队收入',
ADD COLUMN group_profit DECIMAL(10,2) NULL COMMENT '团队利润',
ADD COLUMN cost_per_pax DECIMAL(10,2) NULL COMMENT '人均成本',
ADD COLUMN revenue_per_pax DECIMAL(10,2) NULL COMMENT '人均收入',

-- 团编号自动化（后续可通过触发器或应用层生成）
ADD COLUMN auto_code VARCHAR(50) NULL COMMENT '自动生成团号（如 SG2025-001）',
ADD UNIQUE INDEX idx_auto_code (auto_code),

-- 实际日期
ADD COLUMN actual_departure_date DATE NULL COMMENT '实际出发日期',
ADD COLUMN actual_return_date DATE NULL COMMENT '实际返回日期',

-- 索引
ADD INDEX idx_status (status),
ADD INDEX idx_dates (departure_date, return_date);

-- 自动计算利润（可选触发器）
-- CREATE TRIGGER calculate_group_profit 
-- BEFORE UPDATE ON tour_group
-- FOR EACH ROW
-- BEGIN
--     IF NEW.group_cost IS NOT NULL AND NEW.group_revenue IS NOT NULL THEN
--         SET NEW.group_profit = NEW.group_revenue - NEW.group_cost;
--     END IF;
-- END;
```

### 2.3 tour_products 增强

**迁移脚本**: `migrations/phase1_enhance_tour_products.sql`

```sql
-- ========================================
-- Phase 1: tour_products 表增强
-- ========================================

ALTER TABLE tour_products

-- 与产品模板关联
ADD COLUMN source_product_id INT NULL COMMENT '来源产品模板ID',
ADD CONSTRAINT fk_tourproduct_source 
    FOREIGN KEY (source_product_id) REFERENCES travelproducts(id) 
    ON DELETE SET NULL,

-- 模板类型
ADD COLUMN template_type ENUM(
    'standard', 'promotion', 'customized', 'internal'
) DEFAULT 'standard' COMMENT '模板类型',

-- PDF管理
ADD COLUMN pdf_url VARCHAR(500) NULL COMMENT 'PDF文件路径',
ADD COLUMN pdf_generated_at DATETIME NULL COMMENT 'PDF生成时间',
ADD COLUMN pdf_version INT DEFAULT 1 COMMENT 'PDF版本号',

-- 使用统计
ADD COLUMN view_count INT DEFAULT 0 COMMENT '查看次数',
ADD COLUMN download_count INT DEFAULT 0 COMMENT '下载次数',
ADD COLUMN last_viewed_at DATETIME NULL COMMENT '最后查看时间',

-- 状态
ADD COLUMN status ENUM('active', 'inactive', 'draft', 'archived') 
    DEFAULT 'active' COMMENT '状态',
ADD COLUMN is_featured BOOLEAN DEFAULT FALSE COMMENT '是否推荐',

-- 索引
ADD INDEX idx_source_product (source_product_id),
ADD INDEX idx_template_type (template_type),
ADD INDEX idx_status (status);
```

### 2.4 travelproducts 增强

**迁移脚本**: `migrations/phase1_enhance_travelproducts.sql`

```sql
-- ========================================
-- Phase 1: travelproducts 表增强
-- ========================================

ALTER TABLE travelproducts

-- 版本管理
ADD COLUMN version INT DEFAULT 1 COMMENT '版本号',
ADD COLUMN is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
ADD COLUMN parent_product_id INT NULL COMMENT '父产品ID（用于版本追溯）',
ADD CONSTRAINT fk_parent_product 
    FOREIGN KEY (parent_product_id) REFERENCES travelproducts(id) 
    ON DELETE SET NULL,

-- 标签系统（JSON）
ADD COLUMN tags JSON NULL COMMENT '产品标签（如 honeymoon, family, luxury）',

-- 使用统计
ADD COLUMN used_count INT DEFAULT 0 COMMENT '被使用次数（被项目引用）',
ADD COLUMN last_used_at DATETIME NULL COMMENT '最后使用时间',

-- 索引
ADD INDEX idx_version (version, is_active),
ADD INDEX idx_parent_product (parent_product_id),
ADD INDEX idx_product_status (product_status);

-- 添加示例标签
UPDATE travelproducts 
SET tags = JSON_ARRAY('standard') 
WHERE tags IS NULL;
```

---

## 🏗️ Phase 3: 高级功能（P2）

### 3.1 价格层级表

**创建表**: `migrations/phase2_create_product_price_tiers.sql`

```sql
-- ========================================
-- Phase 2: 产品价格层级表
-- ========================================

CREATE TABLE IF NOT EXISTS product_price_tiers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL COMMENT '产品ID',
    
    -- 人数范围
    min_pax INT NOT NULL COMMENT '最少人数',
    max_pax INT NULL COMMENT '最多人数（NULL表示无上限）',
    
    -- 价格
    price_per_pax DECIMAL(10,2) NOT NULL COMMENT '人均价格',
    currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币',
    
    -- 季节/时间
    season VARCHAR(50) NULL COMMENT '季节（peak/low/shoulder）',
    valid_from DATE NULL COMMENT '有效起始日期',
    valid_until DATE NULL COMMENT '有效截止日期',
    
    -- 备注
    notes TEXT NULL COMMENT '备注说明',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外键
    FOREIGN KEY (product_id) REFERENCES travelproducts(id) ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_product (product_id),
    INDEX idx_pax_range (min_pax, max_pax),
    INDEX idx_dates (valid_from, valid_until)
) COMMENT='产品价格层级表';
```

### 3.2 项目文档表

**创建表**: `migrations/phase2_create_project_documents.sql`

```sql
-- ========================================
-- Phase 2: 项目文档表
-- ========================================

CREATE TABLE IF NOT EXISTS project_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL COMMENT '项目ID',
    
    -- 文档信息
    doc_type ENUM(
        'contract', 'invoice', 'confirmation', 
        'itinerary', 'receipt', 'other'
    ) NOT NULL COMMENT '文档类型',
    doc_name VARCHAR(200) NOT NULL COMMENT '文档名称',
    doc_description TEXT NULL COMMENT '文档描述',
    
    -- 文件信息
    file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
    file_size INT NULL COMMENT '文件大小（bytes）',
    file_type VARCHAR(50) NULL COMMENT '文件类型（pdf/docx/xlsx）',
    
    -- 版本控制
    version INT DEFAULT 1 COMMENT '版本号',
    
    -- 状态
    status ENUM('draft', 'final', 'void') DEFAULT 'draft' COMMENT '文档状态',
    
    -- 上传信息
    uploaded_by VARCHAR(100) NULL COMMENT '上传人',
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外键
    FOREIGN KEY (project_id) REFERENCES tour_project(id) ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_project (project_id),
    INDEX idx_doc_type (doc_type),
    INDEX idx_status (status)
) COMMENT='项目文档管理表';
```

### 3.3 审计日志表

**创建表**: `migrations/phase2_create_audit_logs.sql`

```sql
-- ========================================
-- Phase 2: 审计日志表
-- ========================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 实体信息
    entity_type VARCHAR(50) NOT NULL COMMENT '实体类型（tour_project/tour_group等）',
    entity_id INT NOT NULL COMMENT '实体ID',
    
    -- 操作信息
    action VARCHAR(50) NOT NULL COMMENT '操作（create/update/delete/view）',
    action_detail TEXT NULL COMMENT '操作详情（JSON格式）',
    
    -- 变更内容
    old_values JSON NULL COMMENT '旧值',
    new_values JSON NULL COMMENT '新值',
    
    -- 操作人
    user_id INT NULL COMMENT '用户ID',
    username VARCHAR(100) NULL COMMENT '用户名',
    user_ip VARCHAR(50) NULL COMMENT 'IP地址',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    
    -- 索引
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_user (user_id, username),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) COMMENT='系统审计日志表';
```

---

## 🌍 Phase 4: 国际化与智能化（P3）

### 4.1 多语言支持表

**创建表**: `migrations/phase3_create_multilingual_support.sql`

```sql
-- ========================================
-- Phase 3: 多语言支持表
-- ========================================

CREATE TABLE IF NOT EXISTS product_translations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL COMMENT '产品ID',
    language_code VARCHAR(10) NOT NULL COMMENT '语言代码（en/zh/ja）',
    
    -- 翻译内容
    product_name VARCHAR(200) NULL COMMENT '产品名称',
    product_description TEXT NULL COMMENT '产品描述',
    highlights TEXT NULL COMMENT '产品亮点',
    included_services TEXT NULL COMMENT '包含服务',
    excluded_services TEXT NULL COMMENT '不包含服务',
    important_notes TEXT NULL COMMENT '重要提示',
    
    -- 元数据
    translator VARCHAR(100) NULL COMMENT '翻译人员',
    translation_status ENUM('draft', 'review', 'approved') DEFAULT 'draft',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外键和唯一约束
    FOREIGN KEY (product_id) REFERENCES travelproducts(id) ON DELETE CASCADE,
    UNIQUE KEY unique_product_language (product_id, language_code),
    
    -- 索引
    INDEX idx_language (language_code),
    INDEX idx_status (translation_status)
) COMMENT='产品多语言翻译表';
```

### 4.2 动态行程表

**创建表**: `migrations/phase3_create_product_itinerary.sql`

```sql
-- ========================================
-- Phase 3: 动态行程表
-- ========================================

CREATE TABLE IF NOT EXISTS product_itinerary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL COMMENT '产品ID',
    
    -- 日期信息
    day_number INT NOT NULL COMMENT '第几天',
    day_title VARCHAR(200) NULL COMMENT '当天标题',
    
    -- 详细内容
    activities TEXT NULL COMMENT '活动内容',
    meals VARCHAR(100) NULL COMMENT '用餐（早/午/晚）',
    accommodation VARCHAR(200) NULL COMMENT '住宿',
    transportation VARCHAR(200) NULL COMMENT '交通',
    
    -- 附加信息
    tips TEXT NULL COMMENT '温馨提示',
    optional_activities TEXT NULL COMMENT '可选活动',
    
    -- 排序
    display_order INT DEFAULT 0 COMMENT '显示顺序',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外键
    FOREIGN KEY (product_id) REFERENCES travelproducts(id) ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_product_day (product_id, day_number),
    INDEX idx_display_order (display_order)
) COMMENT='产品动态行程表';
```

---

## 📊 实施时间表

| 阶段 | 优先级 | 预计时间 | 主要内容 |
|------|--------|----------|----------|
| **Phase 0** | 🔴 P0 | 1周 | 清理冗余、统一命名 |
| **Phase 1** | 🟡 P1 | 2-3周 | 核心功能增强（财务、状态、关联） |
| **Phase 2** | 🟢 P2 | 4-6周 | 辅助表创建（价格、文档、日志） |
| **Phase 3** | 🔵 P3 | 2-3个月 | 国际化、智能化功能 |

---

## ✅ 实施检查清单

### Phase 0
- [ ] 备份现有数据库
- [ ] 执行 `cleanup_tour_product_data_table.sql`
- [ ] 运行 `cleanup_tour_product_data_model.py`
- [ ] 创建 `enums.py` 文件
- [ ] 测试应用是否正常运行

### Phase 1
- [ ] 执行 `phase1_enhance_tour_project.sql`
- [ ] 执行 `phase1_enhance_tour_group.sql`
- [ ] 执行 `phase1_enhance_tour_products.sql`
- [ ] 执行 `phase1_enhance_travelproducts.sql`
- [ ] 更新 Python 模型
- [ ] 更新路由和视图
- [ ] 测试新功能

### Phase 2
- [ ] 执行 `phase2_create_product_price_tiers.sql`
- [ ] 执行 `phase2_create_project_documents.sql`
- [ ] 执行 `phase2_create_audit_logs.sql`
- [ ] 创建对应的 Python 模型
- [ ] 实现文档上传功能
- [ ] 实现日志记录中间件

### Phase 3
- [ ] 执行 `phase3_create_multilingual_support.sql`
- [ ] 执行 `phase3_create_product_itinerary.sql`
- [ ] 实现多语言切换功能
- [ ] 实现动态行程编辑器
- [ ] 测试国际化功能

---

## 🎓 总结

你的优化建议**非常专业且全面**，完全符合企业级应用的最佳实践：

### 优点
1. ✅ **分层清晰** - 产品模板 → 展示 → 项目 → 团队
2. ✅ **职责明确** - 每个表有明确的用途和边界
3. ✅ **面向未来** - 版本管理、多语言、审计日志
4. ✅ **可扩展性** - JSON字段、辅助表支持灵活扩展
5. ✅ **数据完整性** - 外键约束、状态枚举、索引优化

### 实施建议
- **采用分阶段实施**，避免一次性大规模改动
- **每个阶段都要充分测试**，确保不影响现有功能
- **使用版本控制**（Alembic/Flask-Migrate）管理所有迁移
- **及时更新文档**，记录每次变更的原因和影响

### 下一步
建议从 **Phase 0 开始**，逐步推进！🚀

