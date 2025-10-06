-- 添加航站楼和登机口字段到flight_schedule表 (安全版本)
-- 执行日期: 2025-01-05

-- 第一步：添加字段
-- 添加出发航站楼字段
ALTER TABLE flight_schedule 
ADD COLUMN departure_terminal VARCHAR(10) DEFAULT 'Unknown';

-- 添加出发登机口字段
ALTER TABLE flight_schedule 
ADD COLUMN departure_gate VARCHAR(10) DEFAULT 'Unknown';

-- 添加到达航站楼字段
ALTER TABLE flight_schedule 
ADD COLUMN arrival_terminal VARCHAR(10) DEFAULT 'Unknown';

-- 添加到达登机口字段
ALTER TABLE flight_schedule 
ADD COLUMN arrival_gate VARCHAR(10) DEFAULT 'Unknown';

-- 添加飞机型号字段
ALTER TABLE flight_schedule 
ADD COLUMN aircraft VARCHAR(10) DEFAULT 'Unknown';

-- 添加航班状态字段
ALTER TABLE flight_schedule 
ADD COLUMN status VARCHAR(20) DEFAULT 'Unknown';

-- 第二步：安全更新现有记录 (分别更新每个字段)
-- 更新出发航站楼
UPDATE flight_schedule 
SET departure_terminal = 'Unknown' 
WHERE id > 0 AND departure_terminal IS NULL;

-- 更新出发登机口
UPDATE flight_schedule 
SET departure_gate = 'Unknown' 
WHERE id > 0 AND departure_gate IS NULL;

-- 更新到达航站楼
UPDATE flight_schedule 
SET arrival_terminal = 'Unknown' 
WHERE id > 0 AND arrival_terminal IS NULL;

-- 更新到达登机口
UPDATE flight_schedule 
SET arrival_gate = 'Unknown' 
WHERE id > 0 AND arrival_gate IS NULL;

-- 更新飞机型号
UPDATE flight_schedule 
SET aircraft = 'Unknown' 
WHERE id > 0 AND aircraft IS NULL;

-- 更新航班状态
UPDATE flight_schedule 
SET status = 'Unknown' 
WHERE id > 0 AND status IS NULL;

-- 第三步：添加注释 (MySQL不支持COMMENT ON COLUMN，使用ALTER TABLE)
ALTER TABLE flight_schedule 
MODIFY COLUMN departure_terminal VARCHAR(10) DEFAULT 'Unknown' COMMENT '出发航站楼';

ALTER TABLE flight_schedule 
MODIFY COLUMN departure_gate VARCHAR(10) DEFAULT 'Unknown' COMMENT '出发登机口';

ALTER TABLE flight_schedule 
MODIFY COLUMN arrival_terminal VARCHAR(10) DEFAULT 'Unknown' COMMENT '到达航站楼';

ALTER TABLE flight_schedule 
MODIFY COLUMN arrival_gate VARCHAR(10) DEFAULT 'Unknown' COMMENT '到达登机口';

ALTER TABLE flight_schedule 
MODIFY COLUMN aircraft VARCHAR(10) DEFAULT 'Unknown' COMMENT '飞机型号';

ALTER TABLE flight_schedule 
MODIFY COLUMN status VARCHAR(20) DEFAULT 'Unknown' COMMENT '航班状态';

-- 第四步：显示表结构确认
SELECT column_name, data_type, column_default, is_nullable, column_comment
FROM information_schema.columns 
WHERE table_name = 'flight_schedule' 
  AND table_schema = DATABASE()
ORDER BY ordinal_position;
