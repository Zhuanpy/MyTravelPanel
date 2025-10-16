-- ========================================
-- 步骤 2: 添加外键约束和索引
-- 执行前确保步骤1已成功完成！
-- ========================================

USE travel_panel_new;

-- ========================================
-- 1. 添加外键约束
-- ========================================

-- travelproducts → suppliers
ALTER TABLE travelproducts 
ADD CONSTRAINT fk_travelproducts_supplier 
FOREIGN KEY (supplier_id) 
REFERENCES suppliers(supplier_id) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- travelproducts 自关联（版本管理）
ALTER TABLE travelproducts 
ADD CONSTRAINT fk_travelproducts_parent 
FOREIGN KEY (parent_product_id) 
REFERENCES travelproducts(id) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- tour_project → travelproducts
ALTER TABLE tour_project 
ADD CONSTRAINT fk_tour_project_base_product 
FOREIGN KEY (base_product_id) 
REFERENCES travelproducts(id) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- ========================================
-- 2. 创建索引
-- ========================================

-- 供应商索引
CREATE INDEX idx_travelproducts_supplier ON travelproducts(supplier_id);

-- 国家+城市联合索引
CREATE INDEX idx_travelproducts_country_city ON travelproducts(country, city_name);

-- 产品状态索引
CREATE INDEX idx_travelproducts_status ON travelproducts(product_status);

-- tour_project 基础产品索引
CREATE INDEX idx_tour_project_base_product ON tour_project(base_product_id);

-- 创建人索引
CREATE INDEX idx_travelproducts_created_by ON travelproducts(created_by);

-- product_code 已经是 UNIQUE，自动创建了索引

-- ========================================
-- 3. 验证约束和索引
-- ========================================

SELECT '✅ Step 2 Completed: Constraints and Indexes Added!' AS Status;

-- 查看外键约束
SELECT 
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'travel_panel_new' 
    AND TABLE_NAME IN ('travelproducts', 'tour_project')
    AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME;

-- 查看索引
SHOW INDEX FROM travelproducts;
SHOW INDEX FROM tour_project;

