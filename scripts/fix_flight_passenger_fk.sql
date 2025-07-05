-- 修复 project_flight_passengers 表的外键约束
-- 1. 删除原有外键（如有）
ALTER TABLE `project_flight_passengers` DROP FOREIGN KEY `project_flight_passengers_ibfk_1`;

-- 2. 添加正确的外键约束，指向 project_refs(id)
ALTER TABLE `project_flight_passengers`
ADD CONSTRAINT `fk_flight_passenger_ref`
FOREIGN KEY (`ref_id`) REFERENCES `project_refs`(`id`) ON DELETE CASCADE;

-- 3. 检查外键约束
SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'project_flight_passengers' AND REFERENCED_TABLE_NAME IS NOT NULL; 