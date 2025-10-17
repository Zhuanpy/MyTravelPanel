-- ========================================
-- MySQL Workbench 执行脚本
-- 移除 travelproducts 表中不需要的字段
-- ========================================

USE travel_panel_new;

-- 1. 先检查表中有哪些字段
DESCRIBE travelproducts;

-- 2. 检查字段是否存在数据（根据实际字段名调整）
SELECT 
    COUNT(*) AS total_products
FROM travelproducts;

-- 如果字段存在，可以查看有数据的记录
-- SELECT * FROM travelproducts WHERE duration_nights IS NOT NULL LIMIT 5;

-- 2. 删除字段（兼容所有MySQL版本）
-- 注意：如果字段不存在会报错，可以忽略错误继续执行

ALTER TABLE travelproducts DROP COLUMN duration_nights;
ALTER TABLE travelproducts DROP COLUMN contact_person;
ALTER TABLE travelproducts DROP COLUMN contact_phone;
ALTER TABLE travelproducts DROP COLUMN contact_email;

-- 3. 验证结果
DESCRIBE travelproducts;

SELECT '✅ 字段删除完成！' AS Status;

