-- =====================================================
-- 更新 project_refs 表结构
-- 根据代码重构：删除冗余字段并重命名字段
-- 执行日期：请在执行前记录
-- =====================================================

-- 步骤1: 重命名字段
-- 注意：需要先备份数据，确保数据安全

-- 1.1 先将 description 重命名为 detailed_description
ALTER TABLE `project_refs` 
CHANGE COLUMN `description` `detailed_description` VARCHAR(200) NOT NULL COMMENT '详细描述';

-- 1.2 将 name 重命名为 description
ALTER TABLE `project_refs` 
CHANGE COLUMN `name` `description` VARCHAR(100) NULL COMMENT '描述';

-- =====================================================
-- 步骤2: 删除冗余字段
-- 以下字段已通过关联表或HID表获取，不再需要
-- =====================================================

-- 2.1 删除供应商联系人字段（通过supplier_id关联获取）
ALTER TABLE `project_refs` 
DROP COLUMN `supplier_contact`,
DROP COLUMN `supplier_phone`;

-- 2.2 删除联系人信息字段（统一保存在HID表中）
ALTER TABLE `project_refs` 
DROP COLUMN `contact_name`,
DROP COLUMN `contact_phone`,
DROP COLUMN `contact_email`,
DROP COLUMN `leader_name`;

-- 2.3 删除交付日期字段（不再需要）
ALTER TABLE `project_refs` 
DROP COLUMN `expected_delivery_date`,
DROP COLUMN `actual_delivery_date`;

-- =====================================================
-- 验证语句（执行后可以运行以下查询验证表结构）
-- =====================================================

-- 查看更新后的表结构
-- DESCRIBE `project_refs`;

-- 查看更新后的字段列表
-- SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_SCHEMA = DATABASE() 
--   AND TABLE_NAME = 'project_refs'
-- ORDER BY ORDINAL_POSITION;

