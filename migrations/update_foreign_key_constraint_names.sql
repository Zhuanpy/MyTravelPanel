-- 更新外键约束名称，使其与新的表名一致
-- 执行时间：在表重命名后执行

-- ============================================
-- 步骤 1: 更新 package_products 表的自引用外键名称
-- ============================================
-- 删除旧的外键约束
ALTER TABLE `package_products` 
DROP FOREIGN KEY `fk_travelproducts_parent`;

-- 重新创建外键约束（使用新名称）
ALTER TABLE `package_products` 
ADD CONSTRAINT `fk_package_products_parent` 
FOREIGN KEY (`parent_product_id`) 
REFERENCES `package_products` (`id`) 
ON DELETE SET NULL 
ON UPDATE CASCADE;

-- ============================================
-- 步骤 2: 验证所有外键约束
-- ============================================
-- 查看所有指向 package_products 的外键
SELECT 
    TABLE_NAME AS '表名',
    COLUMN_NAME AS '列名',
    CONSTRAINT_NAME AS '约束名称',
    REFERENCED_TABLE_NAME AS '引用表名',
    REFERENCED_COLUMN_NAME AS '引用列名'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE REFERENCED_TABLE_NAME = 'package_products'
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- ============================================
-- 步骤 3: 验证 package_products 表的所有外键（包括自引用）
-- ============================================
SELECT 
    TABLE_NAME AS '表名',
    COLUMN_NAME AS '列名',
    CONSTRAINT_NAME AS '约束名称',
    REFERENCED_TABLE_NAME AS '引用表名',
    REFERENCED_COLUMN_NAME AS '引用列名'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_NAME = 'package_products'
ORDER BY CONSTRAINT_NAME;

