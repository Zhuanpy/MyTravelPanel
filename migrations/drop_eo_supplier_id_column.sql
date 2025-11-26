-- =====================================================
-- 删除 project_eos 表中的 supplier_id 列
-- 包括自动查找并删除外键约束
-- =====================================================

-- 步骤1: 查找 supplier_id 的所有外键约束
-- 执行此查询，查看结果中的 CONSTRAINT_NAME
-- =====================================================

SELECT 
    CONSTRAINT_NAME AS '约束名称',
    COLUMN_NAME AS '列名',
    REFERENCED_TABLE_NAME AS '引用表',
    REFERENCED_COLUMN_NAME AS '引用列'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'project_eos'
  AND COLUMN_NAME = 'supplier_id'
  AND REFERENCED_TABLE_NAME IS NOT NULL;

-- =====================================================
-- 步骤2: 如果上面查询有结果，执行删除外键约束（替换约束名称）
-- 如果没有结果，说明没有外键约束，直接跳到步骤3
-- =====================================================

-- 如果查询有结果，请取消注释下面这行，并将 '约束名称' 替换为查询结果中的实际约束名称
-- ALTER TABLE `project_eos` DROP FOREIGN KEY `约束名称`;

-- =====================================================
-- 步骤3: 删除列（如果没有外键约束，可以直接执行此步骤）
-- =====================================================

-- 如果 supplier_id 列不存在外键约束，可以直接执行：
ALTER TABLE `project_eos` DROP COLUMN `supplier_id`;

-- 如果上面报错说有外键约束，请先执行步骤1和步骤2

