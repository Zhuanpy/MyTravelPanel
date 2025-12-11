-- 数据库迁移脚本：将 product_itinerary 和 product_price_variant 重命名为 package_ 开头
-- 执行时间：请在维护窗口期间执行
-- 备份建议：执行前请先备份数据库

-- ============================================
-- 步骤 1: 重命名 product_itinerary 表
-- ============================================
RENAME TABLE `product_itinerary` TO `package_itinerary`;

-- ============================================
-- 步骤 2: 重命名 product_price_variant 表
-- ============================================
RENAME TABLE `product_price_variant` TO `package_price_variant`;

-- ============================================
-- 步骤 3: 更新外键约束名称（使其与新的表名一致）
-- ============================================

-- 更新 package_itinerary 表的外键约束名称
-- 注意：如果外键约束名称不同，请先查询实际的外键名称
-- SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
-- WHERE TABLE_NAME = 'package_itinerary' AND COLUMN_NAME = 'product_id' 
-- AND REFERENCED_TABLE_NAME = 'package_products';

-- 删除旧的外键约束（如果约束名称是 product_itinerary_ibfk_1）
-- 如果约束名称不同，请替换为实际的外键名称
ALTER TABLE `package_itinerary` 
DROP FOREIGN KEY `product_itinerary_ibfk_1`;

-- 重新创建外键约束（使用新名称）
ALTER TABLE `package_itinerary` 
ADD CONSTRAINT `fk_package_itinerary_product` 
FOREIGN KEY (`product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE CASCADE 
ON UPDATE CASCADE;

-- 更新 package_price_variant 表的外键约束名称
-- 注意：如果外键约束名称不同，请先查询实际的外键名称
-- SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
-- WHERE TABLE_NAME = 'package_price_variant' AND COLUMN_NAME = 'product_id' 
-- AND REFERENCED_TABLE_NAME = 'package_products';

-- 删除旧的外键约束（如果约束名称是 product_price_variant_ibfk_1）
-- 如果约束名称不同，请替换为实际的外键名称
ALTER TABLE `package_price_variant` 
DROP FOREIGN KEY `product_price_variant_ibfk_1`;

-- 重新创建外键约束（使用新名称）
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
-- SHOW TABLES LIKE 'package_itinerary';
-- SHOW TABLES LIKE 'package_price_variant';

-- 验证表结构
-- DESCRIBE package_itinerary;
-- DESCRIBE package_price_variant;

-- 验证外键关系
-- SELECT 
--     TABLE_NAME AS '表名',
--     COLUMN_NAME AS '列名',
--     CONSTRAINT_NAME AS '约束名称',
--     REFERENCED_TABLE_NAME AS '引用表名',
--     REFERENCED_COLUMN_NAME AS '引用列名'
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE REFERENCED_TABLE_NAME = 'package_products'
--     AND TABLE_NAME IN ('package_itinerary', 'package_price_variant')
-- ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- ============================================
-- 回滚脚本（如果需要回滚）
-- ============================================
-- RENAME TABLE `package_itinerary` TO `product_itinerary`;
-- RENAME TABLE `package_price_variant` TO `product_price_variant`;
-- 
-- -- 恢复外键约束名称
-- ALTER TABLE `product_itinerary` 
-- DROP FOREIGN KEY `fk_package_itinerary_product`;
-- ALTER TABLE `product_itinerary` 
-- ADD CONSTRAINT `product_itinerary_ibfk_1` 
-- FOREIGN KEY (`product_id`) 
-- REFERENCES `package_products` (`id`);
-- 
-- ALTER TABLE `product_price_variant` 
-- DROP FOREIGN KEY `fk_package_price_variant_product`;
-- ALTER TABLE `product_price_variant` 
-- ADD CONSTRAINT `product_price_variant_ibfk_1` 
-- FOREIGN KEY (`product_id`) 
-- REFERENCES `package_products` (`id`);

