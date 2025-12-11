-- 数据库迁移脚本：将 product_itinerary 和 product_price_variant 重命名为 package_ 开头
-- 手动版本：需要先查询外键名称，然后手动替换
-- 执行时间：请在维护窗口期间执行
-- 备份建议：执行前请先备份数据库

-- ============================================
-- 步骤 1: 查询当前外键约束名称（先执行此步骤）
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
-- 步骤 3: 更新外键约束名称
-- ============================================
-- 注意：请将下面的约束名称替换为步骤1查询到的实际约束名称

-- 更新 package_itinerary 表的外键约束名称
-- 重要：请先执行步骤1的查询，找到实际的约束名称，然后替换下面的 'product_itinerary_ibfk_1'
-- 例如：如果查询到的是 'package_itinerary_ibfk_1'，则改为：
-- ALTER TABLE `package_itinerary` DROP FOREIGN KEY `package_itinerary_ibfk_1`;

-- 先查询实际的约束名称（取消注释执行）
-- SELECT CONSTRAINT_NAME 
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
-- WHERE TABLE_NAME = 'package_itinerary' 
--     AND COLUMN_NAME = 'product_id' 
--     AND REFERENCED_TABLE_NAME = 'package_products';

-- 然后替换下面的约束名称并执行
ALTER TABLE `package_itinerary` 
DROP FOREIGN KEY `product_itinerary_ibfk_1`;

ALTER TABLE `package_itinerary` 
ADD CONSTRAINT `fk_package_itinerary_product` 
FOREIGN KEY (`product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE CASCADE 
ON UPDATE CASCADE;

-- 更新 package_price_variant 表的外键约束名称
-- 重要：请先执行步骤1的查询，找到实际的约束名称，然后替换下面的 'product_price_variant_ibfk_1'
-- 例如：如果查询到的是 'package_price_variant_ibfk_1'，则改为：
-- ALTER TABLE `package_price_variant` DROP FOREIGN KEY `package_price_variant_ibfk_1`;

-- 先查询实际的约束名称（取消注释执行）
-- SELECT CONSTRAINT_NAME 
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
-- WHERE TABLE_NAME = 'package_price_variant' 
--     AND COLUMN_NAME = 'product_id' 
--     AND REFERENCED_TABLE_NAME = 'package_products';

-- 然后替换下面的约束名称并执行
ALTER TABLE `package_price_variant` 
DROP FOREIGN KEY `product_price_variant_ibfk_1`;

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

