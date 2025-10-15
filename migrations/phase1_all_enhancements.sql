-- ========================================
-- Phase 1: 旅游配套数据库全面增强
-- 执行时间: 预计 2-3 周完成
-- 优先级: P1 (高)
-- ========================================

-- 使用数据库
USE mytraveldb;

-- ========================================
-- 1. tour_project 表增强
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
ADD COLUMN status_enum ENUM(
    'draft', 'confirmed', 'in_progress', 
    'completed', 'cancelled'
) DEFAULT 'draft' COMMENT '项目状态（新枚举）',

-- 时间管理
ADD COLUMN start_date DATE NULL COMMENT '开始日期',
ADD COLUMN end_date DATE NULL COMMENT '结束日期',
ADD COLUMN confirmed_at DATETIME NULL COMMENT '确认时间',
ADD COLUMN completed_at DATETIME NULL COMMENT '完成时间',

-- 负责人
ADD COLUMN assigned_to VARCHAR(100) NULL COMMENT '分配给（员工ID或姓名）',

-- 索引
ADD INDEX idx_base_product (base_product_id),
ADD INDEX idx_status_enum (status_enum),
ADD INDEX idx_dates (start_date, end_date),
ADD INDEX idx_assigned (assigned_to);

-- 数据迁移：将旧的 project_status 映射到新字段
UPDATE tour_project 
SET status_enum = CASE 
    WHEN project_status LIKE '%草稿%' THEN 'draft'
    WHEN project_status LIKE '%确认%' THEN 'confirmed'
    WHEN project_status LIKE '%进行%' THEN 'in_progress'
    WHEN project_status LIKE '%完成%' THEN 'completed'
    WHEN project_status LIKE '%取消%' THEN 'cancelled'
    ELSE 'draft'
END
WHERE status_enum IS NULL;

SELECT '✅ tour_project 表增强完成' AS status;


-- ========================================
-- 2. tour_group 表增强
-- ========================================
ALTER TABLE tour_group

-- 状态管理
ADD COLUMN status_enum ENUM(
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

-- 实际日期
ADD COLUMN actual_departure_date DATE NULL COMMENT '实际出发日期',
ADD COLUMN actual_return_date DATE NULL COMMENT '实际返回日期',

-- 索引
ADD INDEX idx_status_enum (status_enum),
ADD INDEX idx_dates (departure_date, return_date),
ADD INDEX idx_auto_code (auto_code);

-- 数据迁移：如果有旧状态字段
UPDATE tour_group 
SET status_enum = CASE 
    WHEN group_status LIKE '%计划%' THEN 'planning'
    WHEN group_status LIKE '%准备%' THEN 'ready'
    WHEN group_status LIKE '%出发%' THEN 'departed'
    WHEN group_status LIKE '%行程%' THEN 'in_tour'
    WHEN group_status LIKE '%返回%' THEN 'returned'
    WHEN group_status LIKE '%取消%' THEN 'cancelled'
    ELSE 'planning'
END
WHERE status_enum IS NULL AND group_status IS NOT NULL;

SELECT '✅ tour_group 表增强完成' AS status;


-- ========================================
-- 3. tour_products 表增强
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
ADD INDEX idx_status (status),
ADD INDEX idx_is_featured (is_featured);

SELECT '✅ tour_products 表增强完成' AS status;


-- ========================================
-- 4. travelproducts 表增强
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

-- 添加默认标签
UPDATE travelproducts 
SET tags = JSON_ARRAY('standard') 
WHERE tags IS NULL;

SELECT '✅ travelproducts 表增强完成' AS status;


-- ========================================
-- 5. 触发器：自动计算团队利润
-- ========================================
DELIMITER //

DROP TRIGGER IF EXISTS calculate_group_profit_insert //
CREATE TRIGGER calculate_group_profit_insert
BEFORE INSERT ON tour_group
FOR EACH ROW
BEGIN
    IF NEW.group_cost IS NOT NULL AND NEW.group_revenue IS NOT NULL THEN
        SET NEW.group_profit = NEW.group_revenue - NEW.group_cost;
    END IF;
    
    IF NEW.group_cost IS NOT NULL AND NEW.pax > 0 THEN
        SET NEW.cost_per_pax = NEW.group_cost / NEW.pax;
    END IF;
    
    IF NEW.group_revenue IS NOT NULL AND NEW.pax > 0 THEN
        SET NEW.revenue_per_pax = NEW.group_revenue / NEW.pax;
    END IF;
END //

DROP TRIGGER IF EXISTS calculate_group_profit_update //
CREATE TRIGGER calculate_group_profit_update
BEFORE UPDATE ON tour_group
FOR EACH ROW
BEGIN
    IF NEW.group_cost IS NOT NULL AND NEW.group_revenue IS NOT NULL THEN
        SET NEW.group_profit = NEW.group_revenue - NEW.group_cost;
    END IF;
    
    IF NEW.group_cost IS NOT NULL AND NEW.pax > 0 THEN
        SET NEW.cost_per_pax = NEW.group_cost / NEW.pax;
    END IF;
    
    IF NEW.group_revenue IS NOT NULL AND NEW.pax > 0 THEN
        SET NEW.revenue_per_pax = NEW.group_revenue / NEW.pax;
    END IF;
END //

DELIMITER ;

SELECT '✅ 触发器创建完成' AS status;


-- ========================================
-- 6. 视图：项目财务汇总
-- ========================================
CREATE OR REPLACE VIEW v_project_financial_summary AS
SELECT 
    p.id AS project_id,
    p.project_name,
    p.status_enum,
    p.total_budget,
    p.actual_cost,
    p.total_revenue,
    p.profit_margin,
    COUNT(g.id) AS total_groups,
    SUM(g.pax) AS total_pax,
    SUM(g.group_cost) AS total_group_cost,
    SUM(g.group_revenue) AS total_group_revenue,
    SUM(g.group_profit) AS total_group_profit,
    p.created_at,
    p.updated_at
FROM tour_project p
LEFT JOIN tour_group g ON p.id = g.project_id
GROUP BY p.id;

SELECT '✅ 财务汇总视图创建完成' AS status;


-- ========================================
-- 7. 视图：产品使用统计
-- ========================================
CREATE OR REPLACE VIEW v_product_usage_stats AS
SELECT 
    p.id AS product_id,
    p.product_name,
    p.city_name,
    p.product_status,
    p.used_count,
    COUNT(DISTINCT pr.id) AS project_count,
    COUNT(DISTINCT tp.id) AS template_count,
    MAX(pr.created_at) AS last_used_in_project,
    p.created_at,
    p.updated_at
FROM travelproducts p
LEFT JOIN tour_project pr ON p.id = pr.base_product_id
LEFT JOIN tour_products tp ON p.id = tp.source_product_id
GROUP BY p.id;

SELECT '✅ 产品使用统计视图创建完成' AS status;


-- ========================================
-- 8. 数据验证
-- ========================================
SELECT '========================================' AS ' ';
SELECT '数据验证结果' AS ' ';
SELECT '========================================' AS ' ';

-- 检查 tour_project 增强
SELECT 
    COUNT(*) AS total_projects,
    SUM(CASE WHEN status_enum IS NOT NULL THEN 1 ELSE 0 END) AS has_status,
    SUM(CASE WHEN total_budget IS NOT NULL THEN 1 ELSE 0 END) AS has_budget
FROM tour_project;

-- 检查 tour_group 增强
SELECT 
    COUNT(*) AS total_groups,
    SUM(CASE WHEN status_enum IS NOT NULL THEN 1 ELSE 0 END) AS has_status,
    SUM(CASE WHEN group_cost IS NOT NULL THEN 1 ELSE 0 END) AS has_cost
FROM tour_group;

-- 检查 tour_products 增强
SELECT 
    COUNT(*) AS total_tour_products,
    SUM(CASE WHEN status IS NOT NULL THEN 1 ELSE 0 END) AS has_status,
    SUM(CASE WHEN template_type IS NOT NULL THEN 1 ELSE 0 END) AS has_type
FROM tour_products;

-- 检查 travelproducts 增强
SELECT 
    COUNT(*) AS total_travel_products,
    SUM(CASE WHEN tags IS NOT NULL THEN 1 ELSE 0 END) AS has_tags,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_products
FROM travelproducts;

SELECT '========================================' AS ' ';
SELECT '✅ Phase 1 所有增强完成！' AS status;
SELECT '========================================' AS ' ';

