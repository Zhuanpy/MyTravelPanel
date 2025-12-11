-- 数据库迁移脚本：将 travelproducts 表重命名为 package_products
-- 执行时间：请在维护窗口期间执行
-- 备份建议：执行前请先备份数据库

-- ============================================
-- 步骤 1: 重命名表
-- ============================================
RENAME TABLE `travelproducts` TO `package_products`;

-- ============================================
-- 步骤 2: 更新外键约束名称（使其与新的表名一致）
-- ============================================
-- 注意：MySQL 会自动更新外键约束的引用，但约束名称可能仍包含旧表名

-- 更新 package_products 表的自引用外键名称
ALTER TABLE `package_products` 
DROP FOREIGN KEY IF EXISTS `fk_travelproducts_parent`;

ALTER TABLE `package_products` 
ADD CONSTRAINT `fk_package_products_parent` 
FOREIGN KEY (`parent_product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- ============================================
-- 步骤 3: 验证迁移结果
-- ============================================
-- 验证表是否存在
-- SHOW TABLES LIKE 'package_products';

-- 验证表结构
-- DESCRIBE package_products;

-- 验证外键关系
-- SELECT 
--     TABLE_NAME,
--     COLUMN_NAME,
--     CONSTRAINT_NAME,
--     REFERENCED_TABLE_NAME,
--     REFERENCED_COLUMN_NAME
-- FROM
--     INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE
--     REFERENCED_TABLE_NAME = 'package_products'
--     OR TABLE_NAME = 'package_products';

-- ============================================
-- 回滚脚本（如果需要回滚）
-- ============================================
-- RENAME TABLE `package_products` TO `travelproducts`;

