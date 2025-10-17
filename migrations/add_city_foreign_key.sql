-- ========================================
-- 为 travelproducts.city_name 添加外键关联到 travel_products_city
-- ========================================

USE travel_panel_new;

-- ========================================
-- 步骤 1: 检查当前数据
-- ========================================

SELECT '=== 步骤 1: 检查城市数据 ===' AS Step;

-- 查看 travelproducts 中有哪些城市
SELECT DISTINCT city_name, COUNT(*) AS product_count
FROM travelproducts
WHERE city_name IS NOT NULL AND city_name != ''
GROUP BY city_name
ORDER BY city_name;

-- 查看 travel_products_city 中有哪些城市
SELECT city_name, country_name, display_name
FROM travel_products_city
ORDER BY city_name;

-- ========================================
-- 步骤 2: 检查数据一致性
-- ========================================

SELECT '=== 步骤 2: 检查是否有孤立的城市名（不在字典表中） ===' AS Step;

SELECT DISTINCT tp.city_name
FROM travelproducts tp
WHERE tp.city_name IS NOT NULL 
  AND tp.city_name != ''
  AND NOT EXISTS (
      SELECT 1 FROM travel_products_city tpc
      WHERE tpc.city_name = tp.city_name
  )
ORDER BY tp.city_name;

-- ========================================
-- 步骤 3: 为缺失的城市创建记录（可选）
-- ========================================

SELECT '=== 步骤 3: 为缺失的城市创建字典记录 ===' AS Step;

-- 注意：这里假设国家名称与城市名称相同，实际使用时需要手动调整
INSERT INTO travel_products_city (city_name, country_name, display_name)
SELECT DISTINCT
    tp.city_name,
    tp.country AS country_name,  -- 从产品的country字段获取
    tp.city_name AS display_name
FROM travelproducts tp
WHERE tp.city_name IS NOT NULL 
  AND tp.city_name != ''
  AND NOT EXISTS (
      SELECT 1 FROM travel_products_city tpc
      WHERE tpc.city_name = tp.city_name
  );

SELECT CONCAT('✅ 新创建了 ', ROW_COUNT(), ' 个城市记录') AS Result;

-- ========================================
-- 步骤 4: 添加外键约束
-- ========================================

SELECT '=== 步骤 4: 添加外键约束 ===' AS Step;

-- 先检查是否已存在该外键
SELECT CONSTRAINT_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'travel_panel_new'
  AND TABLE_NAME = 'travelproducts'
  AND COLUMN_NAME = 'city_name'
  AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 如果没有外键，则添加
-- 注意：如果已存在外键，这条语句会报错，可以忽略
ALTER TABLE travelproducts
ADD CONSTRAINT fk_product_city
FOREIGN KEY (city_name) REFERENCES travel_products_city(city_name)
ON UPDATE CASCADE
ON DELETE SET NULL;

SELECT '✅ 外键约束已添加' AS Status;

-- ========================================
-- 步骤 5: 验证外键
-- ========================================

SELECT '=== 步骤 5: 验证外键关联 ===' AS Step;

-- 查看外键信息
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'travel_panel_new'
  AND TABLE_NAME = 'travelproducts'
  AND COLUMN_NAME = 'city_name';

-- 测试关联查询
SELECT 
    tp.id,
    tp.product_name,
    tp.city_name,
    tpc.country_name,
    tpc.display_name
FROM travelproducts tp
LEFT JOIN travel_products_city tpc ON tp.city_name = tpc.city_name
WHERE tp.city_name IS NOT NULL
LIMIT 10;

SELECT '✅ 外键关联完成！' AS Status;
SELECT '💡 现在可以通过 city 关系访问城市的国家信息' AS Note;

