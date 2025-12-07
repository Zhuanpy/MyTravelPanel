-- 添加 order_type 字段到 athina_booking_headers 表
-- 用于标识订单类型（小单/小单-中单过渡/中单/中单-大单过渡/大单）

ALTER TABLE `athina_booking_headers` 
ADD COLUMN `order_type` VARCHAR(50) NULL COMMENT '订单类型（小单/小单-中单过渡/中单/中单-大单过渡/大单）' AFTER `company_profit`;

