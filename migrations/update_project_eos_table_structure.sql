-- =====================================================
-- 更新 project_eos 表结构
-- 根据代码重构：删除冗余字段（EO是内部用于支付供应商的统计表单）
-- 执行日期：请在执行前记录
-- =====================================================

-- 步骤1: 查看并删除外键约束
-- 需要先删除外键约束才能删除列
-- =====================================================

-- 方法1: 查看所有外键约束（执行此查询以获取实际约束名称）
-- SELECT 
--     CONSTRAINT_NAME,
--     COLUMN_NAME,
--     REFERENCED_TABLE_NAME,
--     REFERENCED_COLUMN_NAME
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE TABLE_SCHEMA = DATABASE()
--   AND TABLE_NAME = 'project_eos'
--   AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 方法2: 使用 REFERENTIAL_CONSTRAINTS 表查询（推荐）
-- SELECT 
--     kcu.CONSTRAINT_NAME,
--     kcu.COLUMN_NAME,
--     kcu.REFERENCED_TABLE_NAME,
--     kcu.REFERENCED_COLUMN_NAME
-- FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
-- JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
--   ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
--   AND rc.CONSTRAINT_SCHEMA = kcu.TABLE_SCHEMA
-- WHERE rc.CONSTRAINT_SCHEMA = DATABASE()
--   AND rc.TABLE_NAME = 'project_eos'
--   AND kcu.COLUMN_NAME = 'supplier_id';

-- 方法3: 查看表创建语句（可以看到所有外键约束名称）
-- SHOW CREATE TABLE `project_eos`;

-- =====================================================
-- 删除 supplier_id 的外键约束
-- 请先执行上面的查询之一，找到实际的外键约束名称
-- 然后将下面的约束名称替换为实际的名称
-- =====================================================

-- 如果查询结果显示约束名称，请取消注释下面这行并替换约束名称
-- ALTER TABLE `project_eos` DROP FOREIGN KEY `实际的约束名称`;

-- 或者，如果supplier_id没有外键约束（可能已经被删除或从未创建），
-- 可以直接跳过此步骤，直接删除列

-- =====================================================
-- 步骤2: 删除冗余字段
-- 以下字段已通过关联的REF表获取，不再需要
-- =====================================================

-- 2.1 删除订单名称字段（通过ref.description获取）
ALTER TABLE `project_eos` 
DROP COLUMN `name`;

-- 2.2 删除供应商类型字段（通过ref.ref_type_id关联获取）
ALTER TABLE `project_eos` 
DROP COLUMN `supplier_type`;

-- 2.3 删除供应商ID字段（通过ref.supplier_id关联获取）
-- 注意：需要先删除外键约束才能删除此列
ALTER TABLE `project_eos` 
DROP COLUMN `supplier_id`;

-- 2.4 删除货币字段（通过ref.currency获取）
ALTER TABLE `project_eos` 
DROP COLUMN `currency`;

-- 2.5 删除备注字段（通过ref.remarks获取）
ALTER TABLE `project_eos` 
DROP COLUMN `remarks`;

-- =====================================================
-- 验证语句（执行后可以运行以下查询验证表结构）
-- =====================================================

-- 查看更新后的表结构
-- DESCRIBE `project_eos`;

-- 查看更新后的字段列表
-- SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_SCHEMA = DATABASE() 
--   AND TABLE_NAME = 'project_eos'
-- ORDER BY ORDINAL_POSITION;

-- =====================================================
-- 保留的字段说明：
-- - id: 主键
-- - ref_id: 关联到REF表（外键）
-- - eo_number: EO编号（唯一标识）
-- - amount: 支付金额
-- - status: 支付状态
-- - external_system: 外部系统名称（可选）
-- - external_status: 外部系统状态（可选）
-- - external_reference: 外部系统参考号（可选）
-- - created_at: 创建时间
-- - updated_at: 更新时间
-- =====================================================

