-- =====================================================
-- 删除 project_eos 表中的 amount 字段
-- 金额现在通过关联的 project_refs.cost_price 获取
-- 执行日期：请在执行前记录
-- =====================================================

-- 删除 amount 字段
ALTER TABLE `project_eos` 
DROP COLUMN `amount`;

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
-- 最终表结构说明：
-- - id: 主键
-- - ref_id: 外键（关联到 project_refs 表）
-- - eo_number: EO编号
-- - status: 支付状态
-- - external_system: 外部系统名称
-- - external_status: 外部系统状态
-- - external_reference: 外部系统参考号
-- - created_at: 创建时间
-- - updated_at: 更新时间
-- 
-- 金额信息通过 ref_id 关联到 project_refs.cost_price 获取
-- =====================================================

