-- =====================================================
-- 查找并删除 project_eos 表中 supplier_id 的外键约束
-- =====================================================

-- 步骤1: 查找 supplier_id 的外键约束名称
-- 请执行此查询并记录返回的 CONSTRAINT_NAME
-- =====================================================

SELECT 
    kcu.CONSTRAINT_NAME AS '外键约束名称',
    kcu.COLUMN_NAME AS '列名',
    kcu.REFERENCED_TABLE_NAME AS '引用表名',
    kcu.REFERENCED_COLUMN_NAME AS '引用列名'
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
  ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
  AND rc.CONSTRAINT_SCHEMA = kcu.TABLE_SCHEMA
WHERE rc.CONSTRAINT_SCHEMA = DATABASE()
  AND rc.TABLE_NAME = 'project_eos'
  AND kcu.COLUMN_NAME = 'supplier_id';

-- =====================================================
-- 步骤2: 根据查询结果，删除外键约束
-- 将 'FK_NAME_FROM_QUERY' 替换为步骤1查询到的实际约束名称
-- =====================================================

-- 示例（请替换为实际的约束名称）:
-- ALTER TABLE `project_eos` DROP FOREIGN KEY `FK_NAME_FROM_QUERY`;

-- =====================================================
-- 步骤3: 删除列
-- =====================================================

ALTER TABLE `project_eos` DROP COLUMN `supplier_id`;

