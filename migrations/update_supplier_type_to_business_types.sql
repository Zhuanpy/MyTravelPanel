-- 将供应商类型从枚举改为关联 business_types 表
-- 执行前请备份数据库

-- 临时禁用安全更新模式
SET SQL_SAFE_UPDATES = 0;

-- 1. 添加新的 supplier_type_id 列（如果列已存在则跳过此步骤）
-- ALTER TABLE `suppliers` 
-- ADD COLUMN `supplier_type_id` INT NULL COMMENT '供应商类型ID' AFTER `name`;

-- 2. 将旧的枚举值映射到 business_types 表的 id
-- 映射关系：visa->签证, flight->机票, hotel->酒店, transport->交通, local_operator->地接, other->其他
UPDATE `suppliers` s
INNER JOIN `business_types` bt ON 
    (s.supplier_type = 'visa' AND bt.code = 'visa') OR
    (s.supplier_type = 'flight' AND bt.code = 'flight') OR
    (s.supplier_type = 'hotel' AND bt.code = 'hotel') OR
    (s.supplier_type = 'transport' AND bt.code = 'transport') OR
    (s.supplier_type = 'local_operator' AND bt.code = 'land_tour') OR
    (s.supplier_type = 'other' AND bt.code = 'other')
SET s.supplier_type_id = bt.id
WHERE s.supplier_id > 0;

-- 3. 如果 business_types 表中没有对应的类型，使用 'other' 类型
UPDATE `suppliers` s
LEFT JOIN `business_types` bt ON s.supplier_type_id = bt.id
SET s.supplier_type_id = (SELECT id FROM `business_types` WHERE code = 'other' LIMIT 1)
WHERE s.supplier_type_id IS NULL AND s.supplier_type IS NOT NULL AND s.supplier_id > 0;

-- 4. 删除旧的 supplier_type 枚举列
-- 注意：MySQL 中删除 ENUM 列需要先删除列，然后重新创建（如果需要保留数据）
-- 这里直接删除，因为数据已经迁移到 supplier_type_id
ALTER TABLE `suppliers` DROP COLUMN `supplier_type`;

-- 恢复安全更新模式
SET SQL_SAFE_UPDATES = 1;

-- 5. 添加外键约束（可选，如果需要强制引用完整性）
-- ALTER TABLE `suppliers` 
-- ADD CONSTRAINT `fk_supplier_business_type` 
-- FOREIGN KEY (`supplier_type_id`) REFERENCES `business_types` (`id`) 
-- ON DELETE SET NULL ON UPDATE CASCADE;

