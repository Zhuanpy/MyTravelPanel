-- ========================================
-- 检查并迁移 company_name 到 suppliers 表
-- ========================================

USE travel_panel_new;

-- ========================================
-- 步骤 1: 检查当前数据状态
-- ========================================

SELECT '=== 步骤 1: 检查 company_name 数据 ===' AS Step;

-- 查看有多少产品有 company_name
SELECT 
    COUNT(*) AS total_products,
    COUNT(CASE WHEN company_name IS NOT NULL AND company_name != '' THEN 1 END) AS has_company_name,
    COUNT(CASE WHEN supplier_id IS NOT NULL AND supplier_id > 0 THEN 1 END) AS has_supplier_id,
    COUNT(CASE WHEN company_name IS NOT NULL AND (supplier_id IS NULL OR supplier_id = 0) THEN 1 END) AS need_migration
FROM travelproducts;

-- 查看所有不同的 company_name
SELECT DISTINCT company_name, COUNT(*) AS product_count
FROM travelproducts
WHERE company_name IS NOT NULL AND company_name != ''
GROUP BY company_name
ORDER BY company_name;

-- ========================================
-- 步骤 2: 检查这些公司是否已存在于 suppliers 表
-- ========================================

SELECT '=== 步骤 2: 检查 suppliers 表中已存在的公司 ===' AS Step;

SELECT 
    tp.company_name,
    COUNT(tp.id) AS product_count,
    s.supplier_id,
    s.name AS supplier_name,
    CASE 
        WHEN s.supplier_id IS NOT NULL THEN '已存在'
        ELSE '需要创建'
    END AS status
FROM travelproducts tp
LEFT JOIN suppliers s ON tp.company_name = s.name
WHERE tp.company_name IS NOT NULL AND tp.company_name != ''
GROUP BY tp.company_name, s.supplier_id, s.name
ORDER BY tp.company_name;

-- ========================================
-- 步骤 3: 为不存在的公司创建 supplier 记录
-- ========================================

SELECT '=== 步骤 3: 创建缺失的 supplier 记录 ===' AS Step;

INSERT INTO suppliers (name, supplier_type, status, created_at, last_updated)
SELECT DISTINCT
    tp.company_name AS name,
    'local_operator' AS supplier_type,
    'active' AS status,
    NOW() AS created_at,
    NOW() AS last_updated
FROM travelproducts tp
WHERE tp.company_name IS NOT NULL 
  AND tp.company_name != ''
  AND NOT EXISTS (
      SELECT 1 FROM suppliers s 
      WHERE s.name = tp.company_name
  );

SELECT CONCAT('✅ 新创建了 ', ROW_COUNT(), ' 个供应商记录') AS Result;

-- ========================================
-- 步骤 4: 更新 travelproducts 的 supplier_id
-- ========================================

SELECT '=== 步骤 4: 更新 supplier_id ===' AS Step;

UPDATE travelproducts tp
INNER JOIN suppliers s ON tp.company_name = s.name
SET tp.supplier_id = s.supplier_id
WHERE tp.company_name IS NOT NULL 
  AND tp.company_name != ''
  AND (tp.supplier_id IS NULL OR tp.supplier_id = 0);

SELECT CONCAT('✅ 更新了 ', ROW_COUNT(), ' 个产品的 supplier_id') AS Result;

-- ========================================
-- 步骤 5: 验证迁移结果
-- ========================================

SELECT '=== 步骤 5: 验证迁移结果 ===' AS Step;

-- 检查还有多少产品没有 supplier_id
SELECT 
    COUNT(*) AS products_without_supplier
FROM travelproducts
WHERE company_name IS NOT NULL 
  AND company_name != ''
  AND (supplier_id IS NULL OR supplier_id = 0);

-- 查看迁移后的数据（前10条）
SELECT 
    tp.id,
    tp.product_name,
    tp.company_name,
    tp.supplier_id,
    s.name AS supplier_name,
    s.supplier_type
FROM travelproducts tp
LEFT JOIN suppliers s ON tp.supplier_id = s.supplier_id
WHERE tp.company_name IS NOT NULL
ORDER BY tp.id
LIMIT 10;

-- ========================================
-- 完成
-- ========================================

SELECT '✅ 数据迁移完成！' AS Status;
SELECT '💡 现在 company_name 已通过 supplier_id 关联到 suppliers 表' AS Note;

