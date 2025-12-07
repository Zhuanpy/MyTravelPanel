-- 检查字段是否存在，如果存在则更新注释（如果不同）

-- 首先检查字段是否存在
-- SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, COLUMN_COMMENT 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_SCHEMA = 'travelindustry' 
-- AND TABLE_NAME = 'athina_booking_headers' 
-- AND COLUMN_NAME = 'is_count_performance';

-- 如果字段已存在，更新默认值和注释
ALTER TABLE `athina_booking_headers` 
MODIFY COLUMN `is_count_performance` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已核算业绩';

