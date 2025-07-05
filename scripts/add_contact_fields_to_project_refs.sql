-- 为 project_refs 表添加联系人字段
-- 执行时间: 2025-01-27

-- 添加联系人姓名字段
ALTER TABLE `project_refs` 
ADD COLUMN `contact_name` VARCHAR(50) NULL COMMENT '联系人姓名' AFTER `supplier_phone`;

-- 添加联系电话字段
ALTER TABLE `project_refs` 
ADD COLUMN `contact_phone` VARCHAR(20) NULL COMMENT '联系电话' AFTER `contact_name`;

-- 添加电子邮箱字段
ALTER TABLE `project_refs` 
ADD COLUMN `contact_email` VARCHAR(100) NULL COMMENT '电子邮箱' AFTER `contact_phone`;

-- 验证字段是否添加成功
DESCRIBE `project_refs`; 