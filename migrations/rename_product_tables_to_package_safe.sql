-- 数据库迁移脚本：将 product_itinerary 和 product_price_variant 重命名为 package_ 开头
-- 执行时间：请在维护窗口期间执行
-- 备份建议：执行前请先备份数据库
-- 注意：此版本先查询外键名称，然后安全删除

-- ============================================
-- 步骤 1: 查询当前外键约束名称
-- ============================================
-- 先执行此查询，获取实际的外键约束名称
SELECT 
    TABLE_NAME AS '表名',
    CONSTRAINT_NAME AS '外键约束名称',
    COLUMN_NAME AS '列名',
    REFERENCED_TABLE_NAME AS '引用表名'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_NAME IN ('product_itinerary', 'product_price_variant')
    AND REFERENCED_TABLE_NAME = 'travelproducts'
    OR (TABLE_NAME IN ('package_itinerary', 'package_price_variant')
        AND REFERENCED_TABLE_NAME = 'package_products')
ORDER BY TABLE_NAME;

-- ============================================
-- 步骤 2: 重命名表
-- ============================================
RENAME TABLE `product_itinerary` TO `package_itinerary`;
RENAME TABLE `product_price_variant` TO `package_price_variant`;

-- ============================================
-- 步骤 3: 更新外键约束名称（需要根据步骤1的查询结果替换约束名称）
-- ============================================

-- 方法一：如果知道确切的外键约束名称，直接执行
-- 更新 package_itinerary 表的外键约束名称
-- 注意：请将 'product_itinerary_ibfk_1' 替换为步骤1查询到的实际约束名称
SET @fk_name_itinerary = (
    SELECT CONSTRAINT_NAME 
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
    WHERE TABLE_NAME = 'package_itinerary' 
        AND COLUMN_NAME = 'product_id' 
        AND REFERENCED_TABLE_NAME = 'package_products'
    LIMIT 1
);

SET @sql_itinerary = CONCAT('ALTER TABLE `package_itinerary` DROP FOREIGN KEY `', @fk_name_itinerary, '`');
PREPARE stmt_itinerary FROM @sql_itinerary;
EXECUTE stmt_itinerary;
DEALLOCATE PREPARE stmt_itinerary;

ALTER TABLE `package_itinerary` 
ADD CONSTRAINT `fk_package_itinerary_product` 
FOREIGN KEY (`product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE CASCADE 
ON UPDATE CASCADE;

-- 更新 package_price_variant 表的外键约束名称
-- 注意：请将 'product_price_variant_ibfk_1' 替换为步骤1查询到的实际约束名称
SET @fk_name_variant = (
    SELECT CONSTRAINT_NAME 
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
    WHERE TABLE_NAME = 'package_price_variant' 
        AND COLUMN_NAME = 'product_id' 
        AND REFERENCED_TABLE_NAME = 'package_products'
    LIMIT 1
);

SET @sql_variant = CONCAT('ALTER TABLE `package_price_variant` DROP FOREIGN KEY `', @fk_name_variant, '`');
PREPARE stmt_variant FROM @sql_variant;
EXECUTE stmt_variant;
DEALLOCATE PREPARE stmt_variant;

ALTER TABLE `package_price_variant` 
ADD CONSTRAINT `fk_package_price_variant_product` 
FOREIGN KEY (`product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE CASCADE 
ON UPDATE CASCADE;

-- ============================================
-- 步骤 4: 验证迁移结果
-- ============================================
-- 验证表是否存在
SHOW TABLES LIKE 'package_itinerary';
SHOW TABLES LIKE 'package_price_variant';

-- 验证外键关系
SELECT 
    TABLE_NAME AS '表名',
    COLUMN_NAME AS '列名',
    CONSTRAINT_NAME AS '约束名称',
    REFERENCED_TABLE_NAME AS '引用表名',
    REFERENCED_COLUMN_NAME AS '引用列名'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE REFERENCED_TABLE_NAME = 'package_products'
    AND TABLE_NAME IN ('package_itinerary', 'package_price_variant')
ORDER BY TABLE_NAME, CONSTRAINT_NAME;


















