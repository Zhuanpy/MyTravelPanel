-- 将 employee_profit 拆分为 operator_profit (操作员利润) 和 sales_profit (业务员利润)
-- 在 athina_booking_headers 表中

-- 步骤 1: 如果 employee_profit 字段存在，先删除它（如果不存在，注释掉或删除这行）
ALTER TABLE `athina_booking_headers` DROP COLUMN `employee_profit`;

-- 步骤 2: 添加操作员利润字段
ALTER TABLE `athina_booking_headers` 
ADD COLUMN `operator_profit` DECIMAL(15, 2) NULL COMMENT '分给操作员的利润' AFTER `sub_total_margin`;

-- 步骤 3: 添加业务员利润字段
ALTER TABLE `athina_booking_headers` 
ADD COLUMN `sales_profit` DECIMAL(15, 2) NULL COMMENT '分给业务员的利润' AFTER `operator_profit`;

