-- 为供应商表添加点击统计字段
-- 执行日期: 2024-12-19

-- 检查并添加click_count字段
SET @sql = IF(
    (SELECT COUNT(*) 
     FROM information_schema.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
     AND TABLE_NAME = 'suppliers' 
     AND COLUMN_NAME = 'click_count') = 0,
    'ALTER TABLE suppliers ADD COLUMN click_count INT DEFAULT 0 COMMENT ''点击次数''',
    'SELECT ''click_count字段已存在，跳过添加'' as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 验证字段添加结果
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'suppliers' 
AND COLUMN_NAME = 'click_count';

-- 显示表结构确认
DESCRIBE suppliers;
