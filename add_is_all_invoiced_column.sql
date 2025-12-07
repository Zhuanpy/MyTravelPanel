-- 添加 is_all_invoiced 字段到 athina_booking_headers 表
ALTER TABLE `athina_booking_headers` 
ADD COLUMN `is_all_invoiced` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否全部已开票（该HEADER下所有booking_ref都有invoice_no）' 
AFTER `sales_consultant`;

-- 删除 invoice_no 字段（如果字段存在，手动执行）
ALTER TABLE `athina_booking_headers` DROP COLUMN `invoice_no`;

-- 删除 invoice_date 字段（如果字段存在，手动执行）
ALTER TABLE `athina_booking_headers` DROP COLUMN `invoice_date`;

