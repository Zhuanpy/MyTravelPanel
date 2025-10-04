-- 添加员工等级字段到用户资料表
-- 执行时间: 2025-10-04

-- 添加staff_level字段
ALTER TABLE user_profiles 
ADD COLUMN staff_level INTEGER DEFAULT 1 COMMENT '员工等级：1-普通员工(只能看自己的订单), 2-高级员工(可看所有订单)';

-- 更新现有员工用户的默认等级
-- 可以根据需要调整特定用户的等级
-- 例如：将管理员或特定员工的等级设置为2
-- UPDATE user_profiles 
-- SET staff_level = 2 
-- WHERE user_id IN (
--     SELECT id FROM auth_users 
--     WHERE role_id = (SELECT id FROM roles WHERE name = 'admin')
-- );

-- 创建索引以提高查询性能
CREATE INDEX idx_user_profiles_staff_level ON user_profiles(staff_level);

-- 验证字段添加成功
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    COLUMN_DEFAULT, 
    COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'user_profiles' 
AND COLUMN_NAME = 'staff_level';
