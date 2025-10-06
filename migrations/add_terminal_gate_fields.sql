-- 添加航站楼和登机口字段到flight_schedule表
-- 执行日期: 2025-01-05

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

-- 为现有记录设置默认值 (使用主键条件避免安全更新模式错误)
UPDATE flight_schedule 
SET 
    departure_terminal = 'Unknown',
    departure_gate = 'Unknown',
    arrival_terminal = 'Unknown',
    arrival_gate = 'Unknown',
    aircraft = 'Unknown',
    status = 'Unknown'
WHERE id > 0 
  AND (departure_terminal IS NULL 
   OR departure_gate IS NULL 
   OR arrival_terminal IS NULL 
   OR arrival_gate IS NULL 
   OR aircraft IS NULL 
   OR status IS NULL);

-- 添加注释
COMMENT ON COLUMN flight_schedule.departure_terminal IS '出发航站楼';
COMMENT ON COLUMN flight_schedule.departure_gate IS '出发登机口';
COMMENT ON COLUMN flight_schedule.arrival_terminal IS '到达航站楼';
COMMENT ON COLUMN flight_schedule.arrival_gate IS '到达登机口';
COMMENT ON COLUMN flight_schedule.aircraft IS '飞机型号';
COMMENT ON COLUMN flight_schedule.status IS '航班状态';

-- 显示表结构确认
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns 
WHERE table_name = 'flight_schedule' 
ORDER BY ordinal_position;
