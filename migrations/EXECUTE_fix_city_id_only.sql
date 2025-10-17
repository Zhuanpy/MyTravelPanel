-- ========================================
-- 只填充和修复 city_id（字段已存在的情况）
-- ========================================

USE travel_panel_new;

-- ========================================
-- 步骤 1: 检查当前状态
-- ========================================

SELECT '=== 步骤 1: 检查当前状态 ===' AS Step;

SELECT 
    COUNT(*) AS total_products,
    COUNT(city_id) AS has_city_id,
    COUNT(*) - COUNT(city_id) AS missing_city_id,
    COUNT(city_name) AS has_city_name
FROM travelproducts;

-- ========================================
-- 步骤 2: 为缺失的城市创建记录
-- ========================================

SELECT '=== 步骤 2: 创建缺失的城市记录 ===' AS Step;

-- 查看缺失的城市
SELECT DISTINCT 
    tp.city_name, 
    tp.country,
    'Will be created' AS status
FROM travelproducts tp
WHERE tp.city_name IS NOT NULL 
  AND tp.city_name != ''
  AND NOT EXISTS (
      SELECT 1 FROM travel_products_city tpc
      WHERE tpc.city_name = tp.city_name
  );

-- 创建缺失的城市记录
INSERT INTO travel_products_city (city_name, country_name, display_name)
SELECT DISTINCT
    tp.city_name,
    COALESCE(tp.country, '未知'),
    tp.city_name
FROM travelproducts tp
WHERE tp.city_name IS NOT NULL 
  AND tp.city_name != ''
  AND NOT EXISTS (
      SELECT 1 FROM travel_products_city tpc
      WHERE tpc.city_name = tp.city_name
  );

SELECT CONCAT('✅ 新创建了 ', ROW_COUNT(), ' 个城市记录') AS Result;

-- ========================================
-- 步骤 3: 填充 city_id
-- ========================================

SELECT '=== 步骤 3: 填充 city_id ===' AS Step;

SET SQL_SAFE_UPDATES = 0;

-- 填充所有有 city_name 但 city_id 为 NULL 的记录
UPDATE travelproducts tp
INNER JOIN travel_products_city tpc ON tp.city_name = tpc.city_name
SET tp.city_id = tpc.id
WHERE tp.city_name IS NOT NULL 
  AND tp.city_name != ''
  AND tp.city_id IS NULL;

SELECT CONCAT('✅ 更新了 ', ROW_COUNT(), ' 个产品的 city_id') AS Result;

SET SQL_SAFE_UPDATES = 1;

-- ========================================
-- 步骤 4: 添加外键约束（如果不存在）
-- ========================================

SELECT '=== 步骤 4: 检查并添加外键约束 ===' AS Step;

-- 检查外键是否已存在
SELECT 
    CONSTRAINT_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'travel_panel_new'
  AND TABLE_NAME = 'travelproducts'
  AND COLUMN_NAME = 'city_id'
  AND CONSTRAINT_NAME = 'fk_product_city_id';

-- 如果外键不存在，则添加
-- 注意：如果已存在会报错，需要手动判断
ALTER TABLE travelproducts
ADD CONSTRAINT fk_product_city_id
FOREIGN KEY (city_id) 
REFERENCES travel_products_city(id)
ON UPDATE CASCADE
ON DELETE SET NULL;

SELECT '✅ 外键约束已添加' AS Status;

-- ========================================
-- 步骤 5: 验证结果
-- ========================================

SELECT '=== 步骤 5: 验证结果 ===' AS Step;

-- 查看最终统计
SELECT 
    COUNT(*) AS total_products,
    COUNT(city_id) AS has_city_id,
    COUNT(*) - COUNT(city_id) AS missing_city_id,
    COUNT(city_name) AS has_city_name
FROM travelproducts;

-- 测试关联查询
SELECT 
    tp.id,
    tp.product_name,
    tp.city_id,
    tp.city_name AS product_city_name,
    tpc.city_name AS city_dict_name,
    tpc.country_name
FROM travelproducts tp
LEFT JOIN travel_products_city tpc ON tp.city_id = tpc.id
WHERE tp.city_id IS NOT NULL
LIMIT 10;

-- 检查数据一致性
SELECT 
    CASE 
        WHEN COUNT(*) = COUNT(CASE WHEN tp.city_name = tpc.city_name THEN 1 END) 
        THEN '✅ 所有数据一致'
        ELSE '⚠️ 存在不一致数据'
    END AS consistency_check,
    COUNT(*) AS total,
    COUNT(CASE WHEN tp.city_name = tpc.city_name THEN 1 END) AS matched,
    COUNT(CASE WHEN tp.city_name != tpc.city_name THEN 1 END) AS mismatched
FROM travelproducts tp
LEFT JOIN travel_products_city tpc ON tp.city_id = tpc.id
WHERE tp.city_id IS NOT NULL;

SELECT '✅ city_id 修复完成！' AS Status;

