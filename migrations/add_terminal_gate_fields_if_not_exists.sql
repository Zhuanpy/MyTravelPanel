-- 添加航站楼和登机口字段到flight_schedule表 (检查字段是否存在)
-- 执行日期: 2025-01-05

-- 检查并添加出发航站楼字段
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'flight_schedule' 
       AND COLUMN_NAME = 'departure_terminal') > 0,
    'SELECT "departure_terminal column already exists" as message',
    'ALTER TABLE flight_schedule ADD COLUMN departure_terminal VARCHAR(10) DEFAULT "Unknown"'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加出发登机口字段
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'flight_schedule' 
       AND COLUMN_NAME = 'departure_gate') > 0,
    'SELECT "departure_gate column already exists" as message',
    'ALTER TABLE flight_schedule ADD COLUMN departure_gate VARCHAR(10) DEFAULT "Unknown"'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加到达航站楼字段
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'flight_schedule' 
       AND COLUMN_NAME = 'arrival_terminal') > 0,
    'SELECT "arrival_terminal column already exists" as message',
    'ALTER TABLE flight_schedule ADD COLUMN arrival_terminal VARCHAR(10) DEFAULT "Unknown"'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加到达登机口字段
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'flight_schedule' 
       AND COLUMN_NAME = 'arrival_gate') > 0,
    'SELECT "arrival_gate column already exists" as message',
    'ALTER TABLE flight_schedule ADD COLUMN arrival_gate VARCHAR(10) DEFAULT "Unknown"'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加飞机型号字段
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'flight_schedule' 
       AND COLUMN_NAME = 'aircraft') > 0,
    'SELECT "aircraft column already exists" as message',
    'ALTER TABLE flight_schedule ADD COLUMN aircraft VARCHAR(10) DEFAULT "Unknown"'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加航班状态字段
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'flight_schedule' 
       AND COLUMN_NAME = 'status') > 0,
    'SELECT "status column already exists" as message',
    'ALTER TABLE flight_schedule ADD COLUMN status VARCHAR(20) DEFAULT "Unknown"'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 安全更新现有记录 (分别更新每个字段)
-- 更新出发航站楼
UPDATE flight_schedule 
SET departure_terminal = 'Unknown' 
WHERE id > 0 AND (departure_terminal IS NULL OR departure_terminal = '');

-- 更新出发登机口
UPDATE flight_schedule 
SET departure_gate = 'Unknown' 
WHERE id > 0 AND (departure_gate IS NULL OR departure_gate = '');

-- 更新到达航站楼
UPDATE flight_schedule 
SET arrival_terminal = 'Unknown' 
WHERE id > 0 AND (arrival_terminal IS NULL OR arrival_terminal = '');

-- 更新到达登机口
UPDATE flight_schedule 
SET arrival_gate = 'Unknown' 
WHERE id > 0 AND (arrival_gate IS NULL OR arrival_gate = '');

-- 更新飞机型号
UPDATE flight_schedule 
SET aircraft = 'Unknown' 
WHERE id > 0 AND (aircraft IS NULL OR aircraft = '');

-- 更新航班状态
UPDATE flight_schedule 
SET status = 'Unknown' 
WHERE id > 0 AND (status IS NULL OR status = '');

-- 显示表结构确认
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns 
WHERE table_name = 'flight_schedule' 
  AND table_schema = DATABASE()
ORDER BY ordinal_position;
