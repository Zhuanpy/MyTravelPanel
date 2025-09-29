-- 为 athina_booking_headers 表添加 book_date 字段
-- 执行时间：2025-09-29

-- 添加 book_date 字段到 athina_booking_headers 表
ALTER TABLE `athina_booking_headers` 
ADD COLUMN `book_date` date DEFAULT NULL COMMENT '预订日期' 
AFTER `corporate_name`;

-- 验证字段是否添加成功
DESCRIBE `athina_booking_headers`;
