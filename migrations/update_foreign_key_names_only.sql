-- 更新外键约束名称脚本（表已重命名的情况下使用）
-- 此脚本只更新外键约束名称，不重命名表
-- 执行时间：请在维护窗口期间执行

-- ============================================
-- 步骤 1: 检查当前表状态
-- ============================================
-- 检查表是否存在
SHOW TABLES LIKE 'package_itinerary';
SHOW TABLES LIKE 'package_price_variant';

-- ============================================
-- 步骤 2: 查询当前外键约束名称
-- ============================================
SELECT 
    TABLE_NAME AS '表名',
    CONSTRAINT_NAME AS '当前外键约束名称',
    COLUMN_NAME AS '列名',
    REFERENCED_TABLE_NAME AS '引用表名'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_NAME IN ('package_itinerary', 'package_price_variant')
    AND COLUMN_NAME = 'product_id' 
    AND REFERENCED_TABLE_NAME = 'package_products'
ORDER BY TABLE_NAME;

-- ============================================
-- 步骤 3: 自动更新外键约束名称（使用动态SQL）
-- ============================================

-- 更新 package_itinerary 表的外键约束
SET @fk_name = (
    SELECT CONSTRAINT_NAME 
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
    WHERE TABLE_NAME = 'package_itinerary' 
        AND COLUMN_NAME = 'product_id' 
        AND REFERENCED_TABLE_NAME = 'package_products'
    LIMIT 1
);

-- 如果找到了外键约束，则更新
SET @sql = CONCAT('ALTER TABLE `package_itinerary` DROP FOREIGN KEY `', @fk_name, '`');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE `package_itinerary` 
ADD CONSTRAINT `fk_package_itinerary_product` 
FOREIGN KEY (`product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE CASCADE 
ON UPDATE CASCADE;

-- 更新 package_price_variant 表的外键约束
SET @fk_name = (
    SELECT CONSTRAINT_NAME 
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
    WHERE TABLE_NAME = 'package_price_variant' 
        AND COLUMN_NAME = 'product_id' 
        AND REFERENCED_TABLE_NAME = 'package_products'
    LIMIT 1
);

-- 如果找到了外键约束，则更新
SET @sql = CONCAT('ALTER TABLE `package_price_variant` DROP FOREIGN KEY `', @fk_name, '`');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE `package_price_variant` 
ADD CONSTRAINT `fk_package_price_variant_product` 
FOREIGN KEY (`product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE CASCADE 
ON UPDATE CASCADE;

-- ============================================
-- 步骤 4: 验证更新结果
-- ============================================
SELECT 
    TABLE_NAME AS '表名',
    COLUMN_NAME AS '列名',
    CONSTRAINT_NAME AS '新约束名称',
    REFERENCED_TABLE_NAME AS '引用表名',
    REFERENCED_COLUMN_NAME AS '引用列名'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE REFERENCED_TABLE_NAME = 'package_products'
    AND TABLE_NAME IN ('package_itinerary', 'package_price_variant')
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

