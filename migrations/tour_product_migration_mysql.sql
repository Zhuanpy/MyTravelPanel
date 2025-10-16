-- ========================================
-- 旅游产品管理系统优化 - MySQL 迁移脚本
-- 日期: 2025-10-16
-- 数据库: travel_panel_new
-- 执行方式: 在 MySQL Workbench 中直接执行
-- ========================================

USE travel_panel_new;

-- ========================================
-- 第一部分：为 travelproducts 表添加新字段
-- ========================================

-- 1. 供应商关联
ALTER TABLE travelproducts 
ADD COLUMN supplier_id INT NULL COMMENT '供应商ID' AFTER id;

-- 2. 产品编号
ALTER TABLE travelproducts 
ADD COLUMN product_code VARCHAR(50) NULL COMMENT '产品编号' AFTER supplier_id;

-- 3. 国家字段
ALTER TABLE travelproducts 
ADD COLUMN country VARCHAR(100) NULL COMMENT '国家' AFTER product_code;

-- 4. 住宿晚数
ALTER TABLE travelproducts 
ADD COLUMN duration_nights INT NULL COMMENT '住宿晚数' AFTER duration_days;

-- 5. 标签（JSON格式）
ALTER TABLE travelproducts 
ADD COLUMN tags TEXT NULL COMMENT '标签（JSON格式）：蜜月/亲子/豪华/经济' AFTER difficulty_level;

-- 6. 封面图
ALTER TABLE travelproducts 
ADD COLUMN cover_image VARCHAR(500) NULL COMMENT '封面图' AFTER important_notes;

-- 7. 图片库
ALTER TABLE travelproducts 
ADD COLUMN gallery_images TEXT NULL COMMENT '图片库（JSON数组）' AFTER cover_image;

-- 8. 是否精选
ALTER TABLE travelproducts 
ADD COLUMN is_featured TINYINT(1) DEFAULT 0 COMMENT '是否精选' AFTER product_status;

-- 9. 有效开始日期
ALTER TABLE travelproducts 
ADD COLUMN valid_from DATE NULL COMMENT '有效开始日期' AFTER is_featured;

-- 10. 版本号
ALTER TABLE travelproducts 
ADD COLUMN version INT DEFAULT 1 COMMENT '版本号' AFTER valid_until;

-- 11. 父产品ID
ALTER TABLE travelproducts 
ADD COLUMN parent_product_id INT NULL COMMENT '父产品ID（版本追踪）' AFTER version;

-- 12. 创建人
ALTER TABLE travelproducts 
ADD COLUMN created_by VARCHAR(100) NULL COMMENT '创建人' AFTER parent_product_id;

-- ========================================
-- 第二部分：为 tour_project 表添加新字段
-- ========================================

-- 1. 关联基础产品
ALTER TABLE tour_project 
ADD COLUMN base_product_id INT NULL COMMENT '基于哪个产品模板' AFTER project_hid;

-- 2. 货币单位
ALTER TABLE tour_project 
ADD COLUMN currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币单位' AFTER budget;

-- 3. 创建人
ALTER TABLE tour_project 
ADD COLUMN created_by VARCHAR(100) NULL COMMENT '创建人' AFTER updated_at;

-- ========================================
-- 第三部分：添加外键约束
-- ========================================

-- 检查并删除已存在的外键（如果有）
-- SET @exist_fk1 := (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS 
--                    WHERE TABLE_SCHEMA = 'travel_panel_new' 
--                    AND TABLE_NAME = 'travelproducts' 
--                    AND CONSTRAINT_NAME = 'fk_travelproducts_supplier');
-- SET @sqlstmt := IF(@exist_fk1 > 0, 'ALTER TABLE travelproducts DROP FOREIGN KEY fk_travelproducts_supplier', 'SELECT 1');
-- PREPARE stmt FROM @sqlstmt;
-- EXECUTE stmt;

-- 1. travelproducts 关联到 suppliers
ALTER TABLE travelproducts 
ADD CONSTRAINT fk_travelproducts_supplier 
FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- 2. travelproducts 父产品关联（自关联）
ALTER TABLE travelproducts 
ADD CONSTRAINT fk_travelproducts_parent 
FOREIGN KEY (parent_product_id) REFERENCES travelproducts(id) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- 3. tour_project 关联到 travelproducts
ALTER TABLE tour_project 
ADD CONSTRAINT fk_tour_project_base_product 
FOREIGN KEY (base_product_id) REFERENCES travelproducts(id) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- ========================================
-- 第四部分：创建索引优化查询性能
-- ========================================

-- 1. 供应商索引
CREATE INDEX idx_travelproducts_supplier ON travelproducts(supplier_id);

-- 2. 国家城市联合索引
CREATE INDEX idx_travelproducts_country_city ON travelproducts(country, city_name);

-- 3. 产品状态索引
CREATE INDEX idx_travelproducts_status ON travelproducts(product_status);

-- 4. 产品编号索引（如果不是 UNIQUE 已自动创建索引）
-- CREATE INDEX idx_travelproducts_code ON travelproducts(product_code);

-- 5. tour_project 基础产品索引
CREATE INDEX idx_tour_project_base_product ON tour_project(base_product_id);

-- 6. 创建人索引
CREATE INDEX idx_travelproducts_created_by ON travelproducts(created_by);

-- ========================================
-- 第五部分：数据清理和优化（可选）
-- ========================================

-- 将 city_name 对应的国家填充到 country 字段
-- UPDATE travelproducts t
-- SET country = (
--     SELECT country_name 
--     FROM travel_products_city c
--     WHERE c.city_name = t.city_name 
--     LIMIT 1
-- )
-- WHERE country IS NULL AND city_name IS NOT NULL;

-- ========================================
-- 第六部分：验证迁移结果
-- ========================================

-- 1. 检查 travelproducts 表结构
SELECT 'Checking travelproducts table structure...' AS Step;
DESCRIBE travelproducts;

-- 2. 检查 tour_project 表结构
SELECT 'Checking tour_project table structure...' AS Step;
DESCRIBE tour_project;

-- 3. 检查外键约束
SELECT 'Checking foreign key constraints...' AS Step;
SELECT 
    CONSTRAINT_NAME AS '约束名称', 
    TABLE_NAME AS '表名', 
    COLUMN_NAME AS '列名', 
    REFERENCED_TABLE_NAME AS '引用表', 
    REFERENCED_COLUMN_NAME AS '引用列'
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'travel_panel_new' 
    AND TABLE_NAME IN ('travelproducts', 'tour_project')
    AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- 4. 检查索引
SELECT 'Checking indexes...' AS Step;
SHOW INDEX FROM travelproducts WHERE Key_name NOT IN ('PRIMARY');

-- 5. 统计信息
SELECT 'Migration Statistics...' AS Step;
SELECT 
    COUNT(*) AS total_products,
    COUNT(DISTINCT supplier_id) AS products_with_supplier,
    COUNT(DISTINCT country) AS distinct_countries,
    COUNT(DISTINCT city_name) AS distinct_cities,
    SUM(CASE WHEN cover_image IS NOT NULL THEN 1 ELSE 0 END) AS products_with_cover,
    SUM(CASE WHEN product_status = 'active' THEN 1 ELSE 0 END) AS active_products
FROM travelproducts;

-- ========================================
-- 完成提示
-- ========================================
SELECT 
    '✅ Tour Product Enhancement Migration Completed Successfully!' AS Status,
    NOW() AS CompletedAt;

