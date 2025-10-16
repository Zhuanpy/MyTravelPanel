-- ========================================
-- 修复：允许 valid_until 字段为空
-- ========================================

USE travel_panel_new;

-- 将 valid_until 字段改为允许 NULL
ALTER TABLE travelproducts 
MODIFY COLUMN valid_until DATE NULL COMMENT '有效期';

-- 验证修改
DESCRIBE travelproducts;

-- 查看 valid_until 字段的定义
SELECT 
    COLUMN_NAME,
    IS_NULLABLE,
    DATA_TYPE,
    COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'travel_panel_new' 
    AND TABLE_NAME = 'travelproducts'
    AND COLUMN_NAME = 'valid_until';

SELECT '✅ valid_until 字段已修改为允许 NULL' AS Status;

