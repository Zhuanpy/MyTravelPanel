-- ========================================
-- 删除 travelproducts.country 字段
-- 保留 city_name 作为冗余字段
-- 通过 city_id 关联获取国家信息
-- ========================================

USE travel_panel_new;

-- ========================================
-- 步骤 1: 检查当前 country 字段使用情况
-- ========================================

SELECT '=== 步骤 1: 检查 country 字段数据 ===' AS Step;

SELECT 
    COUNT(*) AS total_products,
    COUNT(country) AS has_country,
    COUNT(*) - COUNT(country) AS missing_country
FROM travelproducts;

-- 查看 country 和 city 的对应情况
SELECT 
    tp.country AS product_country,
    tpc.country_name AS city_country,
    COUNT(*) AS count,
    CASE 
        WHEN tp.country = tpc.country_name THEN '✅ 一致'
        WHEN tp.country IS NULL THEN '⚠️ 产品无country'
        ELSE '❌ 不一致'
    END AS status
FROM travelproducts tp
LEFT JOIN travel_products_city tpc ON tp.city_id = tpc.id
GROUP BY tp.country, tpc.country_name
ORDER BY count DESC;

-- ========================================
-- 步骤 2: 备份 country 数据（可选）
-- ========================================

SELECT '=== 步骤 2: 查看将被删除的数据 ===' AS Step;

SELECT 
    id,
    product_name,
    country,
    city_id,
    city_name
FROM travelproducts
WHERE country IS NOT NULL
LIMIT 20;

-- ========================================
-- 步骤 3: 删除 country 字段
-- ========================================

SELECT '=== 步骤 3: 删除 country 字段 ===' AS Step;

ALTER TABLE travelproducts
DROP COLUMN country;

SELECT '✅ country 字段已删除' AS Status;

-- ========================================
-- 步骤 4: 验证结果
-- ========================================

SELECT '=== 步骤 4: 验证字段已删除 ===' AS Step;

-- 检查字段是否还存在
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'travel_panel_new'
  AND TABLE_NAME = 'travelproducts'
  AND COLUMN_NAME IN ('country', 'city_id', 'city_name');

-- 测试通过 city_id 获取国家信息
SELECT 
    tp.id,
    tp.product_name,
    tp.city_id,
    tp.city_name,
    tpc.country_name AS country_from_city
FROM travelproducts tp
LEFT JOIN travel_products_city tpc ON tp.city_id = tpc.id
WHERE tp.city_id IS NOT NULL
LIMIT 10;

SELECT '✅ country 字段删除完成！' AS Status;
SELECT '💡 现在通过 city_id 关联获取国家信息，city_name 保留作为冗余字段方便查询' AS Note;

