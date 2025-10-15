-- ========================================
-- 清理重复的 tour_product_data 表
-- 执行日期: 2025-10-15
-- 原因: 该表未被使用且功能被 travelproducts 表完全覆盖
-- ========================================

-- 第一步：检查表是否存在
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME
FROM 
    INFORMATION_SCHEMA.TABLES
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tour_product_data';

-- 第二步：检查是否有数据（备份前）
SELECT COUNT(*) as record_count FROM tour_product_data;

-- 如果有数据，先查看数据内容
SELECT * FROM tour_product_data LIMIT 10;

-- 第三步：检查外键依赖
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE
    TABLE_SCHEMA = DATABASE()
    AND (REFERENCED_TABLE_NAME = 'tour_product_data' 
         OR TABLE_NAME = 'tour_product_data');

-- 第四步：删除表（确认无依赖后执行）
-- 注意：执行前请确保已备份数据！
-- DROP TABLE IF EXISTS tour_product_data;

-- 第五步：验证删除结果
-- SELECT 
--     TABLE_NAME
-- FROM 
--     INFORMATION_SCHEMA.TABLES
-- WHERE 
--     TABLE_SCHEMA = DATABASE()
--     AND TABLE_NAME = 'tour_product_data';
-- 
-- -- 应该返回空结果

-- ========================================
-- 执行说明：
-- 1. 首先执行第一步到第三步，确认表状态
-- 2. 如果有重要数据，使用 mysqldump 备份
-- 3. 确认无外键依赖后，取消第四步注释并执行
-- 4. 执行第五步验证删除成功
-- ========================================

