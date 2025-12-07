-- 为 athina_booking_headers 表添加利润分配字段
-- employee_profit: 分给员工的利润
-- company_profit: 分给公司的利润

ALTER TABLE `athina_booking_headers` 
ADD COLUMN `employee_profit` DECIMAL(15,2) NULL COMMENT '分给员工的利润' AFTER `sub_total_margin`,
ADD COLUMN `company_profit` DECIMAL(15,2) NULL COMMENT '分给公司的利润' AFTER `employee_profit`;

