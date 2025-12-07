-- 添加 is_count_performance 字段到 athina_booking_headers 表
-- 用于标记该记录是否已核算员工业绩

ALTER TABLE `athina_booking_headers` 
ADD COLUMN `is_count_performance` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已核算业绩' 
AFTER `is_all_invoiced`;

