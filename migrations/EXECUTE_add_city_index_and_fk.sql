-- ========================================
-- 为 travel_products_city 添加索引并创建外键
-- ========================================

USE travel_panel_new;

-- ========================================
-- 步骤 1: 检查 travel_products_city 表结构
-- ========================================

SELECT '=== 步骤 1: 检查表结构 ===' AS Step;

DESCRIBE travel_products_city;

-- 查看现有索引
SHOW INDEX FROM travel_products_city;

-- ========================================
-- 步骤 2: 为 city_name 添加唯一索引
-- ========================================

SELECT '=== 步骤 2: 添加唯一索引 ===' AS Step;

-- 检查是否有重复的 city_name
SELECT city_name, COUNT(*) AS count
FROM travel_products_city
GROUP BY city_name
HAVING COUNT(*) > 1;

-- 如果没有重复，添加唯一索引
-- 如果有重复，需要先清理重复数据
ALTER TABLE travel_products_city
ADD UNIQUE INDEX idx_city_name (city_name);

SELECT '✅ 唯一索引已添加' AS Status;

-- ========================================
-- 步骤 3: 检查孤立的城市名（不在字典表中的）
-- ========================================

SELECT '=== 步骤 3: 检查孤立城市 ===' AS Step;

SELECT DISTINCT tp.city_name, tp.country
FROM travelproducts tp
WHERE tp.city_name IS NOT NULL 
  AND tp.city_name != ''
  AND NOT EXISTS (
      SELECT 1 FROM travel_products_city tpc
      WHERE tpc.city_name = tp.city_name
  );

-- ========================================
-- 步骤 4: 为缺失的城市创建记录
-- ========================================

SELECT '=== 步骤 4: 创建缺失的城市记录 ===' AS Step;

INSERT INTO travel_products_city (city_name, country_name, display_name)
SELECT DISTINCT
    tp.city_name,
    tp.country,
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
-- 步骤 5: 添加外键约束
-- ========================================

SELECT '=== 步骤 5: 添加外键约束 ===' AS Step;

ALTER TABLE travelproducts
ADD CONSTRAINT fk_product_city
FOREIGN KEY (city_name) 
REFERENCES travel_products_city(city_name)
ON UPDATE CASCADE
ON DELETE SET NULL;

SELECT '✅ 外键约束已添加' AS Status;

-- ========================================
-- 步骤 6: 验证外键
-- ========================================

SELECT '=== 步骤 6: 验证外键关联 ===' AS Step;

-- 查看外键信息
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME,
    UPDATE_RULE,
    DELETE_RULE
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
  ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE kcu.TABLE_SCHEMA = 'travel_panel_new'
  AND kcu.TABLE_NAME = 'travelproducts'
  AND kcu.COLUMN_NAME = 'city_name';

-- 测试关联查询
SELECT 
    tp.id,
    tp.product_name,
    tp.city_name,
    tp.country AS product_country,
    tpc.country_name AS city_country,
    tpc.display_name
FROM travelproducts tp
LEFT JOIN travel_products_city tpc ON tp.city_name = tpc.city_name
WHERE tp.city_name IS NOT NULL
LIMIT 10;

SELECT '✅ 城市外键关联配置完成！' AS Status;

