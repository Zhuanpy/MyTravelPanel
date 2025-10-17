-- ========================================
-- 检查 city_id 字段和外键的当前状态
-- ========================================

USE travel_panel_new;

-- 1. 检查 city_id 字段是否存在
SELECT '=== 检查 city_id 字段 ===' AS Step;

SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_KEY,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'travel_panel_new'
  AND TABLE_NAME = 'travelproducts'
  AND COLUMN_NAME = 'city_id';

-- 2. 检查外键约束是否存在
SELECT '=== 检查外键约束 ===' AS Step;

SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'travel_panel_new'
  AND TABLE_NAME = 'travelproducts'
  AND COLUMN_NAME = 'city_id';

-- 3. 检查 city_id 数据填充情况
SELECT '=== 检查 city_id 数据 ===' AS Step;

SELECT 
    COUNT(*) AS total_products,
    COUNT(city_id) AS has_city_id,
    COUNT(*) - COUNT(city_id) AS missing_city_id,
    COUNT(city_name) AS has_city_name
FROM travelproducts;

-- 4. 检查不一致的数据（city_name 有值但 city_id 为空）
SELECT '=== 检查需要填充的数据 ===' AS Step;

SELECT 
    tp.id,
    tp.product_name,
    tp.city_id,
    tp.city_name,
    tpc.id AS city_dict_id
FROM travelproducts tp
LEFT JOIN travel_products_city tpc ON tp.city_name = tpc.city_name
WHERE tp.city_name IS NOT NULL 
  AND tp.city_name != ''
  AND tp.city_id IS NULL
LIMIT 10;

SELECT '✅ 状态检查完成' AS Status;

