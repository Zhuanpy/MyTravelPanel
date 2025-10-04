-- 更新staff_level字段的注释和索引 (MySQL版本)
-- 执行时间: 2025-10-04

-- 1. 为staff_level字段添加注释
ALTER TABLE user_profiles 
MODIFY COLUMN staff_level INT DEFAULT 1 COMMENT '员工等级：1-普通员工(只能看自己的订单), 2-高级员工(可看所有订单)';

-- 2. 创建索引以提高查询性能（如果不存在）
-- 先检查索引是否存在，如果不存在则创建
-- 注意：MySQL不支持 CREATE INDEX IF NOT EXISTS，需要手动检查
-- 如果索引已存在，此语句会报错，可以忽略

-- 方法1：直接创建索引（如果已存在会报错，可以忽略）
CREATE INDEX idx_user_profiles_staff_level ON user_profiles(staff_level);

-- 方法2：如果上面报错，说明索引已存在，可以使用以下查询验证
-- SHOW INDEX FROM user_profiles WHERE Column_name = 'staff_level';

-- 3. 验证字段更新成功
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    COLUMN_DEFAULT, 
    COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'user_profiles' 
AND COLUMN_NAME = 'staff_level';

-- 4. 验证索引创建成功
SHOW INDEX FROM user_profiles WHERE Column_name = 'staff_level';
