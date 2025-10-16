-- ========================================
-- 旅游产品管理系统优化 - MySQL 迁移脚本
-- 日期: 2025-10-16
-- 目的: 添加供应商关联、图片、标签等字段到 travelproducts 表
-- ========================================

USE travel_panel_new;

-- ========================================
-- 1. 为 travelproducts 表添加新字段
-- ========================================

-- 供应商关联
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS supplier_id INT NULL COMMENT '供应商ID' AFTER id;

-- 产品编号
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS product_code VARCHAR(50) NULL UNIQUE COMMENT '产品编号' AFTER supplier_id;

-- 国家字段
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS country VARCHAR(100) NULL COMMENT '国家' AFTER product_code;

-- 住宿晚数
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS duration_nights INT NULL COMMENT '住宿晚数' AFTER duration_days;

-- 标签（JSON格式）
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS tags TEXT NULL COMMENT '标签（JSON格式）：蜜月/亲子/豪华/经济' AFTER difficulty_level;

-- 图片字段
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS cover_image VARCHAR(500) NULL COMMENT '封面图' AFTER important_notes;

ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS gallery_images TEXT NULL COMMENT '图片库（JSON数组）' AFTER cover_image;

-- 状态管理
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE COMMENT '是否精选' AFTER product_status;

ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS valid_from DATE NULL COMMENT '有效开始日期' AFTER is_featured;

-- 版本管理
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS version INT DEFAULT 1 COMMENT '版本号' AFTER valid_until;

ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS parent_product_id INT NULL COMMENT '父产品ID（版本追踪）' AFTER version;

-- 创建人
ALTER TABLE travelproducts 
ADD COLUMN IF NOT EXISTS created_by VARCHAR(100) NULL COMMENT '创建人' AFTER parent_product_id;

-- ========================================
-- 2. 为 tour_project 表添加新字段
-- ========================================

-- 关联基础产品
ALTER TABLE tour_project 
ADD COLUMN IF NOT EXISTS base_product_id INT NULL COMMENT '基于哪个产品模板' AFTER project_hid;

-- 货币单位
ALTER TABLE tour_project 
ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币单位' AFTER budget;

-- 创建人
ALTER TABLE tour_project 
ADD COLUMN IF NOT EXISTS created_by VARCHAR(100) NULL COMMENT '创建人' AFTER updated_at;

-- ========================================
-- 3. 添加外键约束
-- ========================================

-- travelproducts 关联到 suppliers
ALTER TABLE travelproducts 
ADD CONSTRAINT fk_travelproducts_supplier 
FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- travelproducts 父产品关联
ALTER TABLE travelproducts 
ADD CONSTRAINT fk_travelproducts_parent 
FOREIGN KEY (parent_product_id) REFERENCES travelproducts(id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- tour_project 关联到 travelproducts
ALTER TABLE tour_project 
ADD CONSTRAINT fk_tour_project_base_product 
FOREIGN KEY (base_product_id) REFERENCES travelproducts(id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- ========================================
-- 4. 创建索引优化查询性能
-- ========================================

-- 供应商索引
CREATE INDEX IF NOT EXISTS idx_travelproducts_supplier ON travelproducts(supplier_id);

-- 国家城市索引
CREATE INDEX IF NOT EXISTS idx_travelproducts_country_city ON travelproducts(country, city_name);

-- 产品状态索引
CREATE INDEX IF NOT EXISTS idx_travelproducts_status ON travelproducts(product_status);

-- 产品编号索引
CREATE INDEX IF NOT EXISTS idx_travelproducts_code ON travelproducts(product_code);

-- tour_project 基础产品索引
CREATE INDEX IF NOT EXISTS idx_tour_project_base_product ON tour_project(base_product_id);

-- ========================================
-- 5. 数据迁移和清理（可选）
-- ========================================

-- 将 city_name 复制到 country（如果为空）
-- UPDATE travelproducts 
-- SET country = (
--     SELECT country_name 
--     FROM travel_products_city 
--     WHERE travel_products_city.city_name = travelproducts.city_name 
--     LIMIT 1
-- )
-- WHERE country IS NULL AND city_name IS NOT NULL;

-- ========================================
-- 验证迁移结果
-- ========================================

-- 检查新字段
DESCRIBE travelproducts;

-- 检查外键约束
SELECT 
    CONSTRAINT_NAME, 
    TABLE_NAME, 
    COLUMN_NAME, 
    REFERENCED_TABLE_NAME, 
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'travel_panel_new' 
    AND TABLE_NAME IN ('travelproducts', 'tour_project')
    AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 检查索引
SHOW INDEX FROM travelproducts;

-- 完成提示
SELECT 'Tour Product Enhancement Migration Completed!' AS Status;

