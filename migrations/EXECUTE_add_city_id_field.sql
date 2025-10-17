-- ========================================
-- 为 travelproducts 添加 city_id 字段并关联
-- 保留 city_name 作为冗余字段方便查询
-- ========================================

USE travel_panel_new;

-- ========================================
-- 步骤 1: 添加 city_id 字段
-- ========================================

SELECT '=== 步骤 1: 添加 city_id 字段 ===' AS Step;

ALTER TABLE travelproducts
ADD COLUMN city_id INT NULL COMMENT '城市ID' AFTER country;

SELECT '✅ city_id 字段已添加' AS Status;

-- ========================================
-- 步骤 2: 为 travel_products_city 添加唯一索引
-- ========================================

SELECT '=== 步骤 2: 添加唯一索引 ===' AS Step;

-- 检查是否有重复的城市名
SELECT city_name, COUNT(*) AS count
FROM travel_products_city
GROUP BY city_name
HAVING COUNT(*) > 1;

-- 检查并添加唯一索引（如果不存在）
SET @index_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = 'travel_panel_new'
      AND TABLE_NAME = 'travel_products_city'
      AND INDEX_NAME = 'idx_city_name'
);

SET @sql = IF(@index_exists = 0, 
    'ALTER TABLE travel_products_city ADD UNIQUE INDEX idx_city_name (city_name)',
    'SELECT "索引 idx_city_name 已存在" AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT '✅ 唯一索引已添加' AS Status;

-- ========================================
-- 步骤 3: 为缺失的城市创建记录
-- ========================================

SELECT '=== 步骤 3: 检查并创建缺失的城市 ===' AS Step;

-- 查看缺失的城市
SELECT DISTINCT tp.city_name, tp.country
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
-- 步骤 4: 填充 city_id（根据 city_name 匹配）
-- ========================================

SELECT '=== 步骤 4: 填充 city_id ===' AS Step;

SET SQL_SAFE_UPDATES = 0;

UPDATE travelproducts tp
INNER JOIN travel_products_city tpc ON tp.city_name = tpc.city_name
SET tp.city_id = tpc.id
WHERE tp.city_name IS NOT NULL 
  AND tp.city_name != '';

SET SQL_SAFE_UPDATES = 1;

SELECT CONCAT('✅ 更新了 ', ROW_COUNT(), ' 个产品的 city_id') AS Result;

-- ========================================
-- 步骤 5: 添加外键约束
-- ========================================

SELECT '=== 步骤 5: 添加外键约束 ===' AS Step;

ALTER TABLE travelproducts
ADD CONSTRAINT fk_product_city_id
FOREIGN KEY (city_id) 
REFERENCES travel_products_city(id)
ON UPDATE CASCADE
ON DELETE SET NULL;

SELECT '✅ 外键约束已添加' AS Status;

-- ========================================
-- 步骤 6: 验证结果
-- ========================================

SELECT '=== 步骤 6: 验证外键关联 ===' AS Step;

-- 查看外键信息
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'travel_panel_new'
  AND TABLE_NAME = 'travelproducts'
  AND COLUMN_NAME = 'city_id';

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
    COUNT(*) AS total,
    COUNT(CASE WHEN tp.city_name = tpc.city_name THEN 1 END) AS matched,
    COUNT(CASE WHEN tp.city_name != tpc.city_name THEN 1 END) AS mismatched
FROM travelproducts tp
LEFT JOIN travel_products_city tpc ON tp.city_id = tpc.id
WHERE tp.city_id IS NOT NULL;

SELECT '✅ city_id 外键关联配置完成！' AS Status;
SELECT '💡 现在 city_id 是主关联，city_name 保留作为冗余字段' AS Note;

