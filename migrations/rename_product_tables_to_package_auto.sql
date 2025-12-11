-- 数据库迁移脚本：将 product_itinerary 和 product_price_variant 重命名为 package_ 开头
-- 自动版本：使用存储过程自动处理外键约束
-- 执行时间：请在维护窗口期间执行
-- 备份建议：执行前请先备份数据库

-- ============================================
-- 步骤 1: 重命名表
-- ============================================
RENAME TABLE `product_itinerary` TO `package_itinerary`;
RENAME TABLE `product_price_variant` TO `package_price_variant`;

-- ============================================
-- 步骤 2: 自动更新外键约束（使用动态SQL）
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
-- 步骤 3: 验证迁移结果
-- ============================================
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




