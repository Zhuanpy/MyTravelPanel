-- 更新 is_count_performance 字段的默认值为 0（否）

-- 步骤1：更新字段的默认值和注释
ALTER TABLE `athina_booking_headers` 
MODIFY COLUMN `is_count_performance` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已核算业绩';

-- 步骤2：将所有现有记录都设为否（未核算）- 使用WHERE条件以符合安全模式
UPDATE `athina_booking_headers` 
SET `is_count_performance` = 0 
WHERE id > 0;

