-- 数据库迁移脚本：将 product_itinerary 和 product_price_variant 重命名为 package_ 开头
-- 执行时间：请在维护窗口期间执行
-- 备份建议：执行前请先备份数据库

-- ============================================
-- 步骤 1: 查询当前外键约束名称（先执行此查询，记录结果）
-- ============================================
SELECT 
    TABLE_NAME AS '表名',
    CONSTRAINT_NAME AS '外键约束名称',
    COLUMN_NAME AS '列名',
    REFERENCED_TABLE_NAME AS '引用表名'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_NAME IN ('product_itinerary', 'product_price_variant')
    AND REFERENCED_TABLE_NAME = 'travelproducts'
ORDER BY TABLE_NAME;

-- ============================================
-- 步骤 2: 重命名表
-- ============================================
RENAME TABLE `product_itinerary` TO `package_itinerary`;
RENAME TABLE `product_price_variant` TO `package_price_variant`;

-- ============================================
-- 步骤 3: 查询重命名后的外键约束名称
-- ============================================
SELECT 
    TABLE_NAME AS '表名',
    CONSTRAINT_NAME AS '外键约束名称',
    COLUMN_NAME AS '列名',
    REFERENCED_TABLE_NAME AS '引用表名'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_NAME IN ('package_itinerary', 'package_price_variant')
    AND REFERENCED_TABLE_NAME = 'package_products'
ORDER BY TABLE_NAME;

-- ============================================
-- 步骤 4: 更新外键约束名称
-- ============================================
-- 注意：请将下面的 'product_itinerary_ibfk_1' 替换为步骤3查询到的实际约束名称
-- 例如：如果查询到的是 'package_itinerary_ibfk_1'，则替换为 'package_itinerary_ibfk_1'

-- 更新 package_itinerary 表的外键约束名称
-- 方法：先查看步骤3的结果，找到 package_itinerary 表的 CONSTRAINT_NAME，替换下面的名称
ALTER TABLE `package_itinerary` 
DROP FOREIGN KEY `product_itinerary_ibfk_1`;

ALTER TABLE `package_itinerary` 
ADD CONSTRAINT `fk_package_itinerary_product` 
FOREIGN KEY (`product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE CASCADE 
ON UPDATE CASCADE;

-- 更新 package_price_variant 表的外键约束名称
-- 方法：先查看步骤3的结果，找到 package_price_variant 表的 CONSTRAINT_NAME，替换下面的名称
ALTER TABLE `package_price_variant` 
DROP FOREIGN KEY `product_price_variant_ibfk_1`;

ALTER TABLE `package_price_variant` 
ADD CONSTRAINT `fk_package_price_variant_product` 
FOREIGN KEY (`product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE CASCADE 
ON UPDATE CASCADE;

-- ============================================
-- 步骤 5: 验证迁移结果
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
















