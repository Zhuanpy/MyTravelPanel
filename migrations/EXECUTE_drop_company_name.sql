-- ========================================
-- 删除 travelproducts 表的 company_name 字段
-- 前提：supplier_id 已全部填充完整
-- ========================================

USE travel_panel_new;

-- 步骤 1: 最后检查（确保没有遗漏）
SELECT '=== 检查是否还有产品缺少 supplier_id ===' AS Step;

SELECT 
    COUNT(*) AS total_products,
    COUNT(CASE WHEN supplier_id IS NULL OR supplier_id = 0 THEN 1 END) AS missing_supplier_id,
    COUNT(CASE WHEN company_name IS NOT NULL THEN 1 END) AS has_company_name
FROM travelproducts;

-- 显示缺少 supplier_id 的产品（如果有）
SELECT 
    id, 
    product_name, 
    company_name, 
    supplier_id
FROM travelproducts
WHERE supplier_id IS NULL OR supplier_id = 0
LIMIT 5;

-- 步骤 2: 删除 company_name 字段
SELECT '=== 删除 company_name 字段 ===' AS Step;

ALTER TABLE travelproducts DROP COLUMN company_name;

-- 步骤 3: 验证删除结果
SELECT '=== 验证结果 ===' AS Step;

DESCRIBE travelproducts;

SELECT '✅ company_name 字段已删除！' AS Status;
SELECT '💡 所有公司信息现在通过 supplier_id 关联获取' AS Note;

