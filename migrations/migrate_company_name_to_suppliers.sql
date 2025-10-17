-- ========================================
-- 迁移 travelproducts.company_name 到 suppliers 表
-- 目的：规范化数据，避免冗余
-- ========================================

USE travel_panel_new;

-- ========================================
-- 步骤 1：检查当前数据状态
-- ========================================

SELECT '检查当前数据状态...' AS Step;

-- 查看有多少产品有 company_name 但没有 supplier_id
SELECT 
    COUNT(*) AS products_with_company_name_only,
    COUNT(DISTINCT company_name) AS distinct_companies
FROM travelproducts
WHERE company_name IS NOT NULL 
  AND (supplier_id IS NULL OR supplier_id = 0);

-- 查看这些公司名称
SELECT DISTINCT company_name
FROM travelproducts
WHERE company_name IS NOT NULL 
  AND (supplier_id IS NULL OR supplier_id = 0)
ORDER BY company_name;

-- ========================================
-- 步骤 2：为缺失的公司创建供应商记录
-- ========================================

SELECT '为缺失的公司创建供应商记录...' AS Step;

-- 插入新供应商（只插入不存在的）
INSERT INTO suppliers (name, supplier_type, contact_email, status, created_at)
SELECT DISTINCT
    tp.company_name,
    'tour_operator' AS supplier_type,
    CONCAT(LOWER(REPLACE(tp.company_name, ' ', '_')), '@example.com') AS contact_email,
    'active' AS status,
    NOW() AS created_at
FROM travelproducts tp
WHERE tp.company_name IS NOT NULL 
  AND (tp.supplier_id IS NULL OR tp.supplier_id = 0)
  AND NOT EXISTS (
      SELECT 1 FROM suppliers s 
      WHERE s.name = tp.company_name
  );

SELECT '新增供应商数量：', ROW_COUNT() AS inserted_count;

-- ========================================
-- 步骤 3：更新产品的 supplier_id
-- ========================================

SELECT '更新产品的 supplier_id...' AS Step;

UPDATE travelproducts tp
INNER JOIN suppliers s ON tp.company_name = s.name
SET tp.supplier_id = s.supplier_id
WHERE tp.company_name IS NOT NULL 
  AND (tp.supplier_id IS NULL OR tp.supplier_id = 0);

SELECT '更新产品数量：', ROW_COUNT() AS updated_count;

-- ========================================
-- 步骤 4：验证迁移结果
-- ========================================

SELECT '验证迁移结果...' AS Step;

-- 检查还有多少产品没有 supplier_id
SELECT 
    COUNT(*) AS products_without_supplier,
    COUNT(DISTINCT company_name) AS distinct_company_names
FROM travelproducts
WHERE company_name IS NOT NULL 
  AND (supplier_id IS NULL OR supplier_id = 0);

-- 检查迁移后的数据
SELECT 
    tp.id,
    tp.product_name,
    tp.company_name AS old_company_name,
    s.name AS supplier_name,
    tp.supplier_id
FROM travelproducts tp
LEFT JOIN suppliers s ON tp.supplier_id = s.supplier_id
WHERE tp.company_name IS NOT NULL
LIMIT 10;

-- ========================================
-- 步骤 5（可选）：清理 company_name 字段
-- ========================================

-- 注意：执行此步骤前请确保步骤 1-4 都成功完成！
-- 如果确认迁移成功，可以将 company_name 设置为 NULL

/*
UPDATE travelproducts
SET company_name = NULL
WHERE supplier_id IS NOT NULL;

SELECT '已清理 company_name 字段' AS Status;
*/

-- ========================================
-- 完成提示
-- ========================================

SELECT '✅ 迁移完成！' AS Status;
SELECT '💡 提示：company_name 字段已保留作为备用，可以稍后手动清理' AS Note;

